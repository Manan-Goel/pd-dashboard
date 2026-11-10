"""
Master ETL Ingestion Orchestrator for Life Insurance Warehouse.
Discovers and processes all 25 insurance company public disclosure workbooks.
"""

import os
import glob
import time
from typing import List, Dict, Any, Optional
from ..db.database import DatabaseManager
from ..db.seeds import seed_database
from .ingest_workbook import WorkbookIngestor, FILE_TO_COMPANY

class PipelineOrchestrator:
    def __init__(self, db_path: str = "life_insurance.db", engine: str = "sqlite"):
        self.db = DatabaseManager(db_path=db_path, engine=engine)
        self.ingestor = None

    def initialize(self, force: bool = False):
        """Initializes database schema and seeds master dimensions."""
        print(f"Initializing {self.db.engine.upper()} database at '{self.db.db_path}'...")
        self.db.init_schema(force=force)
        seed_database(self.db)
        self.ingestor = WorkbookIngestor(self.db)

    def run_all(self, file_pattern: str = "*.xlsx", target_schedules: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Discovers all Excel files matching pattern and executes batch ingestion.
        """
        if self.ingestor is None:
            self.initialize()

        if target_schedules:
            self.ingestor.target_schedules = target_schedules

        files = sorted(glob.glob(file_pattern))
        print(f"\n================================================================================")
        print(f"STARTING BATCH INGESTION: {len(files)} INSURER WORKBOOKS DETECTED")
        sched_desc = "ALL L-Schedules (L-1 to L-45)" if "ALL" in self.ingestor.target_schedules else ', '.join(self.ingestor.target_schedules)
        print(f"Target Schedules: {sched_desc}")
        print(f"================================================================================\n")

        results = []
        start_time = time.time()

        for idx, f in enumerate(files, 1):
            file_name = os.path.basename(f)
            if file_name not in FILE_TO_COMPANY:
                print(f"[{idx:02d}/{len(files)}] Skipping unrecognized file: {file_name}")
                continue

            print(f"[{idx:02d}/{len(files)}] Ingesting {file_name} ...", end=" ", flush=True)
            f_start = time.time()

            try:
                res = self.ingestor.ingest_file(f)
                f_dur = time.time() - f_start
                print(f"DONE ({f_dur:.1f}s) | Processed: {res['records_processed']:4d} | Quarantined: {res['records_quarantined']:3d} | Status: {res['status']}")
                results.append(res)
            except Exception as e:
                f_dur = time.time() - f_start
                print(f"FAILED ({f_dur:.1f}s) | Error: {e}")
                results.append({
                    "file_name": file_name,
                    "status": "FAILED",
                    "error": str(e)
                })

        total_dur = time.time() - start_time
        self._print_summary_report(results, total_dur)
        return results

    def _print_summary_report(self, results: List[Dict[str, Any]], total_duration: float):
        """Prints a structured summary report of the batch run."""
        print(f"\n================================================================================")
        print(f"BATCH INGESTION RUN REPORT")
        print(f"================================================================================")
        print(f"Total Workbooks Attempted: {len(results)}")
        successful = [r for r in results if r["status"] in ("COMPLETED", "COMPLETED_WITH_WARNINGS")]
        failed = [r for r in results if r["status"] == "FAILED"]
        print(f"Successfully Ingested:    {len(successful)} / {len(results)}")
        print(f"Failed Workbooks:         {len(failed)}")
        total_facts = sum(r.get("records_processed", 0) for r in successful)
        total_quarantined = sum(r.get("records_quarantined", 0) for r in successful)
        print(f"Total Financial Facts:    {total_facts:,}")
        print(f"Total Quarantined Lines:  {total_quarantined:,}")
        print(f"Total Ingestion Duration: {total_duration:.1f} seconds")
        print(f"================================================================================\n")
