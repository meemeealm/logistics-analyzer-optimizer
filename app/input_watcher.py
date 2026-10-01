#!/usr/bin/env python3
"""
==============================================================================
            INPUT DATA FOLDER WATCHER & AUTOMATION DAEMON
==============================================================================
Monitors the `input/` folder for new or modified CSV shipment files.
Implements robust debouncing (configurable cooldown window) to prevent duplicate
executions, performs integrity checks, triggers the full logistics analyzer pipeline,
and automatically organizes/packages the resulting output artifacts.
"""

import argparse
import hashlib
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

from structured_logger import get_logger, log_event

logger = get_logger("input_watcher")


def compute_file_hash(filepath: Path) -> str:
    """Calculates MD5 hash of file content to detect real modifications."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class InputFolderWatcher:
    """
    Automated directory watcher with software debouncing to monitor CSV drops.
    """

    def __init__(
        self,
        input_dir: Path = Path("input"),
        reports_dir: Path = Path("reports"),
        debounce_seconds: float = 3.0,
        poll_interval_seconds: float = 1.0,
        run_once_on_startup: bool = False,
    ):
        self.input_dir = input_dir
        self.reports_dir = reports_dir
        self.debounce_seconds = debounce_seconds
        self.poll_interval = poll_interval_seconds
        self.run_once_on_startup = run_once_on_startup

        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Track file states: filepath -> {last_seen_mtime, last_hash, last_triggered_time, pending_since}
        self.file_states: Dict[Path, Dict[str, float]] = {}
        self.processed_hashes: Dict[Path, str] = {}
        self.is_running = False

    def trigger_pipeline(self, target_csv: Path) -> bool:
        """Executes the logistics cost analyzer and artifact packaging."""
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"auto_{run_timestamp}"

        log_event(
            logger,
            "info",
            action="pipeline_auto_trigger_start",
            message=f"New or modified input file detected: '{target_csv.name}'. Triggering analytics pipeline...",
            input_file=str(target_csv.resolve()),
            run_id=run_id,
        )

        print("\n" + "=" * 65)
        print(f" [WATCHER AUTO-TRIGGER] Executing Pipeline for: {target_csv.name}")
        print(f" Run ID: {run_id} | Timestamp: {run_timestamp}")
        print("=" * 65)

        # 1. Run main analytics engine
        python_exec = sys.executable or "python3"
        cmd = [python_exec, "logistics_cost_analyzer.py", "--input", str(target_csv)]

        try:
            start_time = time.time()
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            duration = round(time.time() - start_time, 2)

            if process.returncode == 0:
                print(f"✓ Analysis pipeline succeeded in {duration}s")
                log_event(
                    logger,
                    "info",
                    action="pipeline_auto_trigger_success",
                    message=f"Logistics analysis completed successfully for '{target_csv.name}'",
                    duration_seconds=duration,
                    run_id=run_id,
                )

                # 2. Trigger Artifacts Organizer and Zip Packager
                try:
                    from artifacts_handler import organize_and_package_run
                    pkg_result = organize_and_package_run(
                        reports_dir=self.reports_dir,
                        run_id=run_id,
                        input_file=target_csv,
                    )
                    print(f"✓ Output artifacts organized into: {pkg_result['run_dir']}")
                    print(f"✓ Timestamped archive created: {pkg_result['zip_path']} ({pkg_result['zip_size_kb']} KB)")
                except Exception as pkg_err:
                    log_event(
                        logger,
                        "error",
                        action="artifact_packaging_error",
                        message=f"Failed to package artifacts: {pkg_err}",
                        error=str(pkg_err),
                    )
                return True
            else:
                print(f"✗ Analysis failed with return code {process.returncode}")
                print(process.stderr)
                log_event(
                    logger,
                    "error",
                    action="pipeline_auto_trigger_failed",
                    message=f"Pipeline execution failed for '{target_csv.name}'",
                    returncode=process.returncode,
                    stderr=process.stderr,
                )
                return False

        except Exception as e:
            log_event(
                logger,
                "error",
                action="pipeline_auto_trigger_exception",
                message=f"Exception while running pipeline: {e}",
                error=str(e),
            )
            return False

    def scan_and_debounce(self) -> None:
        """Scans the input directory and debounces file updates."""
        now = time.time()
        current_csvs = list(self.input_dir.glob("*.csv"))

        for csv_path in current_csvs:
            try:
                stat = csv_path.stat()
                mtime = stat.st_mtime
                size = stat.st_size

                # Avoid empty/locked files currently being written
                if size == 0:
                    continue

                if csv_path not in self.file_states:
                    # New file discovered
                    file_hash = compute_file_hash(csv_path)
                    self.file_states[csv_path] = {
                        "mtime": mtime,
                        "last_change": now,
                        "pending_trigger": True,
                    }
                    self.processed_hashes[csv_path] = ""
                    log_event(
                        logger,
                        "info",
                        action="file_discovered",
                        message=f"Discovered new CSV file: '{csv_path.name}'. Starting debounce window ({self.debounce_seconds}s)...",
                        filepath=str(csv_path.resolve()),
                        size_bytes=size,
                    )
                else:
                    # Existing file: check if mtime changed
                    state = self.file_states[csv_path]
                    if mtime != state["mtime"]:
                        state["mtime"] = mtime
                        state["last_change"] = now
                        state["pending_trigger"] = True
                        log_event(
                            logger,
                            "info",
                            action="file_modified_debouncing",
                            message=f"File '{csv_path.name}' modified while debouncing; timer reset.",
                            filepath=str(csv_path.resolve()),
                        )

                # Check if debounce cooldown window has passed with no further writes
                state = self.file_states[csv_path]
                if state["pending_trigger"]:
                    time_since_last_change = now - state["last_change"]
                    if time_since_last_change >= self.debounce_seconds:
                        current_hash = compute_file_hash(csv_path)
                        # Verify content has actually changed from last processed run
                        if current_hash != self.processed_hashes.get(csv_path):
                            log_event(
                                logger,
                                "info",
                                action="debounce_cooldown_complete",
                                message=f"Debounce cooldown passed for '{csv_path.name}'. Triggering execution.",
                                file_hash=current_hash,
                            )
                            success = self.trigger_pipeline(csv_path)
                            if success:
                                self.processed_hashes[csv_path] = current_hash
                        else:
                            log_event(
                                logger,
                                "info",
                                action="duplicate_content_skipped",
                                message=f"Skipping duplicate execution for '{csv_path.name}': content hash unchanged.",
                                file_hash=current_hash,
                            )
                        state["pending_trigger"] = False

            except (FileNotFoundError, PermissionError) as e:
                # File might be temporarily locked by Windows/OS copy
                continue

    def start(self) -> None:
        """Starts the persistent polling and debouncing loop."""
        self.is_running = True
        log_event(
            logger,
            "info",
            action="watcher_service_started",
            message=f"Input folder watcher started for directory '{self.input_dir.resolve()}'. Debounce: {self.debounce_seconds}s.",
            input_dir=str(self.input_dir.resolve()),
            debounce_seconds=self.debounce_seconds,
        )

        print("\n" + "=" * 65)
        print("     LOGISTICS COST ANALYZER - AUTOMATED INPUT WATCHER")
        print("=" * 65)
        print(f"Monitoring folder:   {self.input_dir.resolve()}")
        print(f"Debounce window:     {self.debounce_seconds} seconds")
        print(f"Poll interval:       {self.poll_interval} second(s)")
        print("Press Ctrl+C to stop watching.")
        print("=" * 65 + "\n")

        # Initial check
        if self.run_once_on_startup:
            target = self.input_dir / "shipments.csv"
            if target.exists():
                self.trigger_pipeline(target)

        try:
            while self.is_running:
                self.scan_and_debounce()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\nStopping input watcher...")
            log_event(
                logger,
                "info",
                action="watcher_service_stopped",
                message="Input folder watcher stopped by user interrupt.",
            )


def main():
    parser = argparse.ArgumentParser(description="Automated input directory watcher with debouncing")
    parser.add_argument("--input-dir", type=str, default="input", help="Directory to monitor for CSV files")
    parser.add_argument("--reports-dir", type=str, default="reports", help="Reports output directory")
    parser.add_argument("--debounce", type=float, default=3.0, help="Debounce cooldown window in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--run-on-start", action="store_true", help="Execute once immediately if file exists")
    args = parser.parse_args()

    watcher = InputFolderWatcher(
        input_dir=Path(args.input_dir),
        reports_dir=Path(args.reports_dir),
        debounce_seconds=args.debounce,
        poll_interval_seconds=args.interval,
        run_once_on_startup=args.run_on_start,
    )
    watcher.start()


if __name__ == "__main__":
    main()
