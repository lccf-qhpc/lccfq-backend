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
from typing import Union
from ..model.tasks import CircuitTask, TestTask, ControlTask, TaskType
from ..model.results import CircuitResult, TestResult, ControlAck
from .fsm import QPUAbstraction, QPUEvent
from .error import UnknownQPUTaskType
# from .hwman_client import HWManClient


class QPUExecutor:
    """Representation of the QPU executor

    """

    def __init__(self):
        self.qpu = QPUAbstraction()
        # self.hwman = HWManClient(...)

    def execute(self, task: Union[CircuitTask, TestTask, ControlTask]):
        """Dispatch mechanism for tasks.

        :param task: a circuit, a test or a control task
        :return: result of action
        """
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
        """Execute a circuit task.

        :param task: circuit task
        :return: result of executing the circuit
        """
        self.qpu.transition(QPUEvent.TASK_STARTED)

        # result = self.hwman.run_circuit(task.gates, task.shots)
        result = {"000": 420, "111": 580}  # placeholder

        self.qpu.transition(QPUEvent.TASK_FINISHED)
        return CircuitResult(task_id=task.task_id, distribution=result)

    def _execute_test(self, task: TestTask) -> TestResult:
        """Execute a test task.

        :param task: test task
        :return: test results
        """
        self.qpu.transition(QPUEvent.TASK_STARTED)

        # params = self.hwman.run_test(task.symbol, task.params, task.shots)
        params = {
            "fidelity": 0.982,
            "xeb_fit": 0.975
        }

        self.qpu.transition(QPUEvent.TASK_FINISHED)
        return TestResult(task_id=task.task_id, parameters=params)

    def _execute_control(self, task: ControlTask) -> ControlAck:
        """Execute a control task.

        Note that control tasks do not reach the QPU, and only model the state in the backend.

        :param task:
        :return:
        """
        match task.command:
            case "reset":
                self.qpu.transition(QPUEvent.RESET)
                return ControlAck(task_id=task.task_id, status="ok", message="QPU reset")
            case "disconnect":
                self.qpu.transition(QPUEvent.DISCONNECT)
                return ControlAck(task_id=task.task_id, status="ok", message="Disconnected from QPU")
            case _:
                return ControlAck(task_id=task.task_id, status="error", message=f"Unknown control: {task.command}")
