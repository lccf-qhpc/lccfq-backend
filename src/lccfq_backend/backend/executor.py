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
from typing import Union, Optional
from ..model.tasks import CircuitTask, TestTask, ControlTask, TaskType
from ..model.results import CircuitResult, TestResult, ControlAck
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

    def execute(self, task: Union[CircuitTask, TestTask, ControlTask], user: str):
        """Enqueue and dispatch a QPU task.

        :param task: a circuit, test or control task
        :param user: user requesting task
        :return: result if executed, or None if deferred
        """
        entry = self.queue.enqueue(task, user=user)

        print(f"[QPUExecutor] Task enqueued: {entry.task.task_id} ({task.type}) by {user}")

        if not self.qpu.state == QPUState.IDLE:
            print(f"[QPUExecutor] QPU busy (state: {self.qpu.state}), deferring task {entry.task.task_id}")
            return None

        return self._execute_next()

    def _execute_next(self) -> Optional[Union[CircuitResult, TestResult, ControlAck]]:
        """Try to dequeue and execute next task."""
        entry = self.queue.dequeue()

        print(entry)

        if not entry:
            raise QPUQueueEmpty()

        task = entry.task
        print(f"[QPUExecutor] Dispatching task {task.task_id} ({task.type}) for user {entry.user}")

        match task.type:
            case TaskType.CIRCUIT:
                return self._execute_circuit(task)
            case TaskType.TEST:
                return self._execute_test(task)
            case TaskType.CONTROL:
                return self._execute_control(task)
            case _:
                raise UnknownQPUTaskType(task.type)

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
                        return ControlAck(task_id=task.task_id, status="ok",
                                          message=f"Fidelity {fidelity:.3f} meets tolerance {tolerance:.3f}")
                    self.hwman.retune()

                fidelity = self.hwman.evaluate_fidelity()

                if fidelity >= tolerance:
                    self.qpu.transition(QPUEvent.TUNE_SUCCESS)
                    return ControlAck(task_id=task.task_id, status="warning",
                                      message=f"Fidelity {fidelity:.3f} meets tolerance after retries, but warning issued")
                else:
                    self.qpu.transition(QPUEvent.TUNE_FAIL)
                    return ControlAck(task_id=task.task_id, status="error",
                                      message=f"Fidelity {fidelity:.3f} below tolerance {tolerance:.3f}")
            case _:
                return ControlAck(task_id=task.task_id, status="error", message=f"Unknown control: {task.command}")
