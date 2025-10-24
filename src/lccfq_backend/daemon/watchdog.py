"""
Filename: watchdog.py
Author: Santiago Nunez-Corrales
Date: 2025-10-20
Description:
    QPU watchdog daemon that checks the availability of the QPU for SLURM scheduling.

License: Apache 2.0
"""
import time
import threading
from multiprocessing import Event
from ..logging.logger import setup_logger
from ..backend.hwman import HWManClient
from ..slurm.exporter import export_observables

logger = setup_logger("lccfq_backend.daemon.watchdog")


class QPUWatchdog:
    """Watchdog to check QPU health and availability periodically."""

    def __init__(self, interval: int = 300):
        self.interval = interval
        self.hwman = HWManClient()
        self.stop_event = Event()
        self.status_file = "/tmp/qpu_status.flag"  # Readable by SLURM or systemd unit

    def is_qpu_online(self) -> bool:
        try:
            with open(self.status_file, "r") as f:
                return f.read().strip() == "online"
        except FileNotFoundError:
            logger.warning("QPU status file not found.")
            return False
        except Exception as e:
            logger.error(f"Error checking QPU status: {e}")
            return False

    def check_hardware(self) -> bool:
        """Returns True if QPU responds to ping, else False."""
        try:
            return self.hwman.ping()
        except Exception as e:
            logger.error(f"[Watchdog] Hardware ping failed: {e}")
            return False

    def write_status(self, alive: bool):
        """Writes status to a file SLURM/systemd can query."""
        try:
            with open(self.status_file, "w") as f:
                f.write("online\n" if alive else "offline\n")
        except Exception as e:
            logger.error(f"Could not write to status file: {e}")

    def run(self):
        """Main loop for the watchdog."""
        logger.info("[Watchdog] Starting watchdog main loop.")
        while not self.stop_event.is_set():
            alive = self.check_hardware()
            self.write_status(alive)
            logger.info(f"[Watchdog] QPU status: {'online' if alive else 'offline'}")

            if alive:
                try:
                    observables = self.hwman.get_observables()
                    export_observables(observables)
                except Exception as e:
                    logger.warning(f"[Watchdog] Could not export observables: {e}")

            time.sleep(self.interval)

    def stop(self):
        """External stop signal handler."""
        logger.info("[Watchdog] Watchdog stop requested.")
        self.stop_event.set()
        self.write_status(False)

def start_watchdog(interval: int = 300) -> QPUWatchdog:
    """
    Starts the watchdog in a background thread.
    Returns the watchdog instance so it can be stopped externally.
    This function should only be called from the main thread.
    """
    logger.info(f"[Watchdog] Preparing to start watchdog thread with interval = {interval} sec.")

    watchdog = QPUWatchdog(interval=interval)

    try:
        thread = threading.Thread(target=watchdog.run, daemon=True)
        thread.start()
        logger.info(f"[Watchdog] Watchdog thread started successfully (daemon = True).")
    except Exception as e:
        logger.exception(f"[Watchdog] Failed to start watchdog thread: {e}")
        raise

    return watchdog