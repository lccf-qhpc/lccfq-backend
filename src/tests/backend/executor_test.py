import pytest
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from lccfq_backend.backend.executor import QPUExecutor
from lccfq_backend.config import BackendSettings
from lccfq_backend.model.tasks import CircuitTask, TestTask, ControlTask, TaskType, Gate, TaskStatus
from lccfq_backend.backend.error import UnknownQPUTaskType
from lccfq_backend.model.state import QPUState
from lccfq_backend.backend.users import UserManager
from lccfq_backend.backend.queue import QueueEntry

_config = BackendSettings(hwman_mock_mode=True)


def test_execute_circuit_task():
    executor = QPUExecutor(config=_config, users=UserManager())
    task = CircuitTask(
        task_id="circuit-001",
        type=TaskType.CIRCUIT,
        gates=[Gate(symbol="rx", target_qubits=[0], control_qubits=[], params=[])],
        shots=1000
    )

    result = executor.execute(task, user="alice")
    assert result is None or result.task_id == task.task_id


def test_execute_test_task():
    executor = QPUExecutor(config=_config, users=UserManager())
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


def test_execute_runs_idle_task_only_once(monkeypatch):
    executor = QPUExecutor(
        config=_config,
        users=UserManager(),
    )
    executor.qpu.state = QPUState.IDLE

    task = TestTask(
        task_id="single-execution-task",
        type=TaskType.TEST,
        symbol="xeb",
        params=[1, 2, 3],
        shots=10,
    )

    executed_task_ids = []

    def record_execution(executed_task):
        executed_task_ids.append(executed_task.task_id)
        return None

    monkeypatch.setattr(executor, "_execute_test", record_execution)

    executor.execute(task, user="alice")

    assert executed_task_ids == [task.task_id]
    assert executor.queue.list_pending() == []
    assert executor.get_task_status(task.task_id) == TaskStatus.COMPLETED


def test_execute_control_reset():
    executor = QPUExecutor(config=_config, users=UserManager())
    task = ControlTask(
        task_id="control-001",
        type=TaskType.CONTROL,
        command="reset"
    )

    result = executor.execute(task, user="carol")
    assert result is None or result.status in ["ok", "error", "warning"]


def test_execute_control_unknown_command():
    executor = QPUExecutor(config=_config, users=UserManager())
    task = ControlTask(
        task_id="control-003",
        type=TaskType.CONTROL,
        command="unknown"
    )

    result = executor.execute(task, user="carol")
    if result is not None:
        assert result.status == "error"


def test_execute_unknown_task_type():
    executor = QPUExecutor(config=_config, users=UserManager())

    class FakeTask:
        def __init__(self):
            self.task_id = "fake-001"
            self.type = "nonsense"

    with pytest.raises(UnknownQPUTaskType):
        executor.execute(FakeTask(), user="eve")


def test_dispatch_updates_task_status_to_completed():
    executor = QPUExecutor(
        config=_config,
        users=UserManager(),
    )
    executor.qpu.state = QPUState.IDLE

    task = TestTask(
        task_id="test-status-completed",
        type=TaskType.TEST,
        symbol="xeb",
        params=[1, 2, 3],
        shots=10,
    )

    executor._dispatch(task)

    assert executor.get_task_status(task.task_id) == TaskStatus.COMPLETED


def test_dispatch_updates_task_status_to_failed(monkeypatch):
    executor = QPUExecutor(
        config=_config,
        users=UserManager(),
    )

    task = TestTask(
        task_id="test-status-failed",
        type=TaskType.TEST,
        symbol="xeb",
        params=[1, 2, 3],
        shots=10,
    )

    def raise_execution_error(_task):
        raise RuntimeError("test execution failed")

    monkeypatch.setattr(executor, "_execute_test", raise_execution_error)

    with pytest.raises(RuntimeError, match="test execution failed"):
        executor._dispatch(task)

    assert executor.get_task_status(task.task_id) == TaskStatus.FAILED

def test_task_logs_record_status_transitions():
    executor = QPUExecutor(
        config=_config,
        users=UserManager(),
    )

    task_id = "task-with-logs"

    executor.set_task_status(task_id, TaskStatus.QUEUED)
    executor.set_task_status(task_id, TaskStatus.RUNNING)
    executor.set_task_status(task_id, TaskStatus.COMPLETED)

    assert executor.get_task_logs(task_id) == [
        "Task status changed to queued",
        "Task status changed to running",
        "Task status changed to completed",
    ]
    assert executor.get_task_logs("unknown-task") is None


def test_batched_context_updates_task_status_to_completed():
    executor = QPUExecutor(
        config=_config,
        users=UserManager(),
    )
    executor.qpu.state = QPUState.IDLE

    task = TestTask(
        task_id="batch-status-completed",
        type=TaskType.TEST,
        symbol="xeb",
        params=[1, 2, 3],
        shots=10,
    )

    entry = QueueEntry(
        task_id=task.task_id,
        task=task,
        timestamp=datetime.now(),
        user="alice",
        context_id="context-001",
    )

    results = executor._execute_batched_context([entry])

    assert len(results) == 1
    assert executor.get_task_status(task.task_id) == TaskStatus.COMPLETED

def test_enqueue_task_records_queued_before_running(monkeypatch):
    executor = QPUExecutor(
        config=_config,
        users=UserManager(),
    )

    task = TestTask(
        task_id="atomic-enqueue-task",
        type=TaskType.TEST,
        symbol="xeb",
        params=[1, 2, 3],
        shots=10,
    )

    task_added_to_queue = Event()
    allow_enqueue_to_finish = Event()
    running_status_attempted = Event()

    original_enqueue = executor.queue.enqueue
    original_set_task_status = executor.set_task_status

    def paused_enqueue(*args, **kwargs):
        entry = original_enqueue(*args, **kwargs)
        task_added_to_queue.set()
        allow_enqueue_to_finish.wait(timeout=5)
        return entry

    def observed_set_task_status(task_id, status):
        if status == TaskStatus.RUNNING:
            running_status_attempted.set()

        return original_set_task_status(task_id, status)

    monkeypatch.setattr(executor.queue, "enqueue", paused_enqueue)
    monkeypatch.setattr(executor, "set_task_status", observed_set_task_status)
    monkeypatch.setattr(executor, "_execute_test", lambda _task: None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        enqueue_future = pool.submit(
            executor.enqueue_task,
            task,
            "alice",
        )

        try:
            assert task_added_to_queue.wait(timeout=5)

            execute_future = pool.submit(executor._execute_next)

            assert running_status_attempted.wait(timeout=5)
        finally:
            allow_enqueue_to_finish.set()

        enqueue_future.result(timeout=5)
        execute_future.result(timeout=5)

    assert executor.get_task_status(task.task_id) == TaskStatus.COMPLETED
    assert executor.get_task_logs(task.task_id) == [
        "Task status changed to queued",
        "Task status changed to running",
        "Task status changed to completed",
    ]

def test_cancel_task_removes_queued_task():
    executor = QPUExecutor(
        config=_config,
        users=UserManager(),
    )

    task = TestTask(
        task_id="task-to-cancel",
        type=TaskType.TEST,
        symbol="xeb",
        params=[1, 2, 3],
        shots=10,
    )

    executor.execute(task, user="alice")

    assert executor.get_task_status(task.task_id) == TaskStatus.QUEUED
    assert executor.cancel_task(task.task_id) is True
    assert executor.get_task_status(task.task_id) == TaskStatus.CANCELLED
    assert executor.queue.list_pending() == []
    assert executor.get_task_logs(task.task_id) == [
        "Task status changed to queued",
        "Task status changed to cancelled",
    ]


def test_cancel_task_rejects_running_task():
    executor = QPUExecutor(
        config=_config,
        users=UserManager(),
    )
    executor.set_task_status("running-task", TaskStatus.RUNNING)

    assert executor.cancel_task("running-task") is False
    assert executor.get_task_status("running-task") == TaskStatus.RUNNING