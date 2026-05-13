"""
Filename: result_store.py
Author: Santiago Nunez-Corrales
Date: 2026-04-07
Version: 1.0
Description:
    Persistent JSON-backed store for task results.
    Each result is written to a timestamped folder named
    {YYYY-MM-DDTHHMMSS}_{task_id}/ containing a single result.json file.

License: Apache 2.0
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from ..model.results import CircuitResult, ControlAck, ResultType, TaskResult, TestResult
from ..utils.log import setup_logger

logger = setup_logger("lccfq.result_store")


class ResultStore:
    """Saves and loads task results as JSON files under results_dir.

    On-disk layout::

        results/
          2026-02-05T083139_<task_id>/
            result.json
          2026-02-05T083205_<task_id>/
            result.json
    """

    def __init__(self, results_dir: Path):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ResultStore initialized at {self.results_dir}")

    def _job_dir(self, task_id: str) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        return self.results_dir / f"{timestamp}_{task_id}"

    def save(self, result: TaskResult) -> None:
        job_dir = self._job_dir(result.task_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / "result.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(result.model_dump_json())
        os.replace(tmp, path)  # atomic on POSIX — prevents partial reads by gRPC thread
        logger.info(f"Result saved: {result.task_id} -> {path}")

    def load(self, task_id: str) -> Optional[Union[CircuitResult, TestResult, ControlAck]]:
        matches = list(self.results_dir.glob(f"*_{task_id}/result.json"))
        if not matches:
            logger.debug(f"No result found for task {task_id}")
            return None
        path = matches[0]  # task_ids are UUIDs — at most one match
        try:
            data = json.loads(path.read_text())
        except Exception as e:
            logger.error(f"Failed to read result file {path}: {e}")
            return None
        match data.get("result_type"):
            case ResultType.CIRCUIT:
                return CircuitResult.model_validate(data)
            case ResultType.TEST:
                return TestResult.model_validate(data)
            case ResultType.CONTROL:
                return ControlAck.model_validate(data)
            case _:
                logger.error(f"Unknown result_type in {path}: {data.get('result_type')!r}")
                return None
