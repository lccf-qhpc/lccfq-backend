"""
Filename: error.py
Author: Santiago Nunez-Corrales
Date: 2025-08-06
Version: 1.0
Description:
    This file implements named errors across the backend.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""

class UnknownQPUState(Exception):
    """Exception raised when the QPU topology not the correct one.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, state):
        self.message = f"QPU state unknown - {state}. Critical failure. Aborting."
        super().__init__(self.message)