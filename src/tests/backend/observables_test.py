"""
Filename: observables_test.py
Author: Santiago Nunez-Corrales
Date: 2025-08-07
Description:
    This file implements tests for the observables model.

License: Apache 2.0
"""
import pytest
from lccfq_backend.model.observables import QubitObservable, QPUObservables


def test_qubit_observable_instantiation():
    obs = QubitObservable(
        t1=18.4,
        t2=21.1,
        anharmonicity=-0.3,
        frequency=5.25,
        gate_fidelity_1q=0.9992,
        gate_fidelity_2q=0.985,
        rx_duration=35.0,
        ry_duration=35.0,
        sqrt_iswap_duration=65.0,
        reset_duration=200.0,
        measurement_duration=300.0,
        max_circuit_depth=24
    )

    assert obs.frequency == 5.25
    assert obs.max_circuit_depth == 24
    assert obs.gate_fidelity_2q < 1.0


def test_qpu_observables_summary_and_dict():
    q1 = QubitObservable(
        t1=20.0, t2=25.0, anharmonicity=-0.32, frequency=4.91,
        gate_fidelity_1q=0.9989, gate_fidelity_2q=0.983,
        rx_duration=30.0, ry_duration=30.0, sqrt_iswap_duration=60.0,
        reset_duration=180.0, measurement_duration=250.0,
        max_circuit_depth=20
    )

    q2 = QubitObservable(
        t1=22.5, t2=26.1, anharmonicity=-0.29, frequency=5.11,
        gate_fidelity_1q=0.9991, gate_fidelity_2q=0.988,
        rx_duration=33.0, ry_duration=33.0, sqrt_iswap_duration=58.0,
        reset_duration=175.0, measurement_duration=240.0,
        max_circuit_depth=22
    )

    qpu_obs = QPUObservables(qubits={0: q1, 1: q2})

    summary = qpu_obs.summary()
    assert "Qubit 0" in summary
    assert "Qubit 1" in summary
    assert "T1=20.0" in summary or "T1=22.5" in summary

    d = qpu_obs.to_dict()
    assert 0 in d and 1 in d
    assert d[0]["frequency"] == 4.91