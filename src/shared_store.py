import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

DATA_DIR = Path(__file__).with_name("data")

# Pre-SQLite storage format, kept only so a one-time migration can import any
# existing demo history the first time this runs against a fresh database.
LEGACY_SETTINGS_PATH = DATA_DIR / "settings.json"
LEGACY_LOG_PATH = DATA_DIR / "safety_log.json"

DEFAULT_SETTINGS = {"age_band": "11-13"}

MAX_PIN_ATTEMPTS = 5
PIN_LOCKOUT_MINUTES = 5

# Streamlit Community Cloud stores secrets in st.secrets, not in the process
# environment, so bridge them into os.environ for the local-dev-style os.getenv()
# calls elsewhere in the app to pick up.
ENV_BRIDGE_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    # chatgpt_adapter.py accepts either naming — someone actually using
    # DeepSeek reasonably sets DEEPSEEK_* instead of OPENAI_* in secrets.
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_BASE_URL",
    "PARENT_PIN",
    "UNSPLASH_ACCESS_KEY",
    "JUNI_PLACEHOLDER_IMAGE_URL",
)

# A raw JSON file rewritten on every write has two problems once more than one
# person can hit the app at once: concurrent writes can silently clobber each
# other (last writer wins), and it doesn't play well with being placed on a
# mounted persistent volume. SQLite (stdlib, zero extra dependency) gives each
# write its own atomic transaction and survives on the same kind of volume.
# SAFECHATGPT_DB_PATH lets a production deployment point this at a mounted
# disk (e.g. /data/safechatgpt.db) so it survives restarts/redeploys.
_init_lock = threading.Lock()
_schema_ready_paths = set()


def _db_path() -> Path:
    override = os.getenv("SAFECHATGPT_DB_PATH")
    return Path(override) if override else DATA_DIR / "safechatgpt.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS safety_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, data TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS pin_attempts ("
        "id INTEGER PRIMARY KEY CHECK (id = 1), failed_count INTEGER NOT NULL DEFAULT 0, locked_until TEXT)"
    )
    conn.commit()


def _migrate_legacy_json(conn: sqlite3.Connection) -> None:
    if LEGACY_LOG_PATH.exists() and conn.execute("SELECT COUNT(*) FROM safety_log").fetchone()[0] == 0:
        try:
            for entry in json.loads(LEGACY_LOG_PATH.read_text()):
                timestamp = entry.get("timestamp", datetime.now().isoformat(timespec="seconds"))
                conn.execute("INSERT INTO safety_log (timestamp, data) VALUES (?, ?)", (timestamp, json.dumps(entry)))
            conn.commit()
        except (json.JSONDecodeError, OSError):
            pass

    if LEGACY_SETTINGS_PATH.exists() and conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
        try:
            for key, value in json.loads(LEGACY_SETTINGS_PATH.read_text()).items():
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))
            conn.commit()
        except (json.JSONDecodeError, OSError):
            pass


def _get_conn() -> sqlite3.Connection:
    path_key = str(_db_path())
    conn = _connect()
    if path_key not in _schema_ready_paths:
        with _init_lock:
            _init_schema(conn)
            _migrate_legacy_json(conn)
            _schema_ready_paths.add(path_key)
    return conn


def bridge_secrets_to_env() -> None:
    try:
        for key in ENV_BRIDGE_KEYS:
            if key in st.secrets and not os.getenv(key):
                # .strip() guards against a value pasted into Streamlit Cloud's
                # secrets editor with a trailing newline/space — indistinguishable
                # from a wrong key once it reaches an external API.
                os.environ[key] = str(st.secrets[key]).strip()
    except Exception:
        pass


def load_settings() -> Dict:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    finally:
        conn.close()
    return {**DEFAULT_SETTINGS, **{key: json.loads(value) for key, value in rows}}


def save_settings(settings: Dict) -> None:
    conn = _get_conn()
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            [(key, json.dumps(value)) for key, value in settings.items()],
        )
        conn.commit()
    finally:
        conn.close()


def load_log() -> List[Dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT data FROM safety_log ORDER BY id ASC").fetchall()
    finally:
        conn.close()
    return [json.loads(row[0]) for row in rows]


def append_log_entry(entry: Dict) -> None:
    conn = _get_conn()
    try:
        timestamp = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO safety_log (timestamp, data) VALUES (?, ?)",
            (timestamp, json.dumps({**entry, "timestamp": timestamp})),
        )
        conn.commit()
    finally:
        conn.close()


def clear_log() -> None:
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM safety_log")
        conn.commit()
    finally:
        conn.close()


# A 4-digit PIN has only 10,000 combinations, so the Guardian Command Center
# needs a real lockout rather than relying on the PIN alone. This is tracked
# in the database (not st.session_state) so a new browser tab/session can't
# be used to reset the attempt counter.
def record_failed_pin_attempt() -> None:
    conn = _get_conn()
    try:
        conn.execute("INSERT OR IGNORE INTO pin_attempts (id, failed_count) VALUES (1, 0)")
        failed_count = conn.execute("SELECT failed_count FROM pin_attempts WHERE id = 1").fetchone()[0] + 1
        locked_until = None
        if failed_count >= MAX_PIN_ATTEMPTS:
            locked_until = (datetime.now() + timedelta(minutes=PIN_LOCKOUT_MINUTES)).isoformat(timespec="seconds")
        conn.execute(
            "UPDATE pin_attempts SET failed_count = ?, locked_until = ? WHERE id = 1",
            (failed_count, locked_until),
        )
        conn.commit()
    finally:
        conn.close()


def reset_pin_attempts() -> None:
    conn = _get_conn()
    try:
        conn.execute("INSERT OR REPLACE INTO pin_attempts (id, failed_count, locked_until) VALUES (1, 0, NULL)")
        conn.commit()
    finally:
        conn.close()


def get_pin_lockout() -> Optional[datetime]:
    """Returns the datetime the PIN entry is locked until, or None if not locked."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT locked_until FROM pin_attempts WHERE id = 1").fetchone()
    finally:
        conn.close()
    if not row or not row[0]:
        return None
    locked_until = datetime.fromisoformat(row[0])
    return locked_until if datetime.now() < locked_until else None
