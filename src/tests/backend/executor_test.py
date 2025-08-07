"""
Filename: executor_test.py
Author: Santiago Nunez-Corrales
Date: 2025-08-07
Description:
    This file implements a test for the QPU executor.

License: Apache 2.0
"""
import pytest
from lccfq_backend.backend.executor import QPUExecutor
from lccfq_backend.model.tasks import Gate, CircuitTask, TestTask, ControlTask
from lccfq_backend.backend.error import UnknownQPUTaskType
from lccfq_backend.backend.fsm import QPUEvent


def bring_executor_to_idle_state(executor: QPUExecutor):
    executor.qpu.transition(QPUEvent.CONNECT)
    executor.qpu.transition(QPUEvent.DEVICE_OK)
    executor.qpu.transition(QPUEvent.TUNE_SUCCESS)
    executor.qpu.transition(QPUEvent.RESET)


def bring_executor_to_tuned_state(executor: QPUExecutor):
    executor.qpu.transition(QPUEvent.CONNECT)
    executor.qpu.transition(QPUEvent.DEVICE_OK)
    executor.qpu.transition(QPUEvent.TUNE_SUCCESS)


def bring_executor_to_unresponsive_state(executor: QPUExecutor):
    executor.qpu.transition(QPUEvent.CONNECT)
    executor.qpu.transition(QPUEvent.DEVICE_FAIL)


def test_execute_circuit_task():
    executor = QPUExecutor()
    bring_executor_to_idle_state(executor)

    gate = Gate(symbol="rx", target_qubits=[0], control_qubits=[], params=[3.14])
    task = CircuitTask(gates=[gate], shots=1000)

    result = executor.execute(task)
    assert result.task_id == task.task_id
    assert isinstance(result.distribution, dict)
    assert set(result.distribution.keys()) <= {"000", "111"}
    assert executor.qpu.state.name == "IDLE"


def test_execute_test_task():
    executor = QPUExecutor()
    bring_executor_to_idle_state(executor)

    task = TestTask(symbol="xeb", params=[0, 1], shots=512)
    result = executor.execute(task)

    assert result.task_id == task.task_id
    assert isinstance(result.parameters, dict)
    assert "fidelity" in result.parameters
    assert "xeb_fit" in result.parameters
    assert executor.qpu.state.name == "IDLE"


def test_execute_control_reset():
    executor = QPUExecutor()
    bring_executor_to_tuned_state(executor)

    task = ControlTask(command="reset")
    result = executor.execute(task)

    assert result.status == "ok"
    assert "reset" in result.message.lower()
    assert executor.qpu.state.name == "IDLE"


def test_execute_control_disconnect():
    executor = QPUExecutor()
    bring_executor_to_unresponsive_state(executor)

    task = ControlTask(command="disconnect")
    result = executor.execute(task)

    assert result.status == "ok"
    assert "disconnect" in result.message.lower()
    assert executor.qpu.state.name == "INACCESSIBLE"


def test_execute_control_unknown_command():
    executor = QPUExecutor()

    task = ControlTask(command="self_destruct")
    result = executor.execute(task)

    assert result.status == "error"
    assert "unknown" in result.message.lower()


def test_execute_unknown_task_type():
    executor = QPUExecutor()

    class DummyTask:
        type = "alien_task"

    with pytest.raises(UnknownQPUTaskType):
        executor.execute(DummyTask())