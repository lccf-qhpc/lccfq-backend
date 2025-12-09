"""
Filename: main.py
Author: Santiago Nunez-Corrales
Date: 2025-08-09
Version: 1.0
Description:
    Entry point for the LCCFQ backend service.
    This loop monitors the QPU status and handles queued tasks.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
"""
Filename: main.py
Author: Santiago Nunez-Corrales
Date: 2025-08-09
Description:
    Main entry point for the LCCFQ backend service.

License: Apache 2.0
"""

import logging
import signal
import threading
import time

from lccfq_backend.api.grpc_server import GRPCServer
from lccfq_backend.backend.executor import QPUExecutor, QPUQueueEmpty
from lccfq_backend.config import BackendSettings
from lccfq_backend.daemon.watchdog import start_watchdog
from lccfq_backend.utils.log import setup_logger

# Load configuration
config = BackendSettings()

# Set up logger with configured log level
logger = setup_logger("LCCFQBackendMain", level=getattr(logging, config.log_level))

# Global shutdown flag
shutdown_flag = False


def handle_signal(signum, frame):
    """Signal handler to set shutdown flag on termination signals."""
    global shutdown_flag
    logger.info(f"[Main] Received signal {signum}, initiating shutdown.")
    shutdown_flag = True


def start_loop(executor: QPUExecutor, poll_interval: int = 10):
    """Start the backend service loop that monitors and executes QPU tasks."""
    logger.info("[Main] Starting LCCFQ backend main loop.")

    while not shutdown_flag:
        try:
            if executor.is_qpu_online():
                result = executor._execute_next()
                logger.info(f"[Main] Task(s) executed: {result}")
            else:
                logger.warning("[Main] QPU not available. Will retry.")
                time.sleep(poll_interval)
        except QPUQueueEmpty:
            logger.debug("[Main] No tasks to execute. Sleeping.")
            time.sleep(poll_interval)
        except Exception as e:
            logger.exception(f"[Main] Unexpected error: {e}")
            time.sleep(poll_interval)

    logger.info("[Main] Backend service stopped gracefully.")

def main():
    """Starts the backend service.

    All configuration is read from config.toml.
    """
    global shutdown_flag

    logger.info("[Main] Initializing LCCFQ backend service.")
    logger.info(f"[Main] Configuration: log_level={config.log_level}, with_grpc={config.with_grpc}, "
                f"grpc_port={config.grpc_port}, with_watchdog={config.with_watchdog}, "
                f"watchdog_interval={config.watchdog_interval}")

    # Set signal handlers from main thread only
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Create executor instance (shared between main loop and gRPC server)
    executor = QPUExecutor()

    # Start gRPC server in background thread if enabled in config
    grpc_server = None
    grpc_server_thread = None
    if config.with_grpc:
        logger.info("[Main] Launching gRPC server thread.")
        grpc_server = GRPCServer(
            executor,
            address=config.grpc_address,
            port=config.grpc_port,
            cert_dir=config.cert_dir,
            max_workers=config.grpc_max_workers
        )
        grpc_server_thread = threading.Thread(target=grpc_server.serve, daemon=True)
        grpc_server_thread.start()

    # Start watchdog in background thread if enabled in config
    watchdog = None
    if config.with_watchdog:
        logger.info("[Main] Launching watchdog thread.")
        watchdog = start_watchdog(interval=config.watchdog_interval)

    try:
        start_loop(executor)
    finally:
        if watchdog:
            logger.info("[Main] Stopping watchdog thread.")
            watchdog.stop()
        if grpc_server:
            logger.info("[Main] Stopping gRPC server.")
            grpc_server.cleanup()


if __name__ == "__main__":
    main()
