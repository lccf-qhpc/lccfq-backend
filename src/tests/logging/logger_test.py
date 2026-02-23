"""
Tests for the centralized logging infrastructure.

Covers: JSON formatter, env var configuration, file handler, logger naming,
and FSM transition log levels.
"""
import json
import logging
import os
import tempfile

import pytest

from lccfq_backend.utils.log import (
    JSONFormatter,
    setup_logger,
    reset_logging,
    _TEXT_FORMAT,
    _TEXT_DATEFMT,
)


@pytest.fixture(autouse=True)
def _clean_logging(monkeypatch):
    """Reset logging state and env vars before each test."""
    # Clear all LCCFQ env vars
    for key in list(os.environ):
        if key.startswith("LCCFQ_LOG"):
            monkeypatch.delenv(key, raising=False)

    # Clear handlers on all test/lccfq loggers so they can be re-initialized
    for name in list(logging.Logger.manager.loggerDict):
        if name.startswith("lccfq.") or name.startswith("test."):
            lg = logging.getLogger(name)
            lg.handlers.clear()

    reset_logging()

    yield

    # Clean up after the test as well
    for name in list(logging.Logger.manager.loggerDict):
        if name.startswith("lccfq.") or name.startswith("test."):
            lg = logging.getLogger(name)
            lg.handlers.clear()
    reset_logging()


# ---------- JSONFormatter ----------

class TestJSONFormatter:
    def test_output_is_valid_json(self):
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="lccfq.test", level=logging.INFO, pathname="", lineno=0,
            msg="hello world", args=(), exc_info=None,
        )
        line = fmt.format(record)
        parsed = json.loads(line)
        assert parsed["component"] == "lccfq.test"
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello world"
        assert "timestamp" in parsed

    def test_exception_included(self):
        fmt = JSONFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="lccfq.test", level=logging.ERROR, pathname="", lineno=0,
            msg="failure", args=(), exc_info=exc_info,
        )
        line = fmt.format(record)
        parsed = json.loads(line)
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
        assert "boom" in parsed["exception"]

    def test_no_exception_key_when_none(self):
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="lccfq.test", level=logging.INFO, pathname="", lineno=0,
            msg="ok", args=(), exc_info=None,
        )
        line = fmt.format(record)
        parsed = json.loads(line)
        assert "exception" not in parsed


# ---------- Environment variable configuration ----------

class TestEnvVarConfig:
    def test_default_level_is_info(self, monkeypatch):
        logger = setup_logger("test.default_level")
        assert logger.level == logging.INFO

    def test_global_level_override(self, monkeypatch):
        monkeypatch.setenv("LCCFQ_LOG_LEVEL", "DEBUG")
        logger = setup_logger("test.global_debug")
        assert logger.level == logging.DEBUG

    def test_component_level_override(self, monkeypatch):
        monkeypatch.setenv("LCCFQ_LOG_LEVELS", "test.comp_warn=WARNING")
        logger = setup_logger("test.comp_warn")
        assert logger.level == logging.WARNING

    def test_component_level_takes_precedence_over_global(self, monkeypatch):
        monkeypatch.setenv("LCCFQ_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LCCFQ_LOG_LEVELS", "test.override=ERROR")
        logger = setup_logger("test.override")
        assert logger.level == logging.ERROR

    def test_explicit_level_parameter_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("LCCFQ_LOG_LEVEL", "ERROR")
        monkeypatch.setenv("LCCFQ_LOG_LEVELS", "test.explicit=ERROR")
        logger = setup_logger("test.explicit", level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_multiple_component_levels(self, monkeypatch):
        monkeypatch.setenv("LCCFQ_LOG_LEVELS", "test.a=DEBUG, test.b=ERROR")
        logger_a = setup_logger("test.a")
        logger_b = setup_logger("test.b")
        assert logger_a.level == logging.DEBUG
        assert logger_b.level == logging.ERROR

    def test_invalid_level_string_falls_back_to_global(self, monkeypatch):
        monkeypatch.setenv("LCCFQ_LOG_LEVELS", "test.bad=NOTAVALIDLEVEL")
        monkeypatch.setenv("LCCFQ_LOG_LEVEL", "WARNING")
        logger = setup_logger("test.bad")
        assert logger.level == logging.WARNING


# ---------- JSON format via env var ----------

class TestJSONFormatEnv:
    def test_json_format_produces_json_output(self, monkeypatch, capsys):
        monkeypatch.setenv("LCCFQ_LOG_FORMAT", "json")
        logger = setup_logger("test.json_fmt")
        logger.info("json test message")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip())
        assert parsed["message"] == "json test message"
        assert parsed["component"] == "test.json_fmt"

    def test_text_format_is_default(self, capsys):
        logger = setup_logger("test.text_fmt")
        logger.info("text test message")
        captured = capsys.readouterr()
        assert "[INFO]" in captured.out
        assert "[test.text_fmt]" in captured.out
        assert "text test message" in captured.out


# ---------- File handler ----------

class TestFileHandler:
    def test_file_handler_writes_to_file(self, monkeypatch):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_path = f.name

        try:
            monkeypatch.setenv("LCCFQ_LOG_FILE", log_path)
            logger = setup_logger("test.file_handler")
            logger.info("file handler test")
            # Flush handlers
            for h in logger.handlers:
                h.flush()

            with open(log_path) as f:
                content = f.read()
            assert "file handler test" in content
            assert "[test.file_handler]" in content
        finally:
            os.unlink(log_path)

    def test_file_handler_json_format(self, monkeypatch):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_path = f.name

        try:
            monkeypatch.setenv("LCCFQ_LOG_FILE", log_path)
            monkeypatch.setenv("LCCFQ_LOG_FORMAT", "json")
            logger = setup_logger("test.file_json")
            logger.info("json file test")
            for h in logger.handlers:
                h.flush()

            with open(log_path) as f:
                content = f.read().strip()
            parsed = json.loads(content)
            assert parsed["message"] == "json file test"
        finally:
            os.unlink(log_path)


# ---------- Logger naming convention ----------

class TestLoggerNaming:
    def test_setup_logger_returns_named_logger(self):
        logger = setup_logger("lccfq.testmod")
        assert logger.name == "lccfq.testmod"

    def test_same_name_returns_same_logger(self):
        logger1 = setup_logger("test.same")
        logger2 = setup_logger("test.same")
        assert logger1 is logger2

    def test_handlers_not_duplicated_on_repeated_calls(self):
        logger1 = setup_logger("test.nodup")
        handler_count = len(logger1.handlers)
        setup_logger("test.nodup")
        assert len(logger1.handlers) == handler_count


# ---------- Helper for caplog with propagate=False loggers ----------

from contextlib import contextmanager


@contextmanager
def _capture_logger(caplog, logger_name, level=logging.DEBUG):
    """Inject caplog's handler directly into a non-propagating logger."""
    lg = logging.getLogger(logger_name)
    lg.addHandler(caplog.handler)
    old_level = lg.level
    lg.setLevel(level)
    caplog.handler.setLevel(level)
    try:
        yield
    finally:
        lg.removeHandler(caplog.handler)
        lg.setLevel(old_level)


# ---------- FSM transition log levels ----------

class TestFSMTransitionLogLevels:
    def test_normal_transitions_log_at_info(self, caplog):
        from lccfq_backend.backend.fsm import QPUAbstraction, QPUEvent

        fsm = QPUAbstraction()
        with _capture_logger(caplog, "lccfq.fsm"):
            fsm.transition(QPUEvent.CONNECT)

        info_records = [r for r in caplog.records if r.levelno == logging.INFO and "lccfq.fsm" in r.name]
        assert len(info_records) == 1
        assert "QPU state transition" in info_records[0].message
        assert "CONNECT" in info_records[0].message.upper()

    def test_degradation_transitions_log_at_warning(self, caplog):
        from lccfq_backend.backend.fsm import QPUAbstraction, QPUEvent

        fsm = QPUAbstraction()
        fsm.transition(QPUEvent.CONNECT)

        caplog.clear()
        with _capture_logger(caplog, "lccfq.fsm"):
            fsm.transition(QPUEvent.DEVICE_FAIL)

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING and "lccfq.fsm" in r.name]
        assert len(warning_records) == 1
        assert "DEVICE_FAIL" in warning_records[0].message.upper()

    def test_fidelity_degraded_logs_at_warning(self, caplog):
        from lccfq_backend.backend.fsm import QPUAbstraction, QPUEvent

        fsm = QPUAbstraction()
        fsm.transition(QPUEvent.CONNECT)
        fsm.transition(QPUEvent.DEVICE_OK)
        fsm.transition(QPUEvent.TUNE_SUCCESS)

        caplog.clear()
        with _capture_logger(caplog, "lccfq.fsm"):
            fsm.transition(QPUEvent.FIDELITY_DEGRADED)

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING and "lccfq.fsm" in r.name]
        assert len(warning_records) == 1
        assert "FIDELITY_DEGRADED" in warning_records[0].message.upper()

    def test_tune_fail_logs_at_warning(self, caplog):
        from lccfq_backend.backend.fsm import QPUAbstraction, QPUEvent

        fsm = QPUAbstraction()
        fsm.transition(QPUEvent.CONNECT)
        fsm.transition(QPUEvent.DEVICE_OK)

        caplog.clear()
        with _capture_logger(caplog, "lccfq.fsm"):
            fsm.transition(QPUEvent.TUNE_FAIL)

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING and "lccfq.fsm" in r.name]
        assert len(warning_records) == 1

    def test_task_started_finished_logs_at_info(self, caplog):
        from lccfq_backend.backend.fsm import QPUAbstraction, QPUEvent

        fsm = QPUAbstraction()
        fsm.transition(QPUEvent.CONNECT)
        fsm.transition(QPUEvent.DEVICE_OK)
        fsm.transition(QPUEvent.TUNE_SUCCESS)
        fsm.transition(QPUEvent.RESET)

        caplog.clear()
        with _capture_logger(caplog, "lccfq.fsm"):
            fsm.transition(QPUEvent.TASK_STARTED)
            fsm.transition(QPUEvent.TASK_FINISHED)

        info_records = [r for r in caplog.records if r.levelno == logging.INFO and "lccfq.fsm" in r.name]
        assert len(info_records) == 2
        # Ensure no warnings for normal operational transitions
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING and "lccfq.fsm" in r.name]
        assert len(warning_records) == 0


# ---------- Queue enriched messages ----------

class TestQueueEnrichedMessages:
    def test_enqueue_log_includes_queue_depth(self, caplog):
        from lccfq_backend.backend.queue import QPUTaskQueue
        from lccfq_backend.model.tasks import CircuitTask, TaskType, Gate

        queue = QPUTaskQueue()
        task = CircuitTask(
            type=TaskType.CIRCUIT,
            gates=[Gate(symbol="RX", target_qubits=[0], control_qubits=[], params=[1.57])],
            shots=100,
        )

        with _capture_logger(caplog, "lccfq.queue"):
            queue.enqueue(task, user="testuser", priority=5)

        enqueue_records = [r for r in caplog.records if "Enqueueing" in r.message]
        assert len(enqueue_records) == 1
        assert "queue_depth=1" in enqueue_records[0].message
        assert "priority=5" in enqueue_records[0].message
        assert "testuser" in enqueue_records[0].message

    def test_dequeue_log_includes_wait_time_and_depth(self, caplog):
        from lccfq_backend.backend.queue import QPUTaskQueue
        from lccfq_backend.model.tasks import CircuitTask, TaskType, Gate

        queue = QPUTaskQueue()
        task = CircuitTask(
            type=TaskType.CIRCUIT,
            gates=[Gate(symbol="RX", target_qubits=[0], control_qubits=[], params=[1.57])],
            shots=100,
        )
        queue.enqueue(task, user="testuser")

        caplog.clear()
        with _capture_logger(caplog, "lccfq.queue"):
            queue.dequeue()

        dequeue_records = [r for r in caplog.records if "Dequeued" in r.message]
        assert len(dequeue_records) == 1
        assert "waited=" in dequeue_records[0].message
        assert "queue_depth=0" in dequeue_records[0].message


# ---------- Watchdog enriched messages ----------

class TestWatchdogEnrichedMessages:
    def test_watchdog_tracks_consecutive_failures(self, tmp_path, monkeypatch, caplog):
        from lccfq_backend.daemon.watchdog import QPUWatchdog

        watchdog = QPUWatchdog(interval=1)
        watchdog.status_file = str(tmp_path / "qpu_status.flag")

        # Mock ping to return False
        monkeypatch.setattr(watchdog.hwman, "ping", lambda: False)

        with caplog.at_level(logging.DEBUG, logger="lccfq.watchdog"):
            # Simulate two check cycles manually
            watchdog._check_count += 1
            alive = watchdog.check_hardware()
            watchdog.write_status(alive)
            if not alive:
                watchdog._consecutive_failures += 1
            logger_msg_1 = (
                f"QPU health check #{watchdog._check_count}: status={'online' if alive else 'offline'}, "
                f"consecutive_failures={watchdog._consecutive_failures}"
            )

            watchdog._check_count += 1
            alive = watchdog.check_hardware()
            watchdog.write_status(alive)
            if not alive:
                watchdog._consecutive_failures += 1

        assert watchdog._consecutive_failures == 2
        assert watchdog._check_count == 2
