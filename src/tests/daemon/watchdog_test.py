import os
import tempfile
import time
import pytest
from unittest.mock import patch, MagicMock

from lccfq_backend.config import BackendSettings
from lccfq_backend.daemon.watchdog import QPUWatchdog

_config = BackendSettings(hwman_mock_mode=True)


@pytest.mark.timeout(2)
def test_watchdog_check_and_write(monkeypatch):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        status_file = tmp.name

    try:
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        with patch("lccfq_backend.daemon.watchdog.make_hwman_client", return_value=mock_client):
            watchdog = QPUWatchdog(config=_config, interval=1)
            watchdog.status_file = status_file

            def fake_sleep(_): watchdog.stop_event.set()

            with patch("time.sleep", fake_sleep):
                watchdog.run()

            with open(status_file, "r") as f:
                content = f.read().strip()
                assert content == "online"

    finally:
        os.remove(status_file)