"""
Filename: context.py
Author: Santiago Núñez-Corrales
Date: 2025-10-16

This module implements a context for related tasks.

"""
from pydantic import BaseModel


class QPUExecutionContext(BaseModel):
    """
    Represents a context for atomic execution of a group of QPU tasks.
    Ensures that all tasks sharing this context will be executed sequentially
    and without interleaving with tasks from other contexts.

    Fields:
        token_id: Identifier for the program or job group.
        user_id: User that submitted the program.
    """
    token_id: str
    user_id: str
