"""
Filename: watchdog.py
Author: Santiago Nunez-Corrales
Date: 2025-10-20
Description:
    QPU watchdog daemon that checks the availability of the QPU for SLURM scheduling.

License: Apache 2.0
"""

import time
import signal
import logging
from multiprocessing import Process, Event

from lccfq_backend.backend.hwman import HWManClient, HWManStatus

log = logging.getLogger("lccfq_backend.daemon.watchdog")
log.setLevel(logging.INFO)

class QPUWatchdog:
    """Watchdog to check QPU health and availability periodically."""

    def __init__(self, interval: int = 300):
        """We check every 5 minutes for QPU availability.
        """
        self.interval = interval
        self.hwman = HWManClient()
        self.stop_event = Event()
        self.status_file = "/tmp/qpu_status.flag"  # Can be read by SLURM wrapper

    def is_qpu_online(self) -> bool:
        try:
            with open("/tmp/qpu_status.flag", "r") as f:
                return f.read().strip() == "online"
        except FileNotFoundError:
            self.logger.warning("QPU status file not found.")
            return False
        except Exception as e:
            self.logger.error(f"Error checking QPU status: {e}")
            return False

    def check_hardware(self) -> bool:
        """Returns True if QPU responds to ping, else False."""
        try:
            return self.hwman.ping()
        except Exception as e:
            log.error(f"[Watchdog] Hardware ping failed: {e}")
            return False

    def write_status(self, alive: bool):
        """Writes status to a file SLURM can query."""
        with open(self.status_file, "w") as f:
            f.write("online\n" if alive else "offline\n")

    def start(self):
        """Start watchdog monitoring loop."""
        log.info("[Watchdog] Starting QPU watchdog.")
        signal.signal(signal.SIGTERM, self._handle_exit)
        signal.signal(signal.SIGINT, self._handle_exit)

        while not self.stop_event.is_set():
            alive = self.check_hardware()
            self.write_status(alive)
            log.info(f"[Watchdog] QPU status: {'online' if alive else 'offline'}")
            time.sleep(self.interval)

    def _handle_exit(self, signum, frame):
        log.info(f"[Watchdog] Stopping QPU watchdog (signal {signum})")
        self.stop_event.set()
        self.write_status(False)

def start_watchdog(interval: int = 5):
    watchdog = QPUWatchdog(interval=interval)
    watchdog.run()