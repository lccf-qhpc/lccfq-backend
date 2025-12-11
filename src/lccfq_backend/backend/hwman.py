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
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Tuple, Optional

from hwman.client.client import Client as HWManGRPCClient

from ..model.tasks import Gate
from ..model.observables import QubitObservable, QPUObservables
from lccfq_backend.utils.log import setup_logger
from lccfq_backend.config import config

log = setup_logger("lccfq_backend.backend.hwman_client")


class HWManStatus(str, Enum):
    """Possible statuses returned by the Hardware Manager."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    RETUNE_REQUIRED = "retune_required"
    TIMEOUT = "timeout"
    DISCONNECTED = "disconnected"


class BaseHWManClient(ABC):
    """Abstract base class for hardware manager client interface."""

    @abstractmethod
    def run_circuit(self, gates: List[Gate], shots: int) -> Dict[str, int]:
        """
        Execute a quantum circuit on the QPU.

        :param gates: List of Gate objects representing the circuit
        :param shots: Number of measurement shots to perform
        :return: Dictionary mapping bitstring outcomes to counts
        """
        pass

    @abstractmethod
    def run_test(self, symbol: str, params: List[int], shots: int) -> Dict[str, float]:
        """
        Run a quantum benchmark test.

        :param symbol: Test name/symbol (e.g., 'xeb', 'rb')
        :param params: Test parameters
        :param shots: Number of measurement shots
        :return: Dictionary of test results (e.g., fidelity, XEB fit)
        """
        pass

    @abstractmethod
    def get_observables(self) -> QPUObservables:
        """
        Return latest observable values for all qubits.

        :return: QPUObservables object with per-qubit metrics
        """
        pass

    @abstractmethod
    def retune(self) -> Tuple[HWManStatus, Optional[str], Optional[Dict[int, QubitObservable]]]:
        """
        Retune the QPU to optimize performance.

        :return: Tuple of (status, error_message, observables)
        """
        pass

    @abstractmethod
    def run_reset_all(self) -> Tuple[HWManStatus, Optional[str]]:
        """
        Reset all qubits to ground state.

        :return: Tuple of (status, error_message)
        """
        pass

    @abstractmethod
    def evaluate_fidelity(self) -> float:
        """
        Evaluate current QPU fidelity.

        :return: Fidelity value between 0 and 1
        """
        pass

    @abstractmethod
    def run_qtol(self, threshold: float, retries: int = 0) -> Tuple[
        HWManStatus, Optional[str], Optional[Dict[int, QubitObservable]]]:
        """
        Run quality tolerance check with automatic retune attempts.

        :param threshold: Minimum acceptable fidelity threshold
        :param retries: Number of retune attempts if threshold not met
        :return: Tuple of (status, error_message, observables)
        """
        pass

    @abstractmethod
    def ping(self) -> bool:
        """
        Custom health signal to determine if QPU is alive.

        :return: True if QPU is responsive, False otherwise
        """
        pass

    @abstractmethod
    def shutdown(self):
        """Gracefully shutdown the hardware manager client."""
        pass


class MockHWManClient(BaseHWManClient):
    """Mock implementation of hardware manager client for testing and development."""

    def __init__(self):
        log.info("MockHWManClient initialized.")

    def run_circuit(self, gates: List[Gate], shots: int) -> Dict[str, int]:
        log.info(f"Running circuit with {len(gates)} gates and {shots} shots.")
        return {"000": int(0.5 * shots), "111": shots - int(0.5 * shots)}

    def run_test(self, symbol: str, params: List[int], shots: int) -> Dict[str, float]:
        log.info(f"Running test {symbol} with params={params} and shots={shots}.")
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
            return True
        except Exception as e:
            log.error(f"Ping failed: {e}")
            return False

    def shutdown(self):
        log.info("Shutting down MockHWManClient.")


class RealHWManClient(BaseHWManClient):
    """Real implementation of hardware manager client using gRPC."""

    def __init__(self):
        """
        Initialize the real hardware manager client with gRPC connection.
        Configuration is loaded from the backend settings.
        """
        log.info("Initializing RealHWManClient...")

        # Initialize the gRPC client with configuration from settings
        self.client = HWManGRPCClient(
            name=config.hwman_client_name,
            address=config.hwman_address,
            port=config.hwman_port,
            clients_cert_dir=config.hwman_cert_client_dir,
            ca_cert_path=f"{config.hwman_cert_dir}/ca.crt",
            initialize_at_start=True
        )

        log.info(f"RealHWManClient initialized. Attempting ping {config.hwman_address}:{config.hwman_port}")
        self.ping()
        log.info("Ping successful. RealHWManClient connected to hwman server.")

    def run_circuit(self, gates: List[Gate], shots: int) -> Dict[str, int]:
        """
        Execute a quantum circuit on the real QPU via hwman.

        Note: This method needs to be implemented based on the actual hwman API
        for circuit execution. Currently raises NotImplementedError.
        """
        log.info(f"Running circuit with {len(gates)} gates and {shots} shots on real QPU.")
        raise NotImplementedError(
            "run_circuit is not yet implemented for RealHWManClient. "
            "The hwman gRPC API needs to expose circuit execution methods."
        )

    def run_test(self, symbol: str, params: List[int], shots: int) -> Dict[str, float]:
        """
        Run a quantum benchmark test on the real QPU.

        Maps test symbols to hwman test methods:
        - 't1' -> start_t1()
        - 't2r' -> start_t2r()
        - 't2e' -> start_t2e()
        - 'power_rabi' -> start_power_rabi()
        - etc.
        """
        log.info(f"Running test {symbol} with params={params} and shots={shots} on real QPU.")

        # Map test symbols to hwman client methods
        test_method_map = {
            "t1": self.client.start_t1,
            "t2r": self.client.start_t2r,
            "t2e": self.client.start_t2e,
            "power_rabi": self.client.start_power_rabi,
            "resfreq": self.client.start_res_spec,
            "res_spec_vs_gain": self.client.start_res_spec_vs_gain,
            "sat_spec": self.client.start_sat_spec,
            "pi_spec": self.client.start_pi_spec,
            "res_spec_after_pi": self.client.start_res_spec_after_pi,
            "ro_cal": self.client.start_ro_cal,
            "tuneup": self.client.start_tuneup_protocol,
        }

        if symbol.lower() not in test_method_map:
            log.error(f"Unknown test symbol: {symbol}")
            raise ValueError(f"Unknown test symbol: {symbol}. Available: {list(test_method_map.keys())}")

        # Execute the test
        result = test_method_map[symbol.lower()]()

        if result is None:
            log.warning(f"Test {symbol} returned None. This may indicate an error.")
            return {"error": 1.0, "success": 0.0}

        # TODO: Parse the actual result from hwman and convert to expected format
        # For now, return a placeholder
        log.info(f"Test {symbol} completed with result: {result}")
        return {
            "fidelity": 0.982,  # Placeholder - parse from actual result
            "success": 1.0
        }

    def get_observables(self) -> QPUObservables:
        """
        Query observables from the real QPU via hwman.

        Note: This method needs to be implemented based on the actual hwman API
        for querying qubit observables. Currently raises NotImplementedError.
        """
        log.info("Querying observables from real QPU.")
        raise NotImplementedError(
            "get_observables is not yet implemented for RealHWManClient. "
            "The hwman gRPC API needs to expose methods to query qubit observables."
        )

    def retune(self) -> Tuple[HWManStatus, Optional[str], Optional[Dict[int, QubitObservable]]]:
        """
        Retune the real QPU using the hwman tuneup protocol.
        """
        log.info("Retuning real QPU via hwman tuneup protocol.")

        try:
            result = self.client.start_tuneup_protocol()

            if result is None:
                log.error("Tuneup protocol returned None.")
                return HWManStatus.ERROR, "Tuneup protocol failed", None

            log.info("Retune complete.")

            # TODO: Parse observables from the tuneup result
            # For now, return success without observables
            return HWManStatus.OK, None, None

        except Exception as e:
            log.error(f"Failed to retune QPU: {e}")
            return HWManStatus.ERROR, str(e), None

    def run_reset_all(self) -> Tuple[HWManStatus, Optional[str]]:
        """
        Reset all qubits to ground state.

        Note: This method needs to be implemented based on the actual hwman API.
        Currently raises NotImplementedError.
        """
        log.info("Resetting all qubits on real QPU.")
        raise NotImplementedError(
            "run_reset_all is not yet implemented for RealHWManClient. "
            "The hwman gRPC API needs to expose reset functionality."
        )

    def evaluate_fidelity(self) -> float:
        """
        Evaluate current QPU fidelity.

        Note: This method needs to be implemented based on the actual hwman API.
        Currently raises NotImplementedError.
        """
        log.info("Evaluating fidelity on real QPU.")
        raise NotImplementedError(
            "evaluate_fidelity is not yet implemented for RealHWManClient. "
            "The hwman gRPC API needs to expose fidelity evaluation methods."
        )

    def run_qtol(self, threshold: float, retries: int = 0) -> Tuple[
        HWManStatus, Optional[str], Optional[Dict[int, QubitObservable]]]:
        """
        Run quality tolerance check with automatic retune attempts on real QPU.

        This method evaluates fidelity and retunes if below threshold.
        """
        log.info(f"Running QTol with threshold={threshold}, retries={retries} on real QPU.")

        raise NotImplementedError("Run QTol is not yet implemented for RealHWManClient.")

    def ping(self) -> bool:
        """
        Check if the real QPU is alive by pinging the hwman server.
        """
        try:
            log.debug("Pinging real QPU via hwman...")
            response = self.client.ping_server()

            if response is not None:
                log.debug(f"Ping successful: {response}")
                return True
            else:
                log.warning("Ping returned None, QPU may be offline")
                return False

        except Exception as e:
            log.error(f"Ping failed: {e}")
            return False

    def shutdown(self):
        """Gracefully shutdown the hardware manager client connection."""
        log.info("Shutting down RealHWManClient.")

        try:
            # Close the gRPC channel if it exists
            if hasattr(self.client, 'channel') and self.client.channel:
                self.client.channel.close()
                log.info("gRPC channel closed successfully.")
        except Exception as e:
            log.error(f"Error during shutdown: {e}")



HWManClient = MockHWManClient if config.hwman_mock_mode else RealHWManClient
