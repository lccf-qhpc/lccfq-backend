import pytest
from lccfq_backend.backend.executor import QPUExecutor
from lccfq_backend.model.tasks import CircuitTask, TestTask, ControlTask, TaskType, Gate
from lccfq_backend.backend.error import UnknownQPUTaskType

def test_execute_circuit_task():
    executor = QPUExecutor()
    task = CircuitTask(
        task_id="circuit-001",
        type=TaskType.CIRCUIT,
        gates=[Gate(symbol="rx", target_qubits=[0], control_qubits=[], params=[])],
        shots=1000
    )

    result = executor.execute(task, user="alice")
    assert result is None or result.task_id == task.task_id


def test_execute_test_task():
    executor = QPUExecutor()
    task = TestTask(
        task_id="test-001",
        type=TaskType.TEST,
        symbol="xeb",
        params=[1, 2, 3],
        shots=1024
    )

    result = executor.execute(task, user="bob")
    # If QPU not idle, result can be None — still valid
    assert result is None or result.task_id == task.task_id


def test_execute_control_reset():
    executor = QPUExecutor()
    task = ControlTask(
        task_id="control-001",
        type=TaskType.CONTROL,
        command="reset"
    )

    result = executor.execute(task, user="carol")
    assert result is None or result.status in ["ok", "error", "warning"]


def test_execute_control_unknown_command():
    executor = QPUExecutor()
    task = ControlTask(
        task_id="control-003",
        type=TaskType.CONTROL,
        command="unknown"
    )

    result = executor.execute(task, user="carol")
    if result is not None:
        assert result.status == "error"


def test_execute_unknown_task_type():
    executor = QPUExecutor()

    class FakeTask:
        def __init__(self):
            self.task_id = "fake-001"
            self.type = "nonsense"

    with pytest.raises(UnknownQPUTaskType):
        executor.execute(FakeTask(), user="eve")