"""
Filename: logging.py
Author: Santiago Nunez-Corrales
Date: 2025-10-20
Version: 1.0
Description:
    This file implements logging across the backend.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
import logging
import sys
from typing import Optional


def setup_logger(name: str, level: Optional[int] = logging.INFO) -> logging.Logger:
    """
    Set up a named logger with a standard format for console output.

    Parameters:
    - name: Name of the logger, usually the module or component name.
    - level: Logging level (DEBUG, INFO, WARNING, ERROR).

    Returns:
    - Configured logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger