"""
Filename: logging.py
Author: Santiago Nunez-Corrales
Date: 2025-10-20
Version: 2.0
Description:
    This file implements logging across the backend.
    Supports console, file (with rotation), syslog, and JSON output.
    Configuration via environment variables:

        LCCFQ_LOG_LEVEL       – global default level (DEBUG, INFO, WARNING, ERROR)
        LCCFQ_LOG_LEVELS      – per-component overrides, comma-separated
                                 e.g. "lccfq.fsm=DEBUG,lccfq.queue=WARNING"
        LCCFQ_LOG_FORMAT      – "text" (default) or "json"
        LCCFQ_LOG_FILE        – path to log file (enables RotatingFileHandler)
        LCCFQ_LOG_FILE_MAX    – max bytes per log file (default 10 MB)
        LCCFQ_LOG_FILE_COUNT  – number of rotated backups (default 5)
        LCCFQ_LOG_SYSLOG      – "1" to enable syslog handler

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
import json
import logging
import logging.handlers
import os
import sys
from typing import Optional


_TEXT_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
_TEXT_DATEFMT = "%Y-%m-%d %H:%M:%S"

_configured_handlers: list[logging.Handler] = []
_initialized = False


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects for log aggregation pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": self.formatTime(record, _TEXT_DATEFMT),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def _get_log_format() -> str:
    return os.environ.get("LCCFQ_LOG_FORMAT", "text").lower()


def _get_global_level() -> int:
    level_name = os.environ.get("LCCFQ_LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def _get_component_levels() -> dict[str, int]:
    raw = os.environ.get("LCCFQ_LOG_LEVELS", "")
    levels = {}
    if not raw:
        return levels
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" in pair:
            name, level_str = pair.split("=", 1)
            level = getattr(logging, level_str.strip().upper(), None)
            if level is not None:
                levels[name.strip()] = level
    return levels


def _build_formatter() -> logging.Formatter:
    if _get_log_format() == "json":
        return JSONFormatter()
    return logging.Formatter(_TEXT_FORMAT, _TEXT_DATEFMT)


def _init_shared_handlers():
    """Initialize shared handlers once; all loggers reuse them."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    formatter = _build_formatter()

    # Console handler (always present)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    _configured_handlers.append(console)

    # File handler (opt-in via env var)
    log_file = os.environ.get("LCCFQ_LOG_FILE")
    if log_file:
        max_bytes = int(os.environ.get("LCCFQ_LOG_FILE_MAX", 10 * 1024 * 1024))
        backup_count = int(os.environ.get("LCCFQ_LOG_FILE_COUNT", 5))
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        _configured_handlers.append(file_handler)

    # Syslog handler (opt-in via env var)
    if os.environ.get("LCCFQ_LOG_SYSLOG", "0") == "1":
        syslog_handler = logging.handlers.SysLogHandler(address="/dev/log")
        syslog_handler.setFormatter(formatter)
        _configured_handlers.append(syslog_handler)


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Set up a named logger with standard formatting and configurable output.

    Parameters:
    - name: Hierarchical component name (e.g. "lccfq.executor").
    - level: Logging level override. If None, resolved from LCCFQ_LOG_LEVELS
             then LCCFQ_LOG_LEVEL, then INFO.

    Returns:
    - Configured logger instance.
    """
    _init_shared_handlers()

    logger = logging.getLogger(name)

    if not logger.handlers:
        # Resolve effective level
        if level is not None:
            effective_level = level
        else:
            component_levels = _get_component_levels()
            effective_level = component_levels.get(name, _get_global_level())

        logger.setLevel(effective_level)
        logger.propagate = False

        for handler in _configured_handlers:
            logger.addHandler(handler)

    return logger


def reset_logging():
    """Reset global logging state. Intended for testing only."""
    global _initialized, _configured_handlers
    _initialized = False
    _configured_handlers.clear()
