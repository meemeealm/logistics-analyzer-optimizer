#!/usr/bin/env python3
"""
==============================================================================
                        STRUCTURED JSON LOGGER UTILITY
==============================================================================
Provides high-performance, structured JSON logging for all pipeline operations,
automations, file watcher triggers, model training, and artifact packaging.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line valid JSON objects."""

    def __init__(self, service_name: str = "logistics_cost_analyzer"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineNo": record.lineno,
            "processId": os.getpid(),
        }

        # Include custom context/extra fields if provided
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_entry.update(record.extra_fields)

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def get_logger(
    name: str = "logistics_analyzer",
    log_dir: Optional[Path] = None,
    log_filename: str = "pipeline_operations.json.log",
    also_console: bool = True,
) -> logging.Logger:
    """
    Returns a configured structured JSON logger writing to both file and console.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = StructuredJsonFormatter(service_name=name)

    # Setup file logging directory
    if log_dir is None:
        log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_filename

    # File handler (JSON lines)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (JSON lines)
    if also_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def log_event(
    logger: logging.Logger,
    level: str,
    action: str,
    message: str,
    **kwargs: Any,
) -> None:
    """Helper method to emit structured events with arbitrary key-value metadata."""
    extra = {
        "action": action,
        **kwargs,
    }
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra={"extra_fields": extra})


if __name__ == "__main__":
    test_logger = get_logger("test_service")
    log_event(
        test_logger,
        "info",
        action="logger_initialization_test",
        message="Structured JSON logging system initialized successfully.",
        status="OK",
        version="1.0.0",
    )
