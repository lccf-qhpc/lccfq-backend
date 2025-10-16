"""
Filename: executor_test.py
Author: Santiago Nunez-Corrales
Date: 2025-08-07
Description:
    This file implements a test for the QPU executor.

License: Apache 2.0
"""
import pytest

from lccfq_backend.backend.error import UnknownQPUState
from lccfq_backend.backend.executor import QPUExecutor
from lccfq_backend.model.tasks import Gate, CircuitTask, TestTask, ControlTask, TaskType
from lccfq_backend.backend.error import UnknownQPUTaskType, UnknownQPUState
from lccfq_backend.backend.fsm import QPUEvent, QPUState


@pytest.fixture
def executor():
    executor = QPUExecutor()
    executor.qpu.state = QPUState.IDLE
    return executor

def test_execute_circuit_task(executor):
    task = CircuitTask(
        task_id="circuit-001",
        type=TaskType.CIRCUIT,
        gates=[Gate(
            symbol="rx",
            target_qubits=[0],
            control_qubits=[],
            params=[]  # or use [] if non-parametric
        )],
        shots=1000
    )
    result = executor.execute(task, user="alice")
    assert result is not None
    assert isinstance(result.distribution, dict)
    assert set(result.distribution.keys()) <= {"000", "111"}


def test_execute_test_task(executor):
    task = TestTask(
        task_id="test-001",
        type=TaskType.TEST,
        symbol="xeb",
        params=[1, 2, 3],
        shots=1024
    )
    result = executor.execute(task, user="bob")
    assert result is not None
    assert isinstance(result.parameters, dict)
    assert "fidelity" in result.parameters


def test_execute_control_reset(executor):
    task = ControlTask(
        task_id="control-001",
        type=TaskType.CONTROL,
        command="reset"
    )
    result = executor.execute(task, user="carol")
    assert result is not None
    assert result.status == "ok"
    assert "reset" in result.message.lower()


def test_execute_control_unknown_command(executor):
    task = ControlTask(
        task_id="control-003",
        type=TaskType.CONTROL,
        command="unknown"
    )
    result = executor.execute(task, user="carol")
    assert result.status == "error"
    assert "unknown" in result.message.lower()


def test_execute_unknown_task_type(executor):
    # Simulate a malformed task
    class FakeTask:
        def __init__(self):
            self.task_id = "fake-001"
            self.type = "nonsense"

    with pytest.raises(UnknownQPUTaskType):
        executor.execute(FakeTask(), user="eve")