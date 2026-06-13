import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backend_client import BackendClient, BackendError, BatteryStatus  # noqa: E402


def _client_with(devices, statuses):
    """devices: [(id, name)], statuses: {id: BatteryStatus or BackendError}."""
    c = BackendClient("127.0.0.1", 12321)
    c.list_devices = lambda: devices

    def _get_status(dev_id):
        val = statuses[dev_id]
        if isinstance(val, BackendError):
            raise val
        return val

    c.get_status = _get_status
    return c


def test_returns_all_detected_devices():
    devices = [("id-mouse", "PRO X2"), ("id-kb", "MX Keys")]
    statuses = {
        "id-mouse": BatteryStatus("id-mouse", "PRO X2", 80.0, True),
        "id-kb": BatteryStatus("id-kb", "MX Keys", 55.0, True),
    }
    c = _client_with(devices, statuses)
    result = c.get_all_statuses()
    assert [s.device_id for s in result] == ["id-mouse", "id-kb"]


def test_includes_non_logitech_and_keyboards():
    devices = [("id-other", "Some Brand Mouse")]
    statuses = {"id-other": BatteryStatus("id-other", "Some Brand Mouse", 42.0, True)}
    c = _client_with(devices, statuses)
    result = c.get_all_statuses()
    assert len(result) == 1
    assert result[0].name == "Some Brand Mouse"


def test_skips_devices_that_fail():
    devices = [("id-ok", "PRO X2"), ("id-bad", "Broken")]
    statuses = {
        "id-ok": BatteryStatus("id-ok", "PRO X2", 80.0, True),
        "id-bad": BackendError("no battery field"),
    }
    c = _client_with(devices, statuses)
    result = c.get_all_statuses()
    assert [s.device_id for s in result] == ["id-ok"]


def test_empty_when_no_devices():
    c = _client_with([], {})
    assert c.get_all_statuses() == []
