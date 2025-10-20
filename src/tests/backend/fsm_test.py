"""
Filename: test_fsm.py
Author: Santiago Nunez-Corrales
Date: 2025-08-06
Description:
    This file implements tests for the QPU abstraction.

License: Apache 2.0
"""
import pytest

from lccfq_backend.backend.fsm import QPUAbstraction, QPUEvent
from lccfq_backend.model.state import QPUState
from lccfq_backend.backend.error import UnknownQPUState


def test_initial_state():
    qpu = QPUAbstraction()
    assert qpu.state == QPUState.INACCESSIBLE


def test_successful_startup_sequence():
    qpu = QPUAbstraction()
    qpu.transition(QPUEvent.CONNECT)
    assert qpu.state == QPUState.ACCESSIBLE

    qpu.transition(QPUEvent.DEVICE_OK)
    assert qpu.state == QPUState.RESPONSIVE

    qpu.transition(QPUEvent.TUNE_SUCCESS)
    assert qpu.state == QPUState.TUNED

    qpu.transition(QPUEvent.RESET)
    assert qpu.state == QPUState.IDLE

    qpu.transition(QPUEvent.TASK_STARTED)
    assert qpu.state == QPUState.BUSY

    qpu.transition(QPUEvent.TASK_FINISHED)
    assert qpu.state == QPUState.IDLE


def test_fidelity_degradation_and_recovery():
    qpu = QPUAbstraction()
    qpu.transition(QPUEvent.CONNECT)
    qpu.transition(QPUEvent.DEVICE_OK)
    qpu.transition(QPUEvent.TUNE_SUCCESS)
    qpu.transition(QPUEvent.FIDELITY_DEGRADED)

    assert qpu.state == QPUState.MISTUNED

    qpu.transition(QPUEvent.TUNE_SUCCESS)
    assert qpu.state == QPUState.TUNED


def test_unresponsive_and_disconnect():
    qpu = QPUAbstraction()
    qpu.transition(QPUEvent.CONNECT)
    qpu.transition(QPUEvent.DEVICE_FAIL)
    assert qpu.state == QPUState.UNRESPONSIVE

    qpu.transition(QPUEvent.DISCONNECT)
    assert qpu.state == QPUState.INACCESSIBLE


def test_invalid_transition_raises():
    qpu = QPUAbstraction()
    # Directly trying to RESET from INACCESSIBLE should fail
    with pytest.raises(UnknownQPUState) as excinfo:
        qpu.transition(QPUEvent.RESET)

    assert "reset" in str(excinfo.value).lower()