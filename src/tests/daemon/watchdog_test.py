import os
import tempfile
import time
import pytest
from unittest.mock import patch

from lccfq_backend.daemon.watchdog import QPUWatchdog


@pytest.mark.timeout(2)
def test_watchdog_check_and_write(monkeypatch):
    # Setup: simulate a QPU that is online
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        status_file = tmp.name

    try:
        # Patch the HWManClient.ping method to return True
        with patch("lccfq_backend.daemon.watchdog.HWManClient") as MockHWMan:
            instance = MockHWMan.return_value
            instance.ping.return_value = True

            watchdog = QPUWatchdog(interval=1)
            watchdog.status_file = status_file

            # Patch sleep and stop event to run the loop only once
            def fake_sleep(_): watchdog.stop_event.set()

            with patch("time.sleep", fake_sleep):
                watchdog.run()

            # Assert that the status was written correctly
            with open(status_file, "r") as f:
                content = f.read().strip()
                assert content == "online"

    finally:
        os.remove(status_file)