import pytest
from lccfq_backend.backend.queue import QPUTaskQueue, QueueEntry

# Updated DummyTask with a realistic interface
class DummyTask:
    def __init__(self, name: str):
        self.name = name
        self.task_id = f"dummy-{name}"

    def __repr__(self):
        return f"<DummyTask {self.name}>"

@pytest.fixture
def queue():
    return QPUTaskQueue()

def test_enqueue_and_dequeue(queue):
    task = DummyTask("task1")
    tid = queue.enqueue(task, user="alice")
    assert isinstance(tid, QueueEntry)
    entry = queue.dequeue()
    assert isinstance(entry, QueueEntry)
    assert isinstance(entry.task, DummyTask)
    assert entry.task.name == "task1"
    assert entry.user == "alice"

def test_peek(queue):
    queue.enqueue(DummyTask("t1"), "u1")
    queue.enqueue(DummyTask("t2"), "u2")
    peeked = queue.peek()
    assert peeked is not None
    assert isinstance(peeked.task, DummyTask)
    assert peeked.task.name == "t1"
    assert peeked.user == "u1"

def test_remove_task(queue):
    entry = queue.enqueue(DummyTask("t1"), "u1")
    found = queue.remove(entry.task_id)
    assert found is True
    assert queue.dequeue() is None

def test_list_pending(queue):
    queue.enqueue(DummyTask("t1"), "u1")
    queue.enqueue(DummyTask("t2"), "u2")
    pending = queue.list_pending()
    assert len(pending) == 2
    assert pending[0].user == "u1"
    assert pending[1].user == "u2"
    assert pending[0].task.name == "t1"
    assert pending[1].task.name == "t2"

def test_clear(queue):
    queue.enqueue(DummyTask("t1"), "u1")
    queue.enqueue(DummyTask("t2"), "u2")
    queue.clear()
    assert queue.list_pending() == []