"""
queue.py - Internal QPU task queue
Author: Santiago Núñez-Corrales
Date: 2025-10-16

This module implements the backend queue abstraction for LCCFQ. It allows pending quantum tasks
from multiple users and programs to be stored, dequeued, inspected, and managed with context control.

"""
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
from collections import deque, defaultdict
from ..model.tasks import TaskBase
from ..model.context import QPUExecutionContext
from threading import Lock
import uuid
import asyncio


@dataclass
class QueueEntry:
    task_id: str
    task: object  # CircuitTask, TestTask, ControlTask
    timestamp: datetime
    user: str
    context_id: Optional[str] = None
    priority: int = 0


class QPUTaskQueue:
    """Thread-safe synchronous task queue with optional async context handling."""

    def __init__(self):
        self._queue: deque[QueueEntry] = deque()
        self._context_locks: Dict[str, bool] = defaultdict(lambda: False)

    # -----------------------------
    # Main synchronous operations
    # -----------------------------

    def enqueue(self, task: TaskBase, user: str, context_id: Optional[str] = None,
                priority: int = 0) -> QueueEntry:
        """Synchronously enqueue a new task."""
        #with self._lock:
        print(f"[QPUTaskQueue] Enqueueing task {task.task_id} (type: {task.type}) by user {user}")

        entry = QueueEntry(
            task_id=task.task_id,
            task=task,
            timestamp=datetime.now(),
            user=user,
            context_id=context_id,
            priority=priority
        )

        # Context lock registration
        if getattr(task, "execution_context", None):
            ctx_id = task.execution_context.token_id
            if ctx_id and not self._context_locks[ctx_id]:
                self._context_locks[ctx_id] = True

        self._queue.append(entry)
        return entry

    def dequeue(self) -> Optional[QueueEntry]:
        """Remove and return the highest-priority (or earliest) task."""
        #with self._lock:
        if not self._queue:
            return None

        best_entry = min(self._queue, key=lambda e: (-e.priority, e.timestamp))
        self._queue.remove(best_entry)
        return best_entry

    def peek(self) -> Optional[QueueEntry]:
        """Return (but do not remove) the next task in queue."""
        #with self._lock:
        if not self._queue:
            return None

        return min(self._queue, key=lambda e: (-e.priority, e.timestamp))

    def remove(self, task_id: str) -> bool:
        """Remove a specific task from the queue by ID."""
        #with self._lock:
        for i, entry in enumerate(self._queue):
            if entry.task_id == task_id:
                del self._queue[i]
                return True

        return False

    def list_pending(self) -> List[QueueEntry]:
        """List all pending tasks."""
        #with self._lock:
        return list(self._queue)

    def clear(self):
        """Remove all tasks from the queue."""
        #with self._lock:
        self._queue.clear()

    def dequeue_all_for_context(self, context: QPUExecutionContext) -> List[TaskBase]:
        ctx_id = context.token_id
        matching_entries = [entry for entry in self._queue
                            if entry.task.execution_context and entry.context_id == ctx_id]
        self._queue = deque([task for task in self._queue if task not in matching_entries])

        print(f"[QPUTaskQueue] Dequeued {len(matching_entries)} task(s) for context {ctx_id}")

        return matching_entries

    def is_locked(self, context: QPUExecutionContext) -> bool:
        """Check whether a context is currently locked."""
        return self._context_locks.get(context.token_id, False)

    def unlock_context(self, context: QPUExecutionContext):
        """Release a context lock after batch execution."""
        ctx_id = context.token_id
        if ctx_id in self._context_locks:
            self._context_locks[ctx_id] = False
            print(f"[QPUTaskQueue] Unlocked context: {ctx_id}")