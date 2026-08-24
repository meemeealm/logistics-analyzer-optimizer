# Logistics Cost Analyzer - Web Dashboard & Automation Guide (HOWTO)

Welcome to the **Logistics Cost Analyzer Web Dashboard**. This guide explains every interactive feature, automated folder watcher, debouncing mechanism, run-specific packaging system, and structured JSON observability log.

---

## Table of Contents

1. [Overview & Architecture](#overview--architecture)
2. [Automated Input Data Watcher & Debouncing](#automated-input-data-watcher--debouncing)
3. [Artifacts Organization & Timestamped ZIP Packaging](#artifacts-organization--timestamped-zip-packaging)
4. [Structured JSON Logging & Observability](#structured-json-logging--observability)
5. [Header & Quick-Action Controls](#header--quick-action-controls)
6. [Tab 1: Executive Dashboard](#tab-1-executive-dashboard)
7. [Tab 2: Generated Charts (7 Visualizations)](#tab-2-generated-charts)
8. [Tab 3: Data Tables & CSV Exports](#tab-3-data-tables--csv-exports)
9. [Tab 4: Packaged Runs & Archives](#tab-4-packaged-runs--archives)
10. [Tab 5: JSON Logs & Observability](#tab-5-json-logs--observability)
11. [Tab 6: Debounced Watcher Console](#tab-6-debounced-watcher-console)
12. [Tab 7: Terminal & CLI Output](#tab-7-terminal--cli-output)
13. [Tab 8: Code & Documentation Viewer](#tab-8-code--documentation-viewer)

---

## Overview & Architecture

The system operates as an end-to-end data pipeline:
```
input/*.csv ──(3s Debounce Watcher)──> logistics_cost_analyzer.py
                                              │
                                              ▼
                                       reports/runs/<run_id>/
                                              │
                                              ▼
                                    reports/archives/<run_id>.zip
                                              │
                                              ▼
                                logs/pipeline_operations.json.log
```

---

## Automated Input Data Watcher & Debouncing

Script: `input_watcher.py`

* **Automatic Detection**: Continuously monitors the `input/` folder for newly dropped or updated `.csv` files.
* **Debounce Cooldown (3.0 seconds default)**:
  - When a file is copied or written in chunks, rapid OS write events occur.
  - The watcher tracks `mtime` and content changes. It resets its timer until write activity ceases for at least 3.0 seconds.
  - Computes MD5 content hashes to avoid redundant duplicate triggers if the file content has not actually changed.
* **Automatic Execution & Packaging**:
  - Automatically invokes `python logistics_cost_analyzer.py --input input/<file>.csv`.
  - Upon completion, immediately calls `artifacts_handler.py` to organize artifacts and generate a timestamped ZIP.

### Usage:
```bash
# Start watcher with 3-second debounce and 1-second polling:
python input_watcher.py --debounce 3.0 --interval 1.0

# Start and execute immediately on startup:
python input_watcher.py --run-on-start
```

---

## Artifacts Organization & Timestamped ZIP Packaging

Script: `artifacts_handler.py`

* **Run-Specific Directories**:
  - Whenever an analysis completes, all output files (`summary.txt`, `regression_results.txt`, all 7 `.png` charts, and all 4 `.csv` datasets) are copied into a run-specific subfolder: `reports/runs/run_YYYYMMDD_HHMMSS/`.
* **Run Manifest (`run_manifest.json`)**:
  - Generates a metadata JSON file inside the run directory recording execution timestamp, input source, file count, and artifact manifest.
* **Timestamped ZIP Packaging**:
  - Automatically compiles all run artifacts into a compressed archive: `reports/archives/logistics_reports_run_YYYYMMDD_HHMMSS.zip`.
  - Available for one-click downloading from the **"Packaged Runs & ZIPs"** dashboard tab.

### Usage:
```bash
# Package the latest reports into a timestamped run:
python artifacts_handler.py

# List all archived runs and packages:
python artifacts_handler.py --list
```

---

## Structured JSON Logging & Observability

Script: `structured_logger.py`

* **Format**: Single-line structured JSON logs with standardized keys (`timestamp`, `level`, `service`, `action`, `message`, `module`, `processId`, plus contextual metadata).
* **Storage**: Appended to `logs/pipeline_operations.json.log`.
* **UI Integration**: The **"JSON Logs & Observability"** tab provides live streaming, filtering by log level (`INFO`, `WARNING`, `ERROR`), JSON copying, and automatic polling.

### Example Log Event:
```json
{
  "timestamp": "2026-08-24T12:15:30.123456+00:00",
  "level": "INFO",
  "service": "logistics_analyzer",
  "action": "pipeline_run_completed",
  "message": "Logistics cost analysis completed successfully",
  "total_spend": 22291225.0,
  "shipments_count": 1246,
  "r2_score": 0.985
}
```

---

## Header & Quick-Action Controls

* **Package ZIP (`btn-package-artifacts`)**: Organizes current reports into a timestamped run and archives them into a ZIP.
* **Generate Sample CSV (`btn-run-generator`)**: Runs `python generate_sample_data.py` to produce 1,250 synthetic shipment records.
* **Run Full Analyzer (`btn-run-analyzer`)**: Executes `python logistics_cost_analyzer.py`, generating all reports, charts, CSVs, and packaged runs.

---

## Tabs Overview

* **Executive Dashboard**: KPI metric cards (Total Spend, Avg Cost, On-Time Rate, Model Accuracy), key findings, and strategic recommendations.
* **Generated Charts (7)**: All 7 publication-grade matplotlib/seaborn charts with real-time regeneration.
* **Data Tables & CSVs**: Interactive spreadsheet preview with CSV download buttons.
* **Packaged Runs & ZIPs**: History of historical runs with file counts, timestamps, and direct ZIP download buttons.
* **JSON Logs & Observability**: Real-time structured event logs with level filtering.
* **Debounced Watcher**: Status, architecture configuration, and one-click test execution for the file watcher.
* **Terminal & CLI Output**: Live execution console streaming subprocess stdout and stderr.
* **User Guide & Code**: Code browser for all project files with one-click clipboard copying.
