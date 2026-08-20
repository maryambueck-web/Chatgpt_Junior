import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import pytest

import shared_store as ss


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SAFECHATGPT_DB_PATH", str(tmp_path / "test.db"))
    # Isolate from any real demo data on disk so migration doesn't pull it in.
    monkeypatch.setattr(ss, "LEGACY_LOG_PATH", tmp_path / "no_such_log.json")
    monkeypatch.setattr(ss, "LEGACY_SETTINGS_PATH", tmp_path / "no_such_settings.json")
    yield


def test_settings_round_trip():
    assert ss.load_settings() == {"age_band": "11-13"}
    ss.save_settings({"age_band": "8-10"})
    assert ss.load_settings() == {"age_band": "8-10"}


def test_log_entries_append_in_order_with_timestamp():
    ss.append_log_entry({"stage": "Input", "action": "ALLOW"})
    ss.append_log_entry({"stage": "Output", "action": "ALLOW"})
    log = ss.load_log()
    assert [e["stage"] for e in log] == ["Input", "Output"]
    assert all("timestamp" in e for e in log)


def test_clear_log_empties_it():
    ss.append_log_entry({"stage": "Input", "action": "ALLOW"})
    ss.clear_log()
    assert ss.load_log() == []


def test_pin_lockout_after_max_attempts():
    assert ss.get_pin_lockout() is None
    for _ in range(ss.MAX_PIN_ATTEMPTS - 1):
        ss.record_failed_pin_attempt()
    assert ss.get_pin_lockout() is None  # not locked yet

    ss.record_failed_pin_attempt()
    assert ss.get_pin_lockout() is not None  # locked on the Nth attempt


def test_reset_pin_attempts_clears_lockout():
    for _ in range(ss.MAX_PIN_ATTEMPTS):
        ss.record_failed_pin_attempt()
    assert ss.get_pin_lockout() is not None

    ss.reset_pin_attempts()
    assert ss.get_pin_lockout() is None
