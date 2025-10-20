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
from ..model.state import QPUState
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
    RETUNE = "retune"
    QTOL_OK = "qtol_ok"
    QTOL_WARN = "qtol_warn"
    QTOL_FAIL = "qtol_fail"


class QPUAbstraction:
    """Abstraction of a QPU as a finite state machine.

    """

    # State transitions
    TRANSITIONS: dict[tuple[QPUState, QPUEvent], QPUState] = {
        (QPUState.INACCESSIBLE, QPUEvent.CONNECT): QPUState.ACCESSIBLE,
        (QPUState.UNRESPONSIVE, QPUEvent.DISCONNECT): QPUState.INACCESSIBLE,
        (QPUState.ACCESSIBLE, QPUEvent.DEVICE_OK): QPUState.RESPONSIVE,
        (QPUState.ACCESSIBLE, QPUEvent.DEVICE_FAIL): QPUState.UNRESPONSIVE,
        (QPUState.RESPONSIVE, QPUEvent.TUNE_SUCCESS): QPUState.TUNED,
        (QPUState.RESPONSIVE, QPUEvent.TUNE_FAIL): QPUState.MISTUNED,
        (QPUState.MISTUNED, QPUEvent.TUNE_SUCCESS): QPUState.TUNED,
        (QPUState.TUNED, QPUEvent.FIDELITY_DEGRADED): QPUState.MISTUNED,
        (QPUState.TUNED, QPUEvent.RESET): QPUState.IDLE,
        (QPUState.IDLE, QPUEvent.RESET): QPUState.IDLE,
        (QPUState.IDLE, QPUEvent.TASK_STARTED): QPUState.BUSY,
        (QPUState.BUSY, QPUEvent.TASK_FINISHED): QPUState.IDLE,
        (QPUState.MISTUNED, QPUEvent.RETUNE): QPUState.RESPONSIVE,
        (QPUState.TUNED, QPUEvent.RETUNE): QPUState.RESPONSIVE,
        (QPUState.TUNED, QPUEvent.QTOL_OK): QPUState.TUNED,
        (QPUState.TUNED, QPUEvent.QTOL_WARN): QPUState.TUNED,
        (QPUState.TUNED, QPUEvent.QTOL_FAIL): QPUState.MISTUNED,
    }

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
        return self.TRANSITIONS.get((self.state, event))

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
