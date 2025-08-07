"""
Filename: observables.py
Author: Santiago Nunez-Corrales
Date: 2025-08-07
Version: 1.0
Description:
    This file implements the model for relevant qubit device quantities.

License: Apache 2.0
Contact: nunezco2@illinois.edu
"""
from typing import Dict
from pydantic import BaseModel, Field
from datetime import datetime


class QubitObservable(BaseModel):
    """Relevant per-qubit observables.

    """
    t1: float
    t2: float
    anharmonicity: float
    frequency: float
    gate_fidelity_1q: float
    gate_fidelity_2q: float
    rx_duration: float
    ry_duration: float
    sqrt_iswap_duration: float
    reset_duration: float
    measurement_duration: float
    max_circuit_depth: int


class QPUObservables(BaseModel):
    """Observables for all qubits."""

    qubits: Dict[int, QubitObservable] = Field(default_factory=dict)
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[int, Dict[str, float]]:
        """Get dictionary representation of QPU observables.

        :return: dictionary of qubits with observables
        """
        return {idx: obs.model_dump() for idx, obs in self.qubits.items()}

    def summary(self) -> str:
        """Summarize observables across qubits."""
        lines = [f"[QPU Observables @ {self.last_updated}]"]

        for idx, obs in self.qubits.items():
            lines.append(f"Qubit {idx}: f={obs.frequency} GHz, T1={obs.t1} μs, T2={obs.t2} μs, "
                         f"F1Q={obs.gate_fidelity_1q}, F2Q={obs.gate_fidelity_2q}, "
                         f"Depth={obs.max_circuit_depth}")

        return "\n".join(lines)