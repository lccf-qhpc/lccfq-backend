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
from lccfq_backend.backend.result_store import ResultStore
from lccfq_backend.config import BackendSettings
from lccfq_backend.daemon.watchdog import start_watchdog
from lccfq_backend.utils.log import setup_logger

logger = setup_logger("lccfq.main")

# Global shutdown flag
shutdown_flag = False


def handle_signal(signum, frame):
    """Signal handler to set shutdown flag on termination signals."""
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating shutdown.")
    shutdown_flag = True


def start_loop(executor: QPUExecutor, config: BackendSettings, poll_interval: int = 10):
    """Start the backend service loop that monitors and executes QPU tasks."""
    logger.info("Starting LCCFQ backend main loop.")

    start = time.time()

    if config.with_calibration:
        try:
            content = config.calibration_state.read_text().strip()
            if content:
                start = float(content)
                logger.info(f"Loaded last calibration time: {time.ctime(start)}")
        except Exception as e:
            logger.warning(f"Failed to load calibration state: {e}. Starting with current time.")

    while not shutdown_flag:
        try:
            if executor.is_qpu_online():

                if config.with_calibration and time.time() - start >= config.calibration_interval:
                    logger.info("Calibration interval reached. Scheduling calibration task.")
                    executor.hwman.retune()
                    start = time.time()
                    try:
                        config.calibration_state.write_text(str(start))
                        logger.info(f"Calibration time saved to {config.calibration_state}.")
                    except Exception as e:
                        logger.warning(f"Failed to save calibration state: {e}.")
                    continue

                result = executor._execute_next()
                logger.info(f"Task(s) executed, qpu_state={executor.qpu.state}, queue_depth={len(executor.queue._queue)}")
            else:
                logger.warning(f"QPU not available (state={executor.qpu.state}). Will retry.")
                time.sleep(poll_interval)
        except QPUQueueEmpty:
            logger.debug("No tasks to execute. Sleeping.")
            time.sleep(poll_interval)
        except Exception as e:
            logger.exception("Unexpected error during main loop")
            time.sleep(poll_interval)

    logger.info("Backend service stopped gracefully.")

def main(config: BackendSettings) -> None:
    """Starts the backend service."""
    global shutdown_flag

    logger.info("Initializing LCCFQ backend service.")
    logger.info(f"Configuration: log_level={config.log_level}, with_grpc={config.with_grpc}, "
                f"grpc_port={config.grpc_port}, with_watchdog={config.with_watchdog}, "
                f"watchdog_interval={config.watchdog_interval}")

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    result_store = ResultStore(results_dir=config.results_dir)
    executor = QPUExecutor(config=config, result_store=result_store)

    grpc_server = None
    grpc_server_thread = None
    if config.with_grpc:
        logger.info("Launching gRPC server thread.")
        grpc_server = GRPCServer(
            executor,
            address=config.grpc_address,
            port=config.grpc_port,
            cert_dir=config.cert_dir,
            max_workers=config.grpc_max_workers,
            result_store=result_store,
        )
        grpc_server_thread = threading.Thread(target=grpc_server.serve, daemon=True)
        grpc_server_thread.start()

    watchdog = None
    if config.with_watchdog:
        logger.info("Launching watchdog thread.")
        watchdog = start_watchdog(config=config, interval=config.watchdog_interval)

    try:
        start_loop(executor, config)
    finally:
        if watchdog:
            logger.info("Stopping watchdog thread.")
            watchdog.stop()
        if grpc_server:
            logger.info("Stopping gRPC server.")
            grpc_server.cleanup()
