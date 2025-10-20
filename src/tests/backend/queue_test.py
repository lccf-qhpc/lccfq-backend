import pytest
from datetime import datetime
from lccfq_backend.backend.queue import QPUTaskQueue, QueueEntry
from lccfq_backend.model.tasks import CircuitTask, TaskType, Gate
from lccfq_backend.model.context import QPUExecutionContext


def make_task(task_id: str, ctx_id: str = None) -> CircuitTask:
    task = CircuitTask(
        task_id=task_id,
        type=TaskType.CIRCUIT,
        gates=[Gate(symbol="rx", target_qubits=[0], control_qubits=[], params=[])],
        shots=1000
    )
    if ctx_id:
        task.execution_context = QPUExecutionContext(token_id=ctx_id, user_id="tim")
    return task


def test_enqueue_and_dequeue():
    queue = QPUTaskQueue()
    task = make_task("t1")
    entry = queue.enqueue(task, user="alice", priority=2)
    assert entry.task_id == "t1"

    dequeued = queue.dequeue()
    assert dequeued is not None
    assert dequeued.task.task_id == "t1"


def test_peek():
    queue = QPUTaskQueue()
    task1 = make_task("t1")
    task2 = make_task("t2")
    queue.enqueue(task1, user="bob", priority=1)
    queue.enqueue(task2, user="bob", priority=2)

    top = queue.peek()
    assert top is not None
    assert top.task.task_id == "t2"  # higher priority


def test_remove_task():
    queue = QPUTaskQueue()
    task = make_task("t-remove")
    queue.enqueue(task, user="alice")
    removed = queue.remove("t-remove")
    assert removed is True
    assert queue.peek() is None


def test_list_pending():
    queue = QPUTaskQueue()
    queue.enqueue(make_task("a"), user="x")
    queue.enqueue(make_task("b"), user="x")
    assert len(queue.list_pending()) == 2


def test_priority_ordering():
    queue = QPUTaskQueue()
    task1 = make_task("low")
    task2 = make_task("high")
    queue.enqueue(task1, user="a", priority=1)
    queue.enqueue(task2, user="b", priority=5)

    dequeued = queue.dequeue()
    assert dequeued is not None
    assert dequeued.task.task_id == "high"


def test_context_locking_and_unlock():
    queue = QPUTaskQueue()
    ctx = QPUExecutionContext(token_id="CTX1", user_id="bob")
    task = make_task("t1", ctx_id="CTX1")
    queue.enqueue(task, user="alice")

    assert queue.is_locked(ctx) is True
    queue.unlock_context(ctx)
    assert queue.is_locked(ctx) is False


def test_dequeue_all_for_context():
    queue = QPUTaskQueue()
    ctx = QPUExecutionContext(token_id="CTX1", user_id="alice")

    task1 = make_task("a", ctx_id="CTX1")
    task2 = make_task("b", ctx_id="CTX1")
    task3 = make_task("c")  # unrelated

    queue.enqueue(task1, user="alice", context_id="CTX1")
    queue.enqueue(task2, user="alice", context_id="CTX1")
    queue.enqueue(task3, user="bob", context_id=None)

    entries = queue.dequeue_all_for_context(ctx)
    assert len(entries) == 2
    task_ids = [entry.task.task_id for entry in entries]
    assert "a" in task_ids
    assert "b" in task_ids