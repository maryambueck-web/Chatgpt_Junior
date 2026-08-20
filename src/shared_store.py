import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import streamlit as st

DATA_DIR = Path(__file__).with_name("data")
SETTINGS_PATH = DATA_DIR / "settings.json"
LOG_PATH = DATA_DIR / "safety_log.json"

DEFAULT_SETTINGS = {"age_band": "11-13"}

# Streamlit Community Cloud stores secrets in st.secrets, not in the process
# environment, so bridge them into os.environ for the local-dev-style os.getenv()
# calls elsewhere in the app to pick up.
ENV_BRIDGE_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    "PARENT_PIN",
    "UNSPLASH_ACCESS_KEY",
    "JUNI_PLACEHOLDER_IMAGE_URL",
)


def bridge_secrets_to_env() -> None:
    try:
        for key in ENV_BRIDGE_KEYS:
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = st.secrets[key]
    except Exception:
        pass


def load_settings() -> Dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULT_SETTINGS)
    return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_PATH.read_text())}


def save_settings(settings: Dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings))


def load_log() -> List[Dict]:
    if not LOG_PATH.exists():
        return []
    return json.loads(LOG_PATH.read_text())


def append_log_entry(entry: Dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    log = load_log()
    log.append({**entry, "timestamp": datetime.now().isoformat(timespec="seconds")})
    LOG_PATH.write_text(json.dumps(log))


def clear_log() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    LOG_PATH.write_text(json.dumps([]))
