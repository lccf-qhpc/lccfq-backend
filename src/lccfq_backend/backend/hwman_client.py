"""
Filename: hwman_client.py
Author: Santiago Nunez-Corrales
Date: 2025-08-07
Version: 1.0
Description:
    This file provides an interface to the hardware manager.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
from typing import List, Dict, Tuple, Optional
from ..model.tasks import Gate
from ..model.observables import QubitObservable


class HWManClient:
    """"Hardware manager client interface. This assumes gRPC.
    """

    def __init__(self):
        pass

    def run_circuit(self, gates: List[Gate], shots: int) -> Dict[str, int]:
        """Run a quantum circuit using the QPU.

        :param gates: program in terms of Gates
        :param shots: number of shots
        :return: resulting distribution
        """
        # TODO: Replace with real quantum device API call
        return {"000": int(0.5 * shots), "111": shots - int(0.5 * shots)}

    def run_test(self, symbol: str, params: List[int], shots: int) -> Dict[str, float]:
        """Run a test using the QPU.

        :param symbol: test
        :param params: test parameters
        :param shots: number of shots
        :return: test results
        """
        # TODO: mock-up data here
        return {
            "fidelity": 0.982,
            "xeb_fit": 0.975
        }

    def run_retune(self) -> Tuple[bool, Optional[str], Optional[Dict[int, QubitObservable]]]:
        """Retune the device and update qubit observables.

        :return:
        """
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
        return True, None, observables

    def run_reset_all(self) -> Tuple[bool, Optional[str]]:
        """Reset all qubits

        :return:
        """
        return True, None

    def run_qtol(self, threshold: float, retries: int = 0) -> Tuple[
        bool, Optional[str], Optional[Dict[int, QubitObservable]]]:

        """Set the qubit fidelity tolerance threshold for XEB RCS.

        """
        if threshold > 0.99:
            return False, "Unable to reach desired fidelity.", None

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
            return True, None, observables
        else:
            return True, "Fidelity threshold not met after retries", observables

    def shutdown(self):
        """Wrap up the hardware manager client connection.

        :return: nothing
        """
        pass
