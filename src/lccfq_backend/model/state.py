"""
Filename: state.py
Author: Santiago Nunez-Corrales
Date: 2025-08-06
Version: 1.0
Description:
    This file defines the finite state machine that provides the QPU abstraction.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
from enum import Enum


class QPUState(str, Enum):
    """Possible QPU states.

    """
    ACCESSIBLE = "accessible"
    RESPONSIVE = "responsive"
    TUNED = "tuned"
    IDLE = "idle"
    BUSY = "busy"
    MISTUNED = "mis-tuned"
    UNRESPONSIVE = "unresponsive"
    INACCESSIBLE = "inaccessible"
