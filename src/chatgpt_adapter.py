import logging
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 20.0
# The OpenAI SDK defaults to 2 automatic retries, so a per-attempt timeout of
# 20s alone doesn't cap latency at 20s — a slow/erroring endpoint can take up
# to (retries + 1) * timeout before call_chatgpt returns. Capping retries at 1
# bounds the real worst case at ~40s instead of a silent ~60s.
MAX_RETRIES = 1


def _mock_chatgpt(messages: List[Dict[str, str]]) -> str:
    user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    low = user.lower()
    if "photosynthesis" in low:
        return "Photosynthesis is how plants use sunlight, water, and carbon dioxide to make their own food. They also release oxygen, which helps animals and people breathe."
    if "drugs" in low:
        return "Drugs are chemicals that change how the body or brain works. Some medicines are used safely with doctors, but illegal or misused drugs can be dangerous. It is best to ask a teacher, parent, or doctor for trusted information."
    return "This is a safe demo response from ChatGPT mock mode. The API is unavailable right now, so the app is using a safe fallback answer."


def _safe_error_message() -> str:
    return "The AI service is temporarily unavailable. I can still help with safe, general learning questions while the connection is restored."


def _env(*names: str, default: str = "") -> str:
    # This app only ever talks to OpenAI-compatible endpoints, so someone
    # actually using DeepSeek reasonably reaches for DEEPSEEK_* names instead
    # of OPENAI_* ones in their .env — that's not a mistake, the code should
    # just accept it. OPENAI_* wins if both happen to be set. Also strips
    # whitespace: a value pasted into a platform's secrets UI with a trailing
    # newline is indistinguishable from "wrong credential" once it reaches
    # the API, and only shows up after deploying, not in local testing.
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return default


def get_chatgpt_status() -> dict:
    """Diagnostic info for the Guardian Command Center — never exposes the full key."""
    api_key = _env("OPENAI_API_KEY", "DEEPSEEK_API_KEY")
    model = _env("OPENAI_MODEL", "DEEPSEEK_MODEL", default="gpt-4o-mini")
    if not api_key or api_key == "your_key_here":
        return {"configured": False, "model": None}
    return {"configured": True, "model": model}


def call_chatgpt(messages: List[Dict[str, str]]) -> str:
    api_key = _env("OPENAI_API_KEY", "DEEPSEEK_API_KEY")
    model = _env("OPENAI_MODEL", "DEEPSEEK_MODEL", default="gpt-4o-mini")
    base_url = _env("OPENAI_BASE_URL", "DEEPSEEK_BASE_URL") or None

    if not api_key or api_key == "your_key_here":
        return _mock_chatgpt(messages)

    try:
        from openai import OpenAI

        client_kwargs = {"api_key": api_key, "timeout": REQUEST_TIMEOUT_SECONDS, "max_retries": MAX_RETRIES}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
        )
        return response.choices[0].message.content or _safe_error_message()
    except Exception:
        logger.exception("ChatGPT API call failed; falling back to safe error message")
        return _safe_error_message()
