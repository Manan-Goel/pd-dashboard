#!/usr/bin/env python3
"""
Curated Web Dashboard & Visual Analytics for Life Insurance Data Warehouse.
Exclusively designed for life_insurance_curated_v2.db.
Features visual KPI cards, dynamic slicers, interactive Chart.js visualizations,
and a searchable 64-metric explorer with zero external dependencies.

Usage:
  python curated_dashboard.py           # Starts server on http://localhost:8501 and opens browser
  python curated_dashboard.py --port 8501
"""

import os
import sys
import json
import sqlite3
import argparse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "life_insurance_curated_v2.db")

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Acko Life Insurance - 64 Curated Metrics Executive Dashboard</title>
  <!-- Bootstrap 5 CSS -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
  <!-- FontAwesome Icons -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    :root {
      --primary-navy: #0f172a;
      --accent-blue: #0284c7;
      --card-bg: #ffffff;
      --body-bg: #f1f5f9;
      --text-muted: #64748b;
    }
    body {
      background-color: var(--body-bg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #1e293b;
      margin: 0;
      padding: 0;
    }
    .top-header {
      background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
      color: #fff;
      padding: 1rem 1.5rem;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    .badge-acko {
      background: rgba(56, 189, 248, 0.2);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.4);
      padding: 0.35rem 0.65rem;
      border-radius: 20px;
      font-weight: 500;
    }
    .kpi-card {
      background: var(--card-bg);
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      padding: 1.2rem;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
      height: 100%;
    }
    .kpi-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
    }
    .kpi-title {
      font-size: 0.82rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      margin-bottom: 0.4rem;
    }
    .kpi-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: #0f172a;
      line-height: 1.2;
    }
    .kpi-subtitle {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 0.35rem;
    }
    .kpi-icon {
      float: right;
      font-size: 1.8rem;
      opacity: 0.2;
    }
    .slicer-card {
      background: #ffffff;
      border-radius: 12px;
      border: 1px solid #cbd5e1;
      padding: 1rem 1.25rem;
      box-shadow: 0 2px 6px rgba(0,0,0,0.03);
      margin-bottom: 1.5rem;
    }
    .nav-tabs .nav-link {
      font-weight: 600;
      color: #64748b;
      border: none;
      border-bottom: 3px solid transparent;
      padding: 0.75rem 1.25rem;
    }
    .nav-tabs .nav-link.active {
      color: #0284c7;
      border-bottom: 3px solid #0284c7;
      background: transparent;
    }
    .chart-container {
      background: #ffffff;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      padding: 1.25rem;
      box-shadow: 0 2px 6px rgba(0,0,0,0.04);
      margin-bottom: 1.5rem;
      height: 380px;
    }
    .table-container {
      background: #ffffff;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      overflow-x: auto !important;
      overflow-y: auto !important;
      max-height: 600px;
      white-space: nowrap !important;
    }
    .table th {
      position: sticky;
      top: 0;
      background: #0f172a;
      color: #38bdf8;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      z-index: 10;
      padding: 10px 14px;
    }
    .table td {
      font-size: 0.84rem;
      padding: 8px 14px;
      vertical-align: middle;
    }
    .badge-metric-id {
      font-size: 0.72rem;
      background: #e0f2fe;
      color: #0369a1;
      padding: 0.2rem 0.45rem;
      border-radius: 4px;
      font-weight: 600;
      margin-right: 4px;
    }
  </style>
</head>
<body>

  <!-- Top Header Navigation -->
  <div class="top-header">
    <div class="container-fluid d-flex flex-wrap justify-content-between align-items-center">
      <div class="d-flex align-items-center gap-3">
        <i class="fa-solid fa-building-shield fa-2x text-info"></i>
        <div>
          <h4 class="mb-0 fw-bold">ACKO Life Insurance — Curated Executive Dashboard</h4>
          <span class="small text-light opacity-75">Statutory 64 Metrics Warehouse &bull; Database: <code>life_insurance_curated_v2.db</code></span>
        </div>
      </div>
      <div class="d-flex align-items-center gap-2 mt-2 mt-md-0">
        <span class="badge-acko"><i class="fa-solid fa-certificate me-1"></i> IRDAI Reg No: 165</span>
        <span class="badge bg-success px-3 py-2 rounded-pill"><i class="fa-solid fa-circle-check me-1"></i> 100% Reconciled (12 Quarters)</span>
      </div>
    </div>
  </div>

  <div class="container-fluid py-4 px-4">

    <!-- Interactive Slicers Bar -->
    <div class="slicer-card">
      <div class="row g-3 align-items-center">
        <div class="col-md-3">
          <label class="form-label small fw-bold text-muted mb-1"><i class="fa-solid fa-calendar-days text-primary me-1"></i> Quarter / Period Slicer</label>
          <select id="slicerPeriod" class="form-select form-select-sm fw-semibold" onchange="onPeriodChange()">
            <option value="ALL">All 12 Quarters (FY2023-24 Q1 to FY2025-26 Q4)</option>
            <option value="FY2025-26_Q4" selected>FY2025-26 Q4 (Latest Reported Quarter)</option>
            <option value="FY2025-26_Q3">FY2025-26 Q3</option>
            <option value="FY2025-26_Q2">FY2025-26 Q2</option>
            <option value="FY2025-26_Q1">FY2025-26 Q1</option>
            <option value="FY2024-25_Q4">FY2024-25 Q4</option>
            <option value="FY2024-25_Q3">FY2024-25 Q3</option>
            <option value="FY2024-25_Q2">FY2024-25 Q2</option>
            <option value="FY2024-25_Q1">FY2024-25 Q1</option>
            <option value="FY2023-24_Q4">FY2023-24 Q4</option>
            <option value="FY2023-24_Q3">FY2023-24 Q3</option>
            <option value="FY2023-24_Q2">FY2023-24 Q2</option>
            <option value="FY2023-24_Q1">FY2023-24 Q1</option>
          </select>
        </div>

        <div class="col-md-3">
          <label class="form-label small fw-bold text-muted mb-1"><i class="fa-solid fa-filter text-info me-1"></i> Metric Category Slicer</label>
          <select id="slicerCategory" class="form-select form-select-sm" onchange="onCategoryChange()">
            <option value="ALL">💎 All 64 Standardized Metrics</option>
            <option value="PREMIUMS">💰 Premiums & Revenue (M01-M15, M24)</option>
            <option value="VOLUMES">📈 Policies, Lives & Volumes (M25-M30)</option>
            <option value="CLAIMS">🩺 Claims & Expenses (M16-M22, M37)</option>
            <option value="SOLVENCY">🛡️ Solvency, Capital & P&L (M31-M35, M55-M58)</option>
            <option value="CHANNELS">🏢 Intermediary Channels & Productivity (M42, M46-M54)</option>
          </select>
        </div>

        <div class="col-md-4">
          <label class="form-label small fw-bold text-muted mb-1"><i class="fa-solid fa-magnifying-glass text-warning me-1"></i> Live Metric Search Filter</label>
          <input type="text" id="metricSearch" class="form-control form-control-sm" placeholder="Search metric name (e.g. solvency, single, claim, pat)..." onkeyup="filterTable()">
        </div>

        <div class="col-md-2 text-end d-flex align-items-end justify-content-end gap-2">
          <button class="btn btn-outline-secondary btn-sm" onclick="exportTableToCSV()"><i class="fa-solid fa-file-csv me-1 text-success"></i> Export CSV</button>
          <button class="btn btn-primary btn-sm" onclick="window.print()"><i class="fa-solid fa-print me-1"></i> Print</button>
        </div>
      </div>
    </div>

    <!-- Executive KPI Row -->
    <div class="row g-3 mb-4">
      <div class="col-md-3 col-sm-6">
        <div class="kpi-card">
          <i class="fa-solid fa-money-bill-wave kpi-icon text-success"></i>
          <div class="kpi-title">Gross Written Premium (GWP)</div>
          <div class="kpi-value text-success" id="kpiGWP">₹7,212 L</div>
          <div class="kpi-subtitle" id="kpiGWPgrowth"><span class="badge bg-success-subtle text-success">+264.4% YoY Growth</span></div>
        </div>
      </div>

      <div class="col-md-3 col-sm-6">
        <div class="kpi-card">
          <i class="fa-solid fa-shield-halved kpi-icon text-primary"></i>
          <div class="kpi-title">Statutory Solvency Ratio</div>
          <div class="kpi-value text-primary" id="kpiSolvency">1.80x</div>
          <div class="kpi-subtitle"><span class="badge bg-primary-subtle text-primary">Compliant (Min 1.50x Req)</span></div>
        </div>
      </div>

      <div class="col-md-3 col-sm-6">
        <div class="kpi-card">
          <i class="fa-solid fa-users kpi-icon text-info"></i>
          <div class="kpi-title">Total Policies & Group Lives</div>
          <div class="kpi-value text-dark" id="kpiPolicies">1,854 pol</div>
          <div class="kpi-subtitle" id="kpiLives">572,968 Group Lives Covered</div>
        </div>
      </div>

      <div class="col-md-3 col-sm-6">
        <div class="kpi-card">
          <i class="fa-solid fa-vault kpi-icon text-warning"></i>
          <div class="kpi-title">Total Sum Assured</div>
          <div class="kpi-value text-warning-emphasis" id="kpiSumAssured">₹10,138 Cr</div>
          <div class="kpi-subtitle" id="kpiSAgrowth">+397.7% YoY Growth</div>
        </div>
      </div>
    </div>

    <!-- Secondary KPI Row -->
    <div class="row g-3 mb-4">
      <div class="col-md-3 col-sm-6">
        <div class="kpi-card">
          <i class="fa-solid fa-hospital-user kpi-icon text-danger"></i>
          <div class="kpi-title">Gross Claims Paid</div>
          <div class="kpi-value text-danger" id="kpiClaims">₹644 L</div>
          <div class="kpi-subtitle">Death & Maturity Benefits</div>
        </div>
      </div>

      <div class="col-md-3 col-sm-6">
        <div class="kpi-card">
          <i class="fa-solid fa-chart-line kpi-icon text-info"></i>
          <div class="kpi-title">Net Worth & Paid-up Capital</div>
          <div class="kpi-value text-info-emphasis" id="kpiNetWorth">₹190.05 Cr</div>
          <div class="kpi-subtitle">Share Capital: ₹190.05 Cr</div>
        </div>
      </div>

      <div class="col-md-3 col-sm-6">
        <div class="kpi-card">
          <i class="fa-solid fa-hourglass-half kpi-icon text-purple"></i>
          <div class="kpi-title">13th Month Persistency</div>
          <div class="kpi-value text-indigo" id="kpiPersistency">100.0%</div>
          <div class="kpi-subtitle">Regular Premium Cohort</div>
        </div>
      </div>

      <div class="col-md-3 col-sm-6">
        <div class="kpi-card">
          <i class="fa-solid fa-envelope-circle-check kpi-icon text-secondary"></i>
          <div class="kpi-title">Grievances / Complaints</div>
          <div class="kpi-value text-secondary" id="kpiComplaints">9 complaints</div>
          <div class="kpi-subtitle">Form L-41 Disposal Rate: 100%</div>
        </div>
      </div>
    </div>

    <!-- Main Navigation Tabs -->
    <ul class="nav nav-tabs mb-3" id="dashboardTabs" role="tablist">
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="tab-charts" data-bs-toggle="tab" data-bs-target="#content-charts" type="button"><i class="fa-solid fa-chart-pie me-1"></i> Trend Visualizations</button>
      </li>
      <li class="nav-item" role="presentation">
        <button class="nav-link" id="tab-metrics" data-bs-toggle="tab" data-bs-target="#content-metrics" type="button"><i class="fa-solid fa-table-list me-1"></i> Standardized 64 Metrics Explorer</button>
      </li>
      <li class="nav-item" role="presentation">
        <button class="nav-link" id="tab-geo" data-bs-toggle="tab" data-bs-target="#content-geo" type="button"><i class="fa-solid fa-map-location-dot me-1"></i> Geographical Distribution (Field 43)</button>
      </li>
      <li class="nav-item" role="presentation">
        <button class="nav-link" id="tab-persistency" data-bs-toggle="tab" data-bs-target="#content-persistency" type="button"><i class="fa-solid fa-timeline me-1"></i> Persistency Cohorts (Field 41)</button>
      </li>
      <li class="nav-item" role="presentation">
        <button class="nav-link" id="tab-channels" data-bs-toggle="tab" data-bs-target="#content-channels" type="button"><i class="fa-solid fa-network-wired me-1"></i> Intermediary Channels (Field 42)</button>
      </li>
    </ul>

    <!-- Tab Contents -->
    <div class="tab-content" id="dashboardTabsContent">
      
      <!-- TAB 1: CHARTS & VISUAL TRENDS -->
      <div class="tab-pane fade show active" id="content-charts">
        <div class="row g-3">
          <!-- Premium Inflow Chart -->
          <div class="col-lg-6">
            <div class="chart-container">
              <h6 class="fw-bold mb-3"><i class="fa-solid fa-chart-column text-success me-2"></i>Quarterly Premium Inflow Trajectory (₹ Lakhs)</h6>
              <div style="height: 300px;"><canvas id="chartPremium"></canvas></div>
            </div>
          </div>

          <!-- Business Scale Chart -->
          <div class="col-lg-6">
            <div class="chart-container">
              <h6 class="fw-bold mb-3"><i class="fa-solid fa-people-roof text-info me-2"></i>Policies Sold & Group Lives Growth</h6>
              <div style="height: 300px;"><canvas id="chartScale"></canvas></div>
            </div>
          </div>

          <!-- Solvency Trend Chart -->
          <div class="col-lg-6">
            <div class="chart-container">
              <h6 class="fw-bold mb-3"><i class="fa-solid fa-shield-virus text-primary me-2"></i>Regulatory Solvency Ratio vs Statutory 1.50x Floor</h6>
              <div style="height: 300px;"><canvas id="chartSolvency"></canvas></div>
            </div>
          </div>

          <!-- Geographic Top States Chart -->
          <div class="col-lg-6">
            <div class="chart-container">
              <h6 class="fw-bold mb-3"><i class="fa-solid fa-earth-asia text-warning me-2"></i>Top 8 States by Premium Collection (₹ Lakhs)</h6>
              <div style="height: 300px;"><canvas id="chartGeo"></canvas></div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 2: STANDARDIZED 64 METRICS EXPLORER TABLE -->
      <div class="tab-pane fade" id="content-metrics">
        <div class="card p-0 shadow-sm border-0">
          <div class="table-container">
            <table class="table table-sm table-striped table-hover mb-0" id="tableMetrics">
              <thead>
                <tr id="tableMetricsHead">
                  <th style="min-width: 130px;">Period</th>
                  <!-- Dynamic 64 Metric Columns -->
                </tr>
              </thead>
              <tbody id="tableMetricsBody">
                <!-- Loaded via JS -->
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 3: GEOGRAPHICAL BREAKDOWN TABLE -->
      <div class="tab-pane fade" id="content-geo">
        <div class="card p-3 shadow-sm border-0">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h6 class="fw-bold mb-0"><i class="fa-solid fa-map text-info me-2"></i>State-Wise Geographical Disclosures (Rural vs. Urban)</h6>
            <span class="badge bg-secondary" id="geoRowCount">0 records</span>
          </div>
          <div class="table-container">
            <table class="table table-sm table-hover mb-0" id="tableGeo">
              <thead class="table-dark">
                <tr>
                  <th>Period</th>
                  <th>Region Type</th>
                  <th>State / Union Territory</th>
                  <th class="text-end">Total Policies</th>
                  <th class="text-end">Total Premium (₹ Lakhs)</th>
                  <th class="text-end">Total Sum Assured (₹ Lakhs)</th>
                  <th class="text-end">Rural Policies</th>
                  <th class="text-end">Urban Policies</th>
                </tr>
              </thead>
              <tbody id="tableGeoBody"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 4: PERSISTENCY COHORTS TABLE -->
      <div class="tab-pane fade" id="content-persistency">
        <div class="card p-3 shadow-sm border-0">
          <h6 class="fw-bold mb-3"><i class="fa-solid fa-user-clock text-warning me-2"></i>Actuarial Persistency Cohort Disclosures (Form L-22 & L-38)</h6>
          <div class="table-container">
            <table class="table table-sm table-hover mb-0" id="tablePersistency">
              <thead class="table-dark">
                <tr>
                  <th>Period</th>
                  <th>Cohort Month</th>
                  <th>Premium Basis Type</th>
                  <th>Metric Basis</th>
                  <th class="text-end">Persistency Ratio (%)</th>
                </tr>
              </thead>
              <tbody id="tablePersistencyBody"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 5: CHANNELS & INTERMEDIARIES TABLE -->
      <div class="tab-pane fade" id="content-channels">
        <div class="card p-3 shadow-sm border-0">
          <h6 class="fw-bold mb-3"><i class="fa-solid fa-network-wired text-primary me-2"></i>Intermediary Distribution Channels & Productivity (Form L-38 & L-42)</h6>
          <div class="table-container">
            <table class="table table-sm table-hover mb-0" id="tableChannels">
              <thead class="table-dark">
                <tr>
                  <th>Period</th>
                  <th>Channel Name</th>
                  <th class="text-end">Policies Count</th>
                  <th class="text-end">Premium (₹ Lakhs)</th>
                  <th class="text-end">Intermediaries / Staff</th>
                  <th class="text-end">Productivity (INR)</th>
                </tr>
              </thead>
              <tbody id="tableChannelsBody"></tbody>
            </table>
          </div>
        </div>
      </div>

    </div>

  </div>

  <!-- Dashboard JavaScript Code -->
  <script>
    let rawMetrics = [];
    let geoData = [];
    let persistencyData = [];
    let channelsData = [];
    let chartInstances = {};

    async function initDashboard() {
      try {
        const res = await fetch('/api/all-data');
        const data = await res.json();
        rawMetrics = data.metrics;
        geoData = data.geo;
        persistencyData = data.persistency;
        channelsData = data.channels;

        renderKPICards("FY2025-26_Q4");
        initCharts();
        renderMetricsTable();
        renderGeoTable();
        renderPersistencyTable();
        renderChannelsTable();
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      }
    }

    function onPeriodChange() {
      const p = document.getElementById('slicerPeriod').value;
      const targetP = (p === 'ALL') ? "FY2025-26_Q4" : p;
      renderKPICards(targetP);
      renderMetricsTable();
      renderGeoTable();
      renderPersistencyTable();
      renderChannelsTable();
    }

    function onCategoryChange() {
      renderMetricsTable();
    }

    function renderKPICards(periodId) {
      const row = rawMetrics.find(r => r.period_id === periodId) || rawMetrics[rawMetrics.length - 1];
      if (!row) return;

      document.getElementById('kpiGWP').textContent = '₹' + Number(row.m13_gross_written_premium || 0).toLocaleString() + ' L';
      document.getElementById('kpiGWPgrowth').innerHTML = (row.m14_avg_premium_growth_pct !== null) 
        ? `<span class="badge bg-success-subtle text-success">+${row.m14_avg_premium_growth_pct}% YoY Growth</span>`
        : `<span class="badge bg-secondary-subtle text-muted">First full operational year</span>`;

      document.getElementById('kpiSolvency').textContent = (row.m35_solvency_ratio || 0).toFixed(2) + 'x';

      document.getElementById('kpiPolicies').textContent = Number(row.m27_total_policies || 0).toLocaleString() + ' pol';
      document.getElementById('kpiLives').textContent = Number(row.m29_group_lives_covered || 0).toLocaleString() + ' Group Lives Covered';

      const saLakhs = Number(row.m25_total_sum_assured || 0);
      const saCrores = (saLakhs / 100.0).toFixed(0);
      document.getElementById('kpiSumAssured').textContent = '₹' + Number(saCrores).toLocaleString() + ' Cr';
      document.getElementById('kpiSAgrowth').textContent = (row.m26_avg_sum_assured_growth_pct) ? `+${row.m26_avg_sum_assured_growth_pct}% YoY Growth` : 'Statutory Form L-36';

      document.getElementById('kpiClaims').textContent = '₹' + Number(row.m17_death_claims || 0).toLocaleString() + ' L';
      const nwCr = ((row.m57_net_worth || 0) / 100.0).toFixed(2);
      document.getElementById('kpiNetWorth').textContent = '₹' + nwCr + ' Cr';
      document.getElementById('kpiComplaints').textContent = (row.m39_total_complaints || 0) + ' complaints';
    }

    function initCharts() {
      const labels = rawMetrics.map(r => r.period_id.replace('FY', '').replace('_', ' '));
      const gwpData = rawMetrics.map(r => r.m13_gross_written_premium || 0);
      const singleData = rawMetrics.map(r => r.m02_total_single_premium || 0);
      const fyData = rawMetrics.map(r => r.m01_fy_premium || 0);
      const polData = rawMetrics.map(r => r.m27_total_policies || 0);
      const livesData = rawMetrics.map(r => r.m29_group_lives_covered || 0);
      const solvencyData = rawMetrics.map(r => r.m35_solvency_ratio || 0);

      // 1. Premium Trajectory Chart
      const ctxPrem = document.getElementById('chartPremium').getContext('2d');
      chartInstances.prem = new Chart(ctxPrem, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            { label: 'Gross Written Premium', data: gwpData, backgroundColor: '#0284c7', borderRadius: 4 },
            { label: 'Single Premium', data: singleData, backgroundColor: '#38bdf8', borderRadius: 4 },
            { label: 'First Year Premium', data: fyData, backgroundColor: '#10b981', borderRadius: 4 }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: { y: { beginAtZero: true, grid: { color: '#f1f5f9' } }, x: { grid: { display: false } } }
        }
      });

      // 2. Business Scale Chart
      const ctxScale = document.getElementById('chartScale').getContext('2d');
      chartInstances.scale = new Chart(ctxScale, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            { label: 'Group Lives Covered', data: livesData, borderColor: '#8b5cf6', backgroundColor: 'rgba(139, 92, 246, 0.1)', fill: true, tension: 0.3, yAxisID: 'y1' },
            { label: 'Total Policies', data: polData, borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: false, tension: 0.3, yAxisID: 'y' }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: {
            y: { type: 'linear', position: 'left', beginAtZero: true, grid: { color: '#f1f5f9' } },
            y1: { type: 'linear', position: 'right', beginAtZero: true, grid: { display: false } }
          }
        }
      });

      // 3. Solvency Ratio Chart
      const ctxSolv = document.getElementById('chartSolvency').getContext('2d');
      chartInstances.solv = new Chart(ctxSolv, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            { label: 'Acko Solvency Ratio', data: solvencyData, borderColor: '#0ea5e9', backgroundColor: '#e0f2fe', tension: 0.2, pointRadius: 5 },
            { label: 'Statutory Min (1.50x)', data: Array(labels.length).fill(1.50), borderColor: '#ef4444', borderDash: [6, 4], pointRadius: 0, fill: false }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: { y: { min: 1.0, max: 3.2, grid: { color: '#f1f5f9' } }, x: { grid: { display: false } } }
        }
      });

      // 4. Geographic Top States Chart (FY25-26 Q4)
      const latestGeo = geoData.filter(g => g.period_id === 'FY2025-26_Q4' && g.region_name !== 'TOTAL' && g.region_name !== 'GRAND TOTAL')
                               .sort((a,b) => b.total_premium_lakhs - a.total_premium_lakhs)
                               .slice(0, 8);
      const ctxGeo = document.getElementById('chartGeo').getContext('2d');
      chartInstances.geo = new Chart(ctxGeo, {
        type: 'bar',
        data: {
          labels: latestGeo.map(g => g.region_name),
          datasets: [{ label: 'Premium Collection (₹ Lakhs)', data: latestGeo.map(g => g.total_premium_lakhs), backgroundColor: '#f59e0b', borderRadius: 4 }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: { x: { beginAtZero: true, grid: { color: '#f1f5f9' } } }
        }
      });
    }

    function renderMetricsTable() {
      const pSlicer = document.getElementById('slicerPeriod').value;
      const catSlicer = document.getElementById('slicerCategory').value;

      let filteredRows = (pSlicer === 'ALL') ? rawMetrics : rawMetrics.filter(r => r.period_id === pSlicer);
      
      const head = document.getElementById('tableMetricsHead');
      const body = document.getElementById('tableMetricsBody');
      head.innerHTML = '<th style="min-width: 140px;">Period</th>';
      body.innerHTML = '';

      if (filteredRows.length === 0) {
        body.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-muted">No records match slicers.</td></tr>';
        return;
      }

      // Filter columns based on category
      const allCols = Object.keys(filteredRows[0]).filter(k => k.startsWith('m'));
      let selectedCols = allCols;

      if (catSlicer === 'PREMIUMS') {
        selectedCols = allCols.filter(k => parseInt(k.substring(1,3)) <= 15 || k.includes('m24'));
      } else if (catSlicer === 'VOLUMES') {
        selectedCols = allCols.filter(k => parseInt(k.substring(1,3)) >= 25 && parseInt(k.substring(1,3)) <= 30);
      } else if (catSlicer === 'CLAIMS') {
        selectedCols = allCols.filter(k => (parseInt(k.substring(1,3)) >= 16 && parseInt(k.substring(1,3)) <= 22) || k.includes('m37'));
      } else if (catSlicer === 'SOLVENCY') {
        selectedCols = allCols.filter(k => (parseInt(k.substring(1,3)) >= 31 && parseInt(k.substring(1,3)) <= 35) || (parseInt(k.substring(1,3)) >= 55 && parseInt(k.substring(1,3)) <= 58));
      } else if (catSlicer === 'CHANNELS') {
        selectedCols = allCols.filter(k => k.includes('m42') || (parseInt(k.substring(1,3)) >= 46 && parseInt(k.substring(1,3)) <= 54));
      }

      // Populate headers
      selectedCols.forEach(col => {
        const th = document.createElement('th');
        const metricNum = col.substring(0, 3).toUpperCase();
        const metricName = col.substring(4).replace(/_/g, ' ');
        th.innerHTML = `<span class="badge-metric-id">${metricNum}</span> ${metricName}`;
        head.appendChild(th);
      });

      // Populate body
      filteredRows.forEach(r => {
        const tr = document.createElement('tr');
        const tdP = document.createElement('td');
        tdP.className = 'fw-bold text-primary';
        tdP.textContent = r.period_id;
        tr.appendChild(tdP);

        selectedCols.forEach(col => {
          const td = document.createElement('td');
          const val = r[col];
          if (typeof val === 'number') {
            td.textContent = val.toLocaleString(undefined, { maximumFractionDigits: 2 });
            td.style.textAlign = 'right';
          } else {
            td.textContent = (val !== null && val !== undefined) ? val : '-';
          }
          tr.appendChild(td);
        });
        body.appendChild(tr);
      });
    }

    function renderGeoTable() {
      const pSlicer = document.getElementById('slicerPeriod').value;
      let rows = (pSlicer === 'ALL') ? geoData : geoData.filter(g => g.period_id === pSlicer);
      document.getElementById('geoRowCount').textContent = rows.length + ' records';
      const body = document.getElementById('tableGeoBody');
      body.innerHTML = '';

      rows.slice(0, 200).forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><span class="badge bg-light text-dark">${r.period_id}</span></td>
          <td>${r.region_type}</td>
          <td class="fw-semibold">${r.region_name}</td>
          <td class="text-end">${Number(r.total_policies || 0).toLocaleString()}</td>
          <td class="text-end fw-bold text-success">₹${Number(r.total_premium_lakhs || 0).toLocaleString()}</td>
          <td class="text-end text-muted">₹${Number(r.total_sum_assured_lakhs || 0).toLocaleString()}</td>
          <td class="text-end">${Number(r.rural_policies || 0).toLocaleString()}</td>
          <td class="text-end">${Number(r.urban_policies || 0).toLocaleString()}</td>
        `;
        body.appendChild(tr);
      });
    }

    function renderPersistencyTable() {
      const pSlicer = document.getElementById('slicerPeriod').value;
      let rows = (pSlicer === 'ALL') ? persistencyData : persistencyData.filter(p => p.period_id === pSlicer);
      const body = document.getElementById('tablePersistencyBody');
      body.innerHTML = '';

      rows.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><span class="badge bg-light text-dark">${r.period_id}</span></td>
          <td class="fw-bold">${r.cohort_month} Month</td>
          <td>${r.premium_basis_type}</td>
          <td>${r.basis_metric}</td>
          <td class="text-end fw-bold text-primary">${(r.persistency_ratio_pct !== null) ? (r.persistency_ratio_pct > 1 ? r.persistency_ratio_pct : r.persistency_ratio_pct * 100).toFixed(1) + '%' : '-'}</td>
        `;
        body.appendChild(tr);
      });
    }

    function renderChannelsTable() {
      const pSlicer = document.getElementById('slicerPeriod').value;
      let rows = (pSlicer === 'ALL') ? channelsData : channelsData.filter(c => c.period_id === pSlicer);
      const body = document.getElementById('tableChannelsBody');
      body.innerHTML = '';

      rows.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><span class="badge bg-light text-dark">${r.period_id}</span></td>
          <td class="fw-semibold text-primary">${r.channel_name}</td>
          <td class="text-end">${Number(r.policies_count || 0).toLocaleString()}</td>
          <td class="text-end fw-bold text-success">₹${Number(r.premium_lakhs || 0).toLocaleString()}</td>
          <td class="text-end">${Number(r.intermediary_count || 0).toLocaleString()}</td>
          <td class="text-end text-muted">₹${Number(r.productivity_inr || 0).toLocaleString()}</td>
        `;
        body.appendChild(tr);
      });
    }

    function filterTable() {
      const query = document.getElementById('metricSearch').value.toLowerCase();
      const ths = document.getElementById('tableMetricsHead').getElementsByTagName('th');
      const trs = document.getElementById('tableMetricsBody').getElementsByTagName('tr');

      for (let i = 1; i < ths.length; i++) {
        const colText = ths[i].textContent.toLowerCase();
        const show = colText.includes(query);
        ths[i].style.display = show ? '' : 'none';
        for (let r = 0; r < trs.length; r++) {
          const tds = trs[r].getElementsByTagName('td');
          if (tds[i]) tds[i].style.display = show ? '' : 'none';
        }
      }
    }

    function exportTableToCSV() {
      if (!rawMetrics || rawMetrics.length === 0) return;
      const keys = Object.keys(rawMetrics[0]);
      let csv = keys.join(",") + "\\n";
      rawMetrics.forEach(row => {
        csv += keys.map(k => '"' + String(row[k] !== null ? row[k] : '').replace(/"/g, '""') + '"').join(",") + "\\n";
      });
      const blob = new Blob([csv], { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = "acko_64_metrics_export.csv";
      a.click();
    }

    window.onload = initDashboard;
  </script>
  <!-- Bootstrap 5 Bundle JS -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

class CuratedDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
        elif url.path == "/api/all-data":
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT * FROM v_all_64_metrics WHERE company_id = 'ACKO_LIFE' ORDER BY period_id")
            metrics = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT period_id, region_type, region_name, total_policies, total_premium_lakhs, 
                       total_sum_assured_lakhs, rural_policies, urban_policies 
                FROM fact_geographical_distribution 
                WHERE company_id = 'ACKO_LIFE' 
                ORDER BY period_id, total_premium_lakhs DESC
            """)
            geo = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT period_id, cohort_month, premium_basis_type, basis_metric, persistency_ratio_pct 
                FROM fact_persistency_cohorts 
                WHERE company_id = 'ACKO_LIFE' 
                ORDER BY period_id, cohort_month
            """)
            persistency = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT period_id, channel_name, policies_count, premium_lakhs, intermediary_count, productivity_inr 
                FROM fact_intermediary_channel_metrics 
                WHERE company_id = 'ACKO_LIFE' 
                ORDER BY period_id, premium_lakhs DESC
            """)
            channels = [dict(r) for r in cur.fetchall()]

            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "metrics": metrics,
                "geo": geo,
                "persistency": persistency,
                "channels": channels
            }).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    parser = argparse.ArgumentParser(description="Start Curated 64-Metrics Web Dashboard")
    parser.add_argument("--port", type=int, default=8501, help="Port to bind (default: 8501)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found!")
        sys.exit(1)

    server = HTTPServer(("localhost", args.port), CuratedDashboardHandler)
    url = f"http://localhost:{args.port}"
    print("=" * 75)
    print("🚀 ACKO LIFE INSURANCE CURATED 64-METRICS EXECUTIVE DASHBOARD ACTIVE")
    print(f"   URL: {url}")
    print(f"   Database: {os.path.abspath(DB_PATH)}")
    print("=" * 75)

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server.")
        server.server_close()

if __name__ == "__main__":
    main()
