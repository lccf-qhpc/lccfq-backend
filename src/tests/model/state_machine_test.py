"""
Filename: state_machine_test.py
Author: Santiago Nunez-Corrales
Date: 2025-09-16
Version: 1.0
Description:
    This file tests state transitions.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
import pytest
from lccfq_backend.backend.fsm import QPUAbstraction, QPUEvent
from lccfq_backend.model.state import QPUState


@pytest.fixture
def qpu_abstraction():
    return QPUAbstraction()

@pytest.mark.parametrize("start_state,event,expected_state", [
    (QPUState.INACCESSIBLE, QPUEvent.CONNECT, QPUState.ACCESSIBLE),
    (QPUState.ACCESSIBLE, QPUEvent.DEVICE_OK, QPUState.RESPONSIVE),
    (QPUState.ACCESSIBLE, QPUEvent.DEVICE_FAIL, QPUState.UNRESPONSIVE),
    (QPUState.RESPONSIVE, QPUEvent.TUNE_SUCCESS, QPUState.TUNED),
    (QPUState.RESPONSIVE, QPUEvent.TUNE_FAIL, QPUState.MISTUNED),
    (QPUState.MISTUNED, QPUEvent.TUNE_SUCCESS, QPUState.TUNED),
    (QPUState.TUNED, QPUEvent.FIDELITY_DEGRADED, QPUState.MISTUNED),
    (QPUState.TUNED, QPUEvent.RESET, QPUState.IDLE),
    (QPUState.IDLE, QPUEvent.TASK_STARTED, QPUState.BUSY),
    (QPUState.BUSY, QPUEvent.TASK_FINISHED, QPUState.IDLE),
    (QPUState.UNRESPONSIVE, QPUEvent.DISCONNECT, QPUState.INACCESSIBLE),
])
def test_valid_transitions(qpu_abstraction, start_state, event, expected_state):
    qpu_abstraction.state = start_state
    next_state = qpu_abstraction._next_state(event)
    assert next_state == expected_state

@pytest.mark.parametrize("start_state,event", [
    (QPUState.INACCESSIBLE, QPUEvent.DEVICE_OK),
    (QPUState.INACCESSIBLE, QPUEvent.TASK_STARTED),
    (QPUState.ACCESSIBLE, QPUEvent.RESET),
    (QPUState.TUNED, QPUEvent.TASK_STARTED),
    (QPUState.RESPONSIVE, QPUEvent.RESET),
    (QPUState.MISTUNED, QPUEvent.TUNE_FAIL),
    (QPUState.UNRESPONSIVE, QPUEvent.CONNECT),
    (QPUState.IDLE, QPUEvent.TUNE_SUCCESS),
    (QPUState.BUSY, QPUEvent.RESET),
    (QPUState.IDLE, QPUEvent.TASK_FINISHED),
])
def test_invalid_transitions(qpu_abstraction, start_state, event):
    qpu_abstraction.state = start_state
    next_state = qpu_abstraction._next_state(event)
    assert next_state is None