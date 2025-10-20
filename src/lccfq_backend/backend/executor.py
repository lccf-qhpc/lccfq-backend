"""
Filename: executor.py
Author: Santiago Nunez-Corrales
Date: 2025-08-07
Version: 1.0
Description:
    This file implements the executor for task execution.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
from typing import Union, Optional, List
from ..model.tasks import CircuitTask, TestTask, ControlTask, TaskType, TaskBase
from ..model.results import CircuitResult, TestResult, ControlAck, TaskResult
from .queue import QPUTaskQueue, QueueEntry
from .fsm import QPUAbstraction, QPUEvent, QPUState
from .error import UnknownQPUTaskType, QPUQueueEmpty
from .hwman_client import HWManClient, HWManStatus


class QPUExecutor:
    """Representation of the QPU executor"""

    def __init__(self):
        self.qpu = QPUAbstraction()
        self.hwman = HWManClient()
        self.queue = QPUTaskQueue()

    def execute(self, task: TaskBase, user: str,
                      context_id: Optional[str] = None,
                      priority: int = 0) -> Optional[TaskResult]:
        """
        Dispatches a task to the appropriate handler or enqueues it for execution.
        Returns the result if executed immediately, otherwise None.
        """
        # Check task type
        if task.type not in TaskType:
            raise UnknownQPUTaskType(task.type)

        # Create queue entry (async call!)
        entry = self.queue.enqueue(
            task=task,
            user=user,
            context_id=context_id,
            priority=priority
        )

        print(f"[QPUExecutor] Task enqueued: {task.task_id} ({task.type}) by {user}")

        # Decide whether to execute now or later
        if self.qpu.state != QPUState.IDLE:
            print(f"[QPUExecutor] QPU busy (state: {self.qpu.state}), deferring task {task.task_id}")
            return None

        # If READY, dispatch execution
        return self._dispatch(task)

    def _dispatch(self, task: Union[CircuitTask, TestTask, ControlTask]) -> Optional[
        Union[CircuitResult, TestResult, ControlAck]]:
        """Dispatch a task to its proper execution routine."""
        result = None

        match task.type:
            case TaskType.CIRCUIT:
                result = self._execute_circuit(task)
            case TaskType.TEST:
                result = self._execute_test(task)
            case TaskType.CONTROL:
                result = self._execute_control(task)
            case _:
                raise UnknownQPUTaskType(task.type)

        # After any successful execution, check if pending tasks can run
        self._handle_deferred_tasks()
        return result

    def _execute_next(self) -> Optional[
        Union[CircuitResult, TestResult, ControlAck, List[Union[CircuitResult, TestResult, ControlAck]]]]:
        """Dequeue and execute the next task in the queue."""
        entry = self.queue.dequeue()
        if not entry:
            raise QPUQueueEmpty("No pending tasks in the queue.")

        context_id = entry.context_id

        if context_id:
            # Execute all tasks sharing the same context
            # (async method → must be awaited from caller)
            print(f"[QPUExecutor] Executing context batch {context_id}")
            return asyncio.run(self.queue.dequeue_all_for_context(context_id))
        else:
            print(f"[QPUExecutor] Executing single task {entry.task.task_id} ({entry.task.type})")
            return self._dispatch(entry.task)

    def _execute_batched_context(
            self, context_entries: List[QueueEntry]
    ) -> List[Union[CircuitResult, TestResult, ControlAck]]:
        """Execute all tasks associated with a single context sequentially."""
        results = []

        print(f"[QPUExecutor] Beginning execution of context batch: {context_entries[0].context_id}")

        for entry in context_entries:
            task: TaskBase = entry.task
            print(f"[QPUExecutor] Executing task {task.task_id} in context {entry.context_id}")

            match task.type:
                case TaskType.CIRCUIT:
                    result = self._execute_circuit(task)
                case TaskType.TEST:
                    result = self._execute_test(task)
                case TaskType.CONTROL:
                    result = self._execute_control(task)
                case _:
                    raise UnknownQPUTaskType(task.type)

            results.append(result)

        print(f"[QPUExecutor] Completed execution of context batch {context_entries[0].context_id}")

        self._handle_deferred_tasks()
        return results

    def _handle_deferred_tasks(self):
        """Process any pending tasks if QPU becomes idle."""
        while self.qpu.state == QPUState.IDLE:
            entry = self.queue.dequeue()
            if not entry:
                break  # Queue is empty

            print(f"[QPUExecutor] Executing deferred task {entry.task.task_id} ({entry.task.type})")
            result = self._dispatch(entry.task)
            print(f"[QPUExecutor] Deferred task {entry.task.task_id} completed with result: {result}")

    def _execute_circuit(self, task: CircuitTask) -> CircuitResult:
        self.qpu.transition(QPUEvent.TASK_STARTED)
        result = self.hwman.run_circuit(task.gates, task.shots)
        self.qpu.transition(QPUEvent.TASK_FINISHED)
        return CircuitResult(task_id=task.task_id, distribution=result)

    def _execute_test(self, task: TestTask) -> TestResult:
        self.qpu.transition(QPUEvent.TASK_STARTED)
        params = self.hwman.run_test(task.symbol, task.params, task.shots)
        self.qpu.transition(QPUEvent.TASK_FINISHED)
        return TestResult(task_id=task.task_id, parameters=params)

    def _execute_control(self, task: ControlTask) -> ControlAck:
        match task.command:
            case "reset":
                self.qpu.transition(QPUEvent.RESET)
                return ControlAck(task_id=task.task_id, status="ok", message="QPU reset")
            case "retune":
                result = self.hwman.retune()
                if result.status == HWManStatus.OK:
                    self.qpu.update_observables(result.observables)
                    self.qpu.transition(QPUEvent.RETUNE)
                    return ControlAck(task_id=task.task_id, status="ok", message="QPU successfully re-tuned")
                else:
                    self.qpu.transition(QPUEvent.TUNE_FAIL)
                    return ControlAck(task_id=task.task_id, status="error", message=result.message)
            case "resetall":
                result = self.hwman.reset_all()
                if result.status == HWManStatus.OK:
                    self.qpu.transition(QPUEvent.RESET)
                    return ControlAck(task_id=task.task_id, status="ok", message="Full QPU reset complete")
                else:
                    self.qpu.transition(QPUEvent.TUNE_FAIL)
                    return ControlAck(task_id=task.task_id, status="error", message=result.message)
            case "qtol":
                tolerance = float(task.params[0]) if task.params else 0.98
                max_retries = int(task.params[1]) if len(task.params) > 1 else 3

                for attempt in range(max_retries):
                    fidelity = self.hwman.evaluate_fidelity()
                    if fidelity >= tolerance:
                        self.qpu.transition(QPUEvent.TUNE_SUCCESS)
                        return ControlAck(
                            task_id=task.task_id, status="ok",
                            message=f"Fidelity {fidelity:.3f} meets tolerance {tolerance:.3f}"
                        )
                    self.hwman.retune()

                fidelity = self.hwman.evaluate_fidelity()
                if fidelity >= tolerance:
                    self.qpu.transition(QPUEvent.TUNE_SUCCESS)
                    return ControlAck(
                        task_id=task.task_id, status="warning",
                        message=f"Fidelity {fidelity:.3f} meets tolerance after retries"
                    )
                else:
                    self.qpu.transition(QPUEvent.TUNE_FAIL)
                    return ControlAck(
                        task_id=task.task_id, status="error",
                        message=f"Fidelity {fidelity:.3f} below tolerance {tolerance:.3f}"
                    )
            case _:
                return ControlAck(task_id=task.task_id, status="error", message=f"Unknown control: {task.command}")