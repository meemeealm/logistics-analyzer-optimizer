#!/usr/bin/env python3
"""
==============================================================================
                    ARTIFACTS HANDLER & PACKAGING MANAGER
==============================================================================
Organizes output artifacts from runs into run-specific timestamped folders
(e.g., reports/runs/run_YYYYMMDD_HHMMSS/), copies summary text, CSV files,
and charts, generates manifest metadata, and packages them into timestamped
ZIP archives inside reports/archives/.
"""

import argparse
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from structured_logger import get_logger, log_event

logger = get_logger("artifacts_handler")


def organize_and_package_run(
    reports_dir: Path = Path("reports"),
    run_id: Optional[str] = None,
    input_file: Optional[Path] = None,
    clean_root_after: bool = False,
) -> Dict[str, Any]:
    """
    Collects newly generated reports and charts in `reports_dir`, organizes them into
    a run-specific subfolder (`reports/runs/run_<timestamp>/`), and packages everything
    into a timestamped ZIP archive in `reports/archives/`.
    """
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    if not run_id:
        run_id = f"run_{timestamp_str}"

    runs_dir = reports_dir / "runs"
    archives_dir = reports_dir / "archives"
    current_run_dir = runs_dir / run_id

    runs_dir.mkdir(parents=True, exist_ok=True)
    archives_dir.mkdir(parents=True, exist_ok=True)
    current_run_dir.mkdir(parents=True, exist_ok=True)

    log_event(
        logger,
        "info",
        action="artifact_packaging_start",
        message=f"Starting artifact organization for run '{run_id}'",
        run_id=run_id,
        timestamp=timestamp_str,
    )

    # Artifact patterns to look for in root reports_dir
    chart_patterns = ["*.png", "*.svg"]
    csv_patterns = ["*.csv"]
    doc_patterns = ["*.txt", "*.json"]

    copied_files: List[Path] = []

    # Copy files from reports_dir (direct children only)
    for item in reports_dir.iterdir():
        if item.is_file() and not item.name.startswith("."):
            dest_file = current_run_dir / item.name
            shutil.copy2(item, dest_file)
            copied_files.append(dest_file)

    # Create run metadata manifest
    manifest_data = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "created_at_local": now.isoformat(),
        "input_source": str(input_file.resolve()) if input_file and input_file.exists() else "default",
        "artifacts_count": len(copied_files),
        "artifacts": [f.name for f in copied_files],
    }

    manifest_file = current_run_dir / "run_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    copied_files.append(manifest_file)

    # Also keep a copy of manifest in reports root
    shutil.copy2(manifest_file, reports_dir / "latest_run_manifest.json")

    # Package into timestamped ZIP
    zip_filename = f"logistics_reports_{run_id}.zip"
    zip_path = archives_dir / zip_filename

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in copied_files:
            zipf.write(file_path, arcname=f"{run_id}/{file_path.name}")

    zip_size_kb = round(zip_path.stat().st_size / 1024, 2)

    log_event(
        logger,
        "info",
        action="artifact_packaging_complete",
        message=f"Run '{run_id}' packaged successfully into '{zip_filename}' ({zip_size_kb} KB)",
        run_id=run_id,
        run_dir=str(current_run_dir.resolve()),
        zip_path=str(zip_path.resolve()),
        zip_size_kb=zip_size_kb,
        files_count=len(copied_files),
    )

    return {
        "run_id": run_id,
        "run_dir": str(current_run_dir),
        "zip_path": str(zip_path),
        "zip_filename": zip_filename,
        "zip_size_kb": zip_size_kb,
        "files_count": len(copied_files),
    }


def list_archived_runs(reports_dir: Path = Path("reports")) -> List[Dict[str, Any]]:
    """Returns a list of all historical runs and packaged zip archives."""
    runs_dir = reports_dir / "runs"
    archives_dir = reports_dir / "archives"
    results = []

    if not runs_dir.exists():
        return []

    for run_folder in sorted(runs_dir.iterdir(), reverse=True):
        if run_folder.is_dir():
            manifest_file = run_folder / "run_manifest.json"
            manifest: Dict[str, Any] = {}
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as mf:
                        manifest = json.load(mf)
                except Exception:
                    pass

            zip_match = archives_dir / f"logistics_reports_{run_folder.name}.zip"
            results.append({
                "run_id": run_folder.name,
                "folder_path": str(run_folder),
                "created_at": manifest.get("created_at_local", ""),
                "artifacts_count": manifest.get("artifacts_count", len(list(run_folder.iterdir()))),
                "zip_exists": zip_match.exists(),
                "zip_filename": zip_match.name if zip_match.exists() else None,
                "zip_size_kb": round(zip_match.stat().st_size / 1024, 2) if zip_match.exists() else 0,
            })
    return results


def main():
    parser = argparse.ArgumentParser(description="Logistics Cost Analyzer - Artifacts Handler")
    parser.add_argument("--reports-dir", type=str, default="reports", help="Root reports directory")
    parser.add_argument("--run-id", type=str, default=None, help="Custom Run ID")
    parser.add_argument("--list", action="store_true", help="List all historical runs and archives")
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)

    if args.list:
        runs = list_archived_runs(reports_dir)
        print(f"\nFound {len(runs)} packaged runs in '{reports_dir}/':\n")
        for r in runs:
            print(f"  • Run ID: {r['run_id']} | Artifacts: {r['artifacts_count']} | ZIP: {r['zip_filename']} ({r['zip_size_kb']} KB)")
        print()
        return

    result = organize_and_package_run(reports_dir=reports_dir, run_id=args.run_id)
    print("\n" + "=" * 60)
    print("           ARTIFACT PACKAGING COMPLETE")
    print("=" * 60)
    print(f"Run ID:        {result['run_id']}")
    print(f"Run Directory: {result['run_dir']}")
    print(f"ZIP Archive:   {result['zip_path']} ({result['zip_size_kb']} KB)")
    print(f"Files Copied:  {result['files_count']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
