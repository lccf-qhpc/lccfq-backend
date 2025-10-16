"""
queue.py - Internal QPU task queue
Author: Santiago Núñez-Corrales
Date: 2025-10-16

This module implements the backend queue abstraction for LCCFQ. It allows pending quantum tasks
from multiple users and programs to be stored, dequeued, inspected, and managed with context control.

"""

from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import uuid


@dataclass
class QueueEntry:
    task_id: str
    task: object  # Any of: CircuitTask, TestTask, ControlTask
    timestamp: datetime
    user: str
    context_id: Optional[str] = None
    priority: int = 0


class QPUTaskQueue:
    def __init__(self):
        self._queue: deque[QueueEntry] = deque()

    def enqueue(self, task: object, user: str, context_id: Optional[str] = None, priority: int = 0) -> QueueEntry:
        task_id = str(uuid.uuid4())
        entry = QueueEntry(
            task_id=task_id,
            task=task,
            timestamp=datetime.now(),
            user=user,
            context_id=context_id,
            priority=priority
        )
        self._queue.append(entry)

        return entry

    def dequeue(self) -> Optional[QueueEntry]:
        if self._queue:
            return self._queue.popleft()

        return None

    def peek(self) -> Optional[QueueEntry]:
        if self._queue:
            return self._queue[0]
        return None

    def remove(self, task_id: str) -> bool:
        for i, entry in enumerate(self._queue):
            if entry.task_id == task_id:
                del self._queue[i]
                return True
        return False

    def list_pending(self) -> List[QueueEntry]:
        return list(self._queue)

    def clear(self):
        self._queue.clear()