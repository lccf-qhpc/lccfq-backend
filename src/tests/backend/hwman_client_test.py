"""
Filename: hwman_client_test.py
Author: Santiago Nunez-Corrales
Date: 2025-08-07
Version: 1.0
Description:
    This file implements tests for the hardware manager client.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
from lccfq_backend.backend.hwman import make_hwman_client
from lccfq_backend.config import BackendSettings
from lccfq_backend.model.tasks import Gate

_config = BackendSettings(hwman_mock_mode=True)


def test_run_circuit_returns_expected_distribution():
    client = make_hwman_client(_config)
    gates = [
        Gate(symbol="rx", target_qubits=[0], control_qubits=[], params=[1.57]),
        Gate(symbol="sqiswap", target_qubits=[1], control_qubits=[0], params=[])
    ]
    shots = 1000
    result = client.run_circuit(gates, shots)

    assert isinstance(result, dict)
    assert "distribution" in result
    assert "raw_bitstream" in result

    distribution = result["distribution"]

    assert "000" in distribution and "111" in distribution
    assert distribution["000"] + distribution["111"] == shots
    assert all(isinstance(v, int) for v in distribution.values())
    assert result["raw_bitstream"] == []


def test_run_test_returns_expected_metrics():
    client = make_hwman_client(_config)
    symbol = "xeb"
    params = [0, 1]
    shots = 512

    result = client.run_test(symbol, params, shots)

    assert isinstance(result, dict)
    assert "fidelity" in result
    assert "xeb_fit" in result
    assert 0 <= result["fidelity"] <= 1
    assert 0 <= result["xeb_fit"] <= 1
    assert all(isinstance(v, float) for v in result.values())
