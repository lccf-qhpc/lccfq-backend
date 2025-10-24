"""
Filename: hwman.py
Author: Santiago Nunez-Corrales
Date: 2025-08-07
Version: 1.0
Description:
    This file provides an interface to the hardware manager.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
from enum import Enum
from typing import List, Dict, Tuple, Optional
from ..model.tasks import Gate
from ..model.observables import QubitObservable, QPUObservables
from ..logging.logger import setup_logger

log = setup_logger("lccfq_backend.backend.hwman_client")


class HWManStatus(str, Enum):
    """Possible statuses returned by the Hardware Manager."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    RETUNE_REQUIRED = "retune_required"
    TIMEOUT = "timeout"
    DISCONNECTED = "disconnected"


class HWManClient:
    """Hardware manager client interface. This assumes gRPC."""

    def __init__(self):
        log.info("HWManClient initialized.")

    def run_circuit(self, gates: List[Gate], shots: int) -> Dict[str, int]:
        log.info(f"Running circuit with {len(gates)} gates and {shots} shots.")
        # TODO: Replace with real quantum device API call
        return {"000": int(0.5 * shots), "111": shots - int(0.5 * shots)}

    def run_test(self, symbol: str, params: List[int], shots: int) -> Dict[str, float]:
        log.info(f"Running test {symbol} with params={params} and shots={shots}.")
        # TODO: mock-up data here
        return {
            "fidelity": 0.982,
            "xeb_fit": 0.975
        }

    def get_observables(self) -> QPUObservables:
        """
        Return latest observable values for all qubits.

        :return: QPUObservables object with per-qubit metrics
        """
        log.info("Querying observables from QPU.")
        observables = {
            i: QubitObservable(
                t1=30.0 + i,
                t2=25.0 + i,
                anharmonicity=-0.3,
                frequency=4.9 + i * 0.01,
                gate_fidelity_1q=0.982,
                gate_fidelity_2q=0.973,
                rx_duration=20.0,
                ry_duration=20.0,
                sqrt_iswap_duration=40.0,
                reset_duration=5.0,
                measurement_duration=12.0,
                max_circuit_depth=2000 - i * 100
            ) for i in range(5)
        }
        return QPUObservables(qubits=observables)

    def retune(self) -> Tuple[HWManStatus, Optional[str], Optional[Dict[int, QubitObservable]]]:
        log.info("Retuning QPU.")
        # TODO: provide real implementation
        observables = {
            i: QubitObservable(
                t1=30.0 + i,
                t2=25.0 + i,
                anharmonicity=-0.3,
                frequency=4.9 + i * 0.01,
                gate_fidelity_1q=0.992,
                gate_fidelity_2q=0.987,
                rx_duration=20.0,
                ry_duration=20.0,
                sqrt_iswap_duration=40.0,
                reset_duration=5.0,
                measurement_duration=12.0
            ) for i in range(5)
        }
        log.info("Retune complete.")
        return HWManStatus.OK, None, observables

    def run_reset_all(self) -> Tuple[HWManStatus, Optional[str]]:
        log.info("Resetting all qubits.")
        return HWManStatus.OK, None

    def evaluate_fidelity(self) -> float:
        # Simulate a fidelity check
        fidelity = 0.981
        log.info(f"Evaluated fidelity: {fidelity}")
        return fidelity

    def run_qtol(self, threshold: float, retries: int = 0) -> Tuple[
        HWManStatus, Optional[str], Optional[Dict[int, QubitObservable]]]:
        log.info(f"Running QTol with threshold={threshold}, retries={retries}")
        if threshold > 0.99:
            log.warning("Requested fidelity threshold too high.")
            return HWManStatus.ERROR, "Unable to reach desired fidelity.", None

        observables = {
            i: QubitObservable(
                t1=30.0 + i,
                t2=25.0 + i,
                anharmonicity=-0.3,
                frequency=4.9 + i * 0.01,
                gate_fidelity_1q=0.982,
                gate_fidelity_2q=0.973,
                rx_duration=20.0,
                ry_duration=20.0,
                sqrt_iswap_duration=40.0,
                reset_duration=5.0,
                measurement_duration=12.0
            ) for i in range(5)
        }

        if threshold < 0.975:
            log.info("QTol threshold met.")
            return HWManStatus.OK, None, observables
        else:
            log.warning("QTol threshold not met, returning warning status.")
            return HWManStatus.WARNING, "Fidelity threshold not met after retries", observables

    def ping(self) -> bool:
        """Custom health signal to determine if QPU is alive."""
        try:
            log.debug("Pinging QPU...")
            # Simulate always online for now
            return True
        except Exception as e:
            log.error(f"Ping failed: {e}")
            return False

    def shutdown(self):
        log.info("Shutting down HWManClient.")
        # TODO: Add graceful disconnection logic if needed
        pass
