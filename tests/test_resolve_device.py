import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backend_client import BackendClient  # noqa: E402


def _client_with(devices):
    c = BackendClient("127.0.0.1", 12321)
    c.list_devices = lambda: devices  # 네트워크 대신 고정 목록
    return c


HINTS = ["SUPERSTRIKE", "SUPERLIGHT", "PRO X"]


def test_matches_superstrike():
    c = _client_with([("id-ss", "PRO X2 SUPERSTRIKE")])
    assert c.resolve_device_id(HINTS) == "id-ss"


def test_matches_superlight():
    c = _client_with([("id-kb", "MX Keys S"), ("id-sl", "G PRO X SUPERLIGHT")])
    assert c.resolve_device_id(HINTS) == "id-sl"


def test_matches_superlight_2():
    c = _client_with([("id-sl2", "G PRO X SUPERLIGHT 2")])
    assert c.resolve_device_id(HINTS) == "id-sl2"


def test_prefers_matching_over_first():
    devices = [("id-other", "M330 Silent"), ("id-sl2", "PRO X SUPERLIGHT 2")]
    c = _client_with(devices)
    assert c.resolve_device_id(HINTS) == "id-sl2"


def test_single_string_hint_still_works():
    c = _client_with([("id-ss", "PRO X2 SUPERSTRIKE")])
    assert c.resolve_device_id("superstrike") == "id-ss"


def test_falls_back_to_first_when_no_match():
    c = _client_with([("id-x", "Some Other Device")])
    assert c.resolve_device_id(HINTS) == "id-x"
