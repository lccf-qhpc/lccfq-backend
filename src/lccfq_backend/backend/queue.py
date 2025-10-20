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
from collections import deque, defaultdict
from ..model.tasks import TaskBase
from ..model.context import QPUExecutionContext
from ..logging.logger import setup_logger

logger = setup_logger("QPUTaskQueue")


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
        self._context_locks: Dict[str, bool] = defaultdict(lambda: False)
        logger.info("Initialized task queue")

    def enqueue(self, task: TaskBase, user: str, context_id: Optional[str] = None, priority: int = 0) -> QueueEntry:
        logger.info(f"Enqueueing task {task.task_id} (type: {task.type}) by user {user}")
        entry = QueueEntry(
            task_id=task.task_id,
            task=task,
            timestamp=datetime.now(),
            user=user,
            context_id=context_id,
            priority=priority
        )

        if task.execution_context:
            ctx_id = task.execution_context.token_id
            if ctx_id and not self._context_locks[ctx_id]:
                self._context_locks[ctx_id] = True
                logger.debug(f"Locked context {ctx_id} for task {task.task_id}")

        self._queue.append(entry)
        return entry

    def dequeue(self) -> Optional[QueueEntry]:
        if not self._queue:
            logger.debug("Dequeue attempted on empty queue")
            return None

        best_entry = min(self._queue, key=lambda entry: (-entry.priority, entry.timestamp))
        self._queue.remove(best_entry)
        logger.info(f"Dequeued task {best_entry.task_id} (type: {best_entry.task.type})")
        return best_entry

    def dequeue_all_for_context(self, context: QPUExecutionContext) -> List[QueueEntry]:
        ctx_id = context.token_id
        matching_entries = [entry for entry in self._queue
                            if entry.task.execution_context and entry.context_id == ctx_id]
        self._queue = deque([entry for entry in self._queue if entry not in matching_entries])

        logger.info(f"Dequeued {len(matching_entries)} task(s) for context {ctx_id}")
        return matching_entries

    def is_locked(self, context: QPUExecutionContext) -> bool:
        locked = self._context_locks.get(context.token_id, False)
        logger.debug(f"Context {context.token_id} locked: {locked}")
        return locked

    def unlock_context(self, context: QPUExecutionContext):
        ctx_id = context.token_id
        if ctx_id in self._context_locks:
            self._context_locks[ctx_id] = False
            logger.info(f"Unlocked context: {ctx_id}")

    def peek(self) -> Optional[QueueEntry]:
        if not self._queue:
            logger.debug("Peek attempted on empty queue")
            return None

        top = min(self._queue, key=lambda entry: (-entry.priority, entry.timestamp))
        logger.debug(f"Peeked task {top.task_id} (type: {top.task.type})")
        return top

    def remove(self, task_id: str) -> bool:
        for i, entry in enumerate(self._queue):
            if entry.task_id == task_id:
                del self._queue[i]
                logger.info(f"Removed task {task_id} from queue")
                return True

        logger.warning(f"Attempted to remove non-existent task {task_id}")
        return False

    def list_pending(self) -> List[QueueEntry]:
        logger.debug(f"Listing {len(self._queue)} pending task(s)")
        return list(self._queue)

    def clear(self):
        size = len(self._queue)
        self._queue.clear()
        logger.info(f"Cleared queue (removed {size} task(s))")