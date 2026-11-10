"""
Workbook Ingestion Pipeline for Life Insurance Public Disclosures.
Ingests a single consolidated Excel workbook:
1. Calculates file checksum and starts audit batch in audit_etl_batches.
2. Extracts tabular blocks across statutory schedules (L-1, L-2, L-3, L-4, L-32, etc.).
3. Scales metrics to standard warehouse base (INR Lakhs) while exempting non-currency items.
4. Performs taxonomy mapping using compiled regex rules.
5. Ingests normalized facts with SCD Type 2 ledger and records cell-level audit lineage.
6. Quarantines unmapped lines into quarantine_unmapped_taxonomy.
7. Executes cross-statement financial reconciliation assertions.
"""

import os
import re
import hashlib
import openpyxl
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from ..parsers.spatial_block import parse_worksheet_blocks, SpatialTableBlock
from ..parsers.unit_detector import apply_unit_scale, normalize_ratio
from ..reconciler.reconciler import reconcile_company_period

FILE_TO_COMPANY = {
    'ACKO_LIFE_INSURANCE_Consolidated.xlsx': 'ACKO_LIFE',
    'ADITYA_BIRLA_SUN_LIFE_INSURANCE_Consolidated.xlsx': 'ADITYA_BIRLA_LIFE',
    'AGEAS_FEDERAL_LIFE_INSURANCE_Consolidated.xlsx': 'AGEAS_FEDERAL_LIFE',
    'AVIVA_LIFE_INSURANCE_Consolidated.xlsx': 'AVIVA_LIFE',
    'AXIS_MAX_LIFE_INSURANCE_Consolidated.xlsx': 'AXIS_MAX_LIFE',
    'BAJAJ_LIFE_INSURANCE_Consolidated.xlsx': 'BAJAJ_LIFE',
    'BANDHAN_LIFE_INSURANCE_Consolidated.xlsx': 'BANDHAN_LIFE',
    'BHARTI_AXA_LIFE_INSURANCE_Consolidated.xlsx': 'BHARTI_AXA_LIFE',
    'CANARA_HSBC_LIFE_INSURANCE_Consolidated.xlsx': 'CANARA_HSBC_LIFE',
    'CREDITACCESS_LIFE_INSURANCE_Consolidated.xlsx': 'CREDITACCESS_LIFE',
    'EDELWEISS_LIFE_INSURANCE_Consolidated.xlsx': 'EDELWEISS_LIFE',
    'GENERALI_CENTRAL_LIFE_INSURANCE_Consolidated.xlsx': 'GENERALI_CENTRAL_LIFE',
    'GO_DIGIT_LIFE_INSURANCE_Consolidated.xlsx': 'GO_DIGIT_LIFE',
    'HDFC_Consolidated.xlsx': 'HDFC_LIFE',
    'ICICI_PRUDENTIAL_LIFE_INSURANCE_Consolidated.xlsx': 'ICICI_PRUDENTIAL_LIFE',
    'INDIAFIRST_LIFE_INSURANCE_Consolidated.xlsx': 'INDIAFIRST_LIFE',
    'INDUSIND_NIPPON_LIFE_INSURANCE_Consolidated.xlsx': 'INDUSIND_NIPPON_LIFE',
    'KOTAK_LIFE_INSURANCE_Consolidated.xlsx': 'KOTAK_LIFE',
    'LIC_Consolidated.xlsx': 'LIC',
    'PNB_METLIFE_INSURANCE_Consolidated (new).xlsx': 'PNB_METLIFE',
    'PRAMERICA_LIFE_INSURANCE_Consolidated.xlsx': 'PRAMERICA_LIFE',
    'SBI_LIFE_INSURANCE_Consolidated.xlsx': 'SBI_LIFE',
    'SHRIRAM_LIFE_INSURANCE_Consolidated.xlsx': 'SHRIRAM_LIFE',
    'SUD_LIFE_INSURANCE_Consolidated.xlsx': 'SUD_LIFE',
    'TATA_AIA_LIFE_INSURANCE_Consolidated.xlsx': 'TATA_AIA_LIFE',
}

def compute_checksum(file_path: str) -> str:
    """Computes SHA256 checksum of the file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

class WorkbookIngestor:
    def __init__(self, db_manager, target_schedules: Optional[List[str]] = None):
        self.db = db_manager
        # Default to "ALL" to ingest all L-schedules across the workbook
        self.target_schedules = target_schedules or ["ALL"]
        self._load_taxonomy_cache()

    def _load_taxonomy_cache(self):
        """Loads compiled regex aliases and line item metadata from database."""
        self.aliases = []  # [(schedule_code, compiled_regex, line_item_id)]
        rows = self.db.execute("SELECT schedule_code, regex_pattern, line_item_id FROM dim_line_item_alias").fetchall()
        for r in rows:
            self.aliases.append((r["schedule_code"], re.compile(r["regex_pattern"], re.I), r["line_item_id"]))

        # Line item metadata
        self.line_items = {}
        li_rows = self.db.execute("SELECT line_item_id, aggregation_type, is_leaf, is_total, is_subtotal, normal_balance_sign FROM dim_line_item").fetchall()
        for r in li_rows:
            self.line_items[r["line_item_id"]] = dict(r)

    def match_line_item(self, schedule_code: str, cleaned_label: str) -> Optional[str]:
        """Matches cleaned particulars text against taxonomy aliases."""
        for sched, regex, li_id in self.aliases:
            if sched == schedule_code and regex.search(cleaned_label):
                return li_id
        return None

    def _get_or_create_line_item(self, schedule_code: str, cleaned_label: str, is_total: int, is_subtotal: int) -> Optional[str]:
        """
        Dynamically registers line items in dim_line_item for any IRDAI schedule (L-1 to L-45).
        Ensures complete schema normalization and zero loss across all statements.
        """
        if not cleaned_label:
            return None

        sched_code = schedule_code.strip()

        # Determine stock vs flow vs ratio vs count
        balance_sheet_scheds = {
            'L-3', 'L-3S', 'L-8', 'L-8A', 'L-9', 'L-9A', 'L-9B', 'L-10', 'L-10A', 'L-10B',
            'L-11', 'L-12', 'L-13', 'L-14', 'L-14A', 'L-15', 'L-16', 'L-17', 'L-18', 'L-19',
            'L-20', 'L-21', 'L-24', 'L-26', 'L-27', 'L-27T', 'L-28', 'L-29', 'L-32', 'L-33', 'L-35'
        }
        ratio_scheds = {'L-22', 'L-38'}

        # Ensure schedule exists in dim_statement_schedule
        is_bs = 1 if sched_code in balance_sheet_scheds else 0
        self.db.execute("""
            INSERT OR IGNORE INTO dim_statement_schedule (schedule_code, schedule_name, statement_type, is_balance_sheet_schedule)
            VALUES (?, ?, 'SCHEDULE_BREAKDOWN', ?)
        """, (sched_code, f"Schedule {sched_code}", is_bs))

        lbl_lower = cleaned_label.lower()
        if sched_code in balance_sheet_scheds:
            agg_type = "POINT_IN_TIME_STOCK"
        elif sched_code in ratio_scheds or "ratio" in lbl_lower or "%" in cleaned_label:
            agg_type = "RATIO_NON_ADDITIVE"
        elif any(w in lbl_lower for w in ("number of", "lives", "count", "nos")):
            agg_type = "COUNT_ADDITIVE"
        else:
            agg_type = "FLOW_ADDITIVE"

        # Generate stable ID from schedule and cleaned label
        clean_slug = re.sub(r"[^A-Za-z0-9]+", "_", cleaned_label).strip("_").upper()
        if not clean_slug:
            clean_slug = "METRIC"
        clean_slug = clean_slug[:45]
        sched_prefix = re.sub(r"[^A-Za-z0-9]", "", sched_code)
        dynamic_id = f"{sched_prefix}_{clean_slug}"[:64]

        if dynamic_id not in self.line_items:
            is_leaf = 0 if (is_total or is_subtotal) else 1
            self.db.execute("""
                INSERT OR IGNORE INTO dim_line_item (
                    line_item_id, schedule_code, canonical_code, canonical_label,
                    statement_section, classification_axis, hierarchy_level,
                    is_leaf, is_total, is_subtotal, normal_balance_sign,
                    aggregation_type, display_order
                ) VALUES (?, ?, ?, ?, 'SCHEDULE_BREAKDOWN', 'PRIMARY_BREAKDOWN', 1, ?, ?, ?, 1, ?, 999)
            """, (dynamic_id, sched_code, dynamic_id, cleaned_label[:120], is_leaf, is_total, is_subtotal, agg_type))
            self.db.commit()

            self.line_items[dynamic_id] = {
                "line_item_id": dynamic_id,
                "aggregation_type": agg_type,
                "is_leaf": is_leaf,
                "is_total": is_total,
                "is_subtotal": is_subtotal,
                "normal_balance_sign": 1
            }

        return dynamic_id

    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """
        Executes full ingestion pipeline for an individual Excel file across all L schedules.
        """
        file_name = os.path.basename(file_path)
        company_id = FILE_TO_COMPANY.get(file_name)
        if not company_id:
            raise ValueError(f"Unknown insurer file: {file_name}. Not in mapping directory.")

        checksum = compute_checksum(file_path)

        # 1. Start audit batch
        cursor = self.db.execute("""
            INSERT INTO audit_etl_batches (source_file_path, source_file_checksum, status)
            VALUES (?, ?, 'RUNNING')
        """, (file_path, checksum))
        batch_id = cursor.lastrowid
        self.db.commit()

        total_processed = 0
        total_quarantined = 0
        periods_seen = set()

        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)

        # Discover all L sheets in workbook
        if self.target_schedules and "ALL" not in self.target_schedules:
            schedules_to_process = [s for s in self.target_schedules if s in wb.sheetnames]
        else:
            schedules_to_process = [s for s in wb.sheetnames if s.upper().startswith("L-") or re.match(r"^L\d+", s, re.I)]

        for sched in schedules_to_process:
            ws = wb[sched]
            blocks = parse_worksheet_blocks(ws, sched)

            for block in blocks:
                # Ensure valid period
                if "UNKNOWN" in block.period_id:
                    continue
                periods_seen.add(block.period_id)

                # Record stage_tabular_blocks
                self.db.execute("""
                    INSERT INTO stage_tabular_blocks (
                        batch_id, source_file, sheet_name, company_id, period_id, schedule_code,
                        start_col_idx, end_col_idx, start_row_idx, end_row_idx, detected_unit_id, unit_multiplier
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    batch_id, file_name, sched, company_id, block.period_id, sched,
                    block.start_col, block.end_col, block.anchor_row, block.anchor_row + len(block.rows),
                    block.unit_id, block.multiplier
                ))

                for r_data in block.rows:
                    cleaned_lbl = r_data["cleaned_particulars"]
                    raw_lbl = r_data["raw_particulars"]
                    line_item_id = self.match_line_item(sched, cleaned_lbl)

                    if not line_item_id:
                        line_item_id = self._get_or_create_line_item(sched, cleaned_lbl, r_data["is_total"], r_data["is_subtotal"])

                    if line_item_id:
                        li_meta = self.line_items.get(line_item_id, {})
                        agg_type = li_meta.get("aggregation_type", "FLOW_ADDITIVE")
                        is_monetary = agg_type not in ("RATIO_NON_ADDITIVE", "COUNT_ADDITIVE")

                        # Extract numbers
                        q_raw = r_data["numeric_values"].get("quarter")
                        ytd_raw = r_data["numeric_values"].get("ytd")
                        tot_raw = r_data["numeric_values"].get("total")

                        # Handle total column if quarter was not present
                        if q_raw is None and tot_raw is not None:
                            q_raw = tot_raw

                        # Scale amounts
                        q_scaled = apply_unit_scale(q_raw, block.multiplier, is_monetary)
                        ytd_scaled = apply_unit_scale(ytd_raw, block.multiplier, is_monetary)
                        pit_scaled = None

                        if agg_type == "POINT_IN_TIME_STOCK":
                            pit_scaled = q_scaled or ytd_scaled
                            q_scaled = None
                            ytd_scaled = None
                        elif agg_type == "RATIO_NON_ADDITIVE":
                            pit_scaled = normalize_ratio(q_raw or ytd_raw)
                            q_scaled = None
                            ytd_scaled = None

                        raw_rep = q_raw if q_raw is not None else ytd_raw

                        # Insert into fact_financial_statement using ON CONFLICT DO UPDATE RETURNING fact_id
                        cur_fact = self.db.execute("""
                            INSERT INTO fact_financial_statement (
                                company_id, period_id, schedule_code, line_item_id, segment_id,
                                filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                raw_reported_amount, quarter_amount_lakhs, ytd_amount_lakhs,
                                point_in_time_amount_lakhs, data_quality_status, statement_version_id,
                                is_active, valid_from_batch_id
                            ) VALUES (?, ?, ?, ?, 'TOTAL', ?, 'AS_REPORTED_ORIGINAL', ?, ?, ?, ?, ?, ?, 'VERIFIED', 1, 1, ?)
                            ON CONFLICT (company_id, period_id, schedule_code, line_item_id, segment_id, reporting_basis, filing_period_id, statement_version_id)
                            DO UPDATE SET
                                quarter_amount_lakhs = COALESCE(excluded.quarter_amount_lakhs, fact_financial_statement.quarter_amount_lakhs),
                                ytd_amount_lakhs = COALESCE(excluded.ytd_amount_lakhs, fact_financial_statement.ytd_amount_lakhs),
                                point_in_time_amount_lakhs = COALESCE(excluded.point_in_time_amount_lakhs, fact_financial_statement.point_in_time_amount_lakhs),
                                updated_at = CURRENT_TIMESTAMP
                            RETURNING fact_id;
                        """, (
                            company_id, block.period_id, sched, line_item_id, block.period_id,
                            block.unit_id, block.multiplier, raw_rep, q_scaled, ytd_scaled,
                            pit_scaled, batch_id
                        ))
                        fact_row = cur_fact.fetchone()
                        fact_id = fact_row[0] if fact_row else None

                        if fact_id:
                            # Record cell-level lineage
                            cell_addr = r_data["particulars_cell_address"]
                            cell_hash = hashlib.sha256(f"{file_name}:{sched}:{cell_addr}:{raw_lbl}".encode("utf-8")).hexdigest()
                            self.db.execute("""
                                INSERT INTO fact_cell_lineage (
                                    fact_id, source_file, sheet_name, row_idx, col_idx, cell_address,
                                    raw_particulars_text, raw_cell_value, cell_checksum
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                fact_id, file_name, sched, r_data["row_idx"], block.particulars_col,
                                cell_addr, raw_lbl, str(raw_rep), cell_hash
                            ))
                            total_processed += 1

                    else:
                        # Log unmapped taxonomy to quarantine
                        self.db.execute("""
                            INSERT INTO quarantine_unmapped_taxonomy (
                                batch_id, source_file, sheet_name, row_idx, schedule_code,
                                period_id, company_id, raw_particulars
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            batch_id, file_name, sched, r_data["row_idx"], sched,
                            block.period_id, company_id, raw_lbl
                        ))
                        total_quarantined += 1

        wb.close()
        self.db.commit()

        # 2. Run Financial Reconciliations across ingested periods
        total_discrepancies = 0
        for p_id in periods_seen:
            disc = reconcile_company_period(self.db, batch_id, company_id, p_id)
            total_discrepancies += len(disc)

        # 3. Finalize audit batch
        status = "COMPLETED_WITH_WARNINGS" if total_discrepancies > 0 else "COMPLETED"
        self.db.execute("""
            UPDATE audit_etl_batches
            SET status = ?, total_records_processed = ?, total_records_quarantined = ?, batch_end_timestamp = CURRENT_TIMESTAMP
            WHERE batch_id = ?
        """, (status, total_processed, total_quarantined, batch_id))
        self.db.commit()

        return {
            "batch_id": batch_id,
            "company_id": company_id,
            "file_name": file_name,
            "records_processed": total_processed,
            "records_quarantined": total_quarantined,
            "reconciliation_discrepancies": total_discrepancies,
            "status": status
        }
