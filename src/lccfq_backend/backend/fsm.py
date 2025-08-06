"""
Filename: fsm.py
Author: Santiago Nunez-Corrales
Date: 2025-08-06
Version: 1.0
Description:
    This file implements the finite state machine governing the QPU abstraction.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
from enum import Enum
from typing import Optional
from ..model.qpu_state import QPUState
from .error import UnknownQPUState


class QPUEvent(str, Enum):
    """Events that trigger state transitions in the QPU abstraction.

    """
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    DEVICE_OK = "device_ok"
    DEVICE_FAIL = "device_fail"
    TUNE_SUCCESS = "tune_success"
    TUNE_FAIL = "tune_fail"
    TASK_STARTED = "task_started"
    TASK_FINISHED = "task_finished"
    FIDELITY_DEGRADED = "fidelity_degraded"
    RESET = "reset"


class QPUAbstraction:
    """Abstraction of a QPU as a finite state machine.

    """

    def __init__(self):
        """The QPU starts with the most conservative assumption, and has to
        increasingly provide evidence of its state.

        """
        self.state: QPUState = QPUState.INACCESSIBLE
        self.last_transition: Optional[str] = None

    def transition(self, event: QPUEvent):
        """Transition function for a QPU.

        :param event: triggering event
        :return: nothing (change of state is side effect)
        """

        prev = self.state
        next_state = self._next_state(event)

        if next_state is None:
            self._invalid_transition(event)
        else:
            self.state = next_state
            self.last_transition = f"{prev} --({event})--> {next_state}"
            self._log(prev, event, next_state)

    def _next_state(self, event: QPUEvent) -> Optional[QPUState]:
        """Implementation of state transition table.

        :param event: triggering event
        :return: new QPU state
        """

        match (self.state, event):
            case (QPUState.INACCESSIBLE, QPUEvent.CONNECT):
                # The QPU connection is successful
                return QPUState.ACCESSIBLE

            case (QPUState.ACCESSIBLE, QPUEvent.DEVICE_OK):
                # The QICK controlled device responds
                return QPUState.RESPONSIVE

            case (QPUState.ACCESSIBLE, QPUEvent.DEVICE_FAIL):
                # The QPU was accessible, but the device/QICK fails and becomes unresponsive
                return QPUState.UNRESPONSIVE

            case (QPUState.RESPONSIVE, QPUEvent.TUNE_SUCCESS):
                # The device/QICK is responsive and was successfully tuned
                return QPUState.TUNED

            case (QPUState.RESPONSIVE, QPUEvent.TUNE_FAIL):
                # The device/QICK is responsive, but tuning failed
                return QPUState.MISTUNED

            case (QPUState.TUNED, QPUEvent.FIDELITY_DEGRADED):
                # The device was previously tuned, but new observations update the state
                return QPUState.MISTUNED

            case (QPUState.MISTUNED, QPUEvent.TUNE_SUCCESS):
                # A tuning task was triggered by the backend and succeeded
                return QPUState.TUNED

            case (QPUState.TUNED, QPUEvent.RESET):
                # Once tuned, the qubits must be reset to |0> to start
                return QPUState.IDLE

            case (QPUState.IDLE, QPUEvent.TASK_STARTED):
                # QPU idle, the scheduler chooses a task
                return QPUState.BUSY

            case (QPUState.BUSY, QPUEvent.TASK_FINISHED):
                # The current task finishes and the QPU becomes available
                return QPUState.IDLE

            case (QPUState.UNRESPONSIVE, QPUEvent.DISCONNECT):
                # QPU is deemed unresponsive, the backend disconnects
                return QPUState.INACCESSIBLE

        return None

    def _invalid_transition(self, event: QPUEvent):
        """Handle invalid transitions

        :param event:
        :return:
        """
        raise UnknownQPUState(event.value)

    def _log(self, prev: QPUState, event: QPUEvent, next_state: QPUState):
        """Log a state transition.

        :param prev: prior state
        :param event: triggering event
        :param next_state: next state
        :return: nothing
        """
        # TODO: implement proper logging later
        print(f"[QPU state] {prev} --({event})--> {next_state}")
