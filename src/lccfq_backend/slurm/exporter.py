"""
Filename: exporter.py
Author: Santiago Nunez-Corrales
Date: 2025-10-24
Description:
    SLURM-compatible exporter for QPU observables.

License: Apache 2.0
"""

import os
from pathlib import Path
from typing import Optional

from ..model.observables import QPUObservables
from ..logging.logger import setup_logger

logger = setup_logger("slurm.exporter")

EXPORT_PATH = Path("/tmp/qpu_observables.env")


def export_observables(
        obs: QPUObservables,
        out_path: Path = EXPORT_PATH,
        include_all: bool = False,
        max_qubits: Optional[int] = None,
):
    """
    Export QPU observables in SLURM-compatible env format (KEY=VALUE per line).

    :param obs: QPUObservables instance
    :param out_path: Path to write SLURM-readable env file
    :param include_all: Whether to export all fields or a summary subset
    :param max_qubits: Max number of qubits to export (by index)
    """
    lines = []
    logger.info(f"[Exporter] Exporting QPU observables to {out_path}")

    for qidx, qobs in sorted(obs.qubits.items()):
        if max_qubits is not None and qidx >= max_qubits:
            break

        if include_all:
            for field, value in qobs.model_dump().items():
                key = f"Q{qidx}_{field.upper()}"
                lines.append(f"{key}={value}")
        else:
            lines.append(f"Q{qidx}_FREQ={qobs.frequency}")
            lines.append(f"Q{qidx}_T1={qobs.t1}")
            lines.append(f"Q{qidx}_T2={qobs.t2}")
            lines.append(f"Q{qidx}_F1Q={qobs.gate_fidelity_1q}")
            lines.append(f"Q{qidx}_F2Q={qobs.gate_fidelity_2q}")
            lines.append(f"Q{qidx}_DEPTH={qobs.max_circuit_depth}")

    lines.append(f"QPU_LAST_UPDATED={obs.last_updated}")

    try:
        with open(out_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"[Exporter] Wrote {len(lines)} lines to {out_path}")
    except Exception as e:
        logger.error(f"[Exporter] Failed to write observables: {e}")