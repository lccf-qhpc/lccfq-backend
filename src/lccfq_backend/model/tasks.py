"""
Filename: tasks.py
Author: Santiago Nunez-Corrales
Date: 2025-08-06
Version: 1.0
Description:
    This file defines a model for tasks addressed by the backend.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
import uuid
import os

from abc import ABC
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Task types LCCFQ backed admits
    """
    CIRCUIT = "circuit"
    TEST = "test"
    CONTROL = "control"


def generate_task_id() -> str:
    """Generate a unique task id

    :return: UUID for a task
    """
    return str(uuid.uuid4())


def get_current_user() -> str:
    """Get current users. This may need to be a
    parameter sent by lccfq_lang.

    :return: username
    """
    return os.getlogin()


def current_timestamp() -> str:
    """Get current timestamp

    :return: timestamp
    """
    return datetime.now().isoformat()


class TaskBase(BaseModel, ABC):
    """Abstract class for lccfq_backend tasks

    """
    task_id: str = Field(default_factory=generate_task_id)
    user: str = Field(default_factory=get_current_user)
    program_id: Optional[int] = None
    timestamp: str = Field(default_factory=current_timestamp)
    tags: Dict[str, str] = Field(default_factory=dict)

    type: TaskType

    class Config:
        use_enum_values = True


class Gate(BaseModel):
    """Matching gate definition from lccfq_lang

    """
    symbol: str
    target_qubits: List[int]
    control_qubits: List[int]
    params: List[float]

    def __repr__(self):
        """Represent a gate

        :return: string representation of gate
        """
        return f"{self.symbol} @ {self.target_qubits} ctrl {self.control_qubits} params={self.params}"


class CircuitTask(TaskBase):
    """Model for a circuit-based task

    """
    type: TaskType = Field(default=TaskType.CIRCUIT, const=True)
    gates: List[Gate]
    shots: int


class TestTask(TaskBase):
    """Model for a test task

    """
    type: TaskType = Field(default=TaskType.TEST, const=True)
    symbol: str
    params: List[int]
    shots: int


class ControlTask(TaskBase):
    """Model for a control task

    """
    type: TaskType = Field(default=TaskType.CONTROL, const=True)
    command: str
    params: Optional[List[int]] = Field(default_factory=list)