import logging
import os
import re
from typing import Optional, Tuple
from urllib.parse import quote_plus

import requests

from policy_engine import decide_for_input
from shared_store import append_log_entry

logger = logging.getLogger(__name__)

UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"
REQUEST_TIMEOUT_SECONDS = 6

# A child asking to *see* something phrases it very differently from a child
# asking a question, so this is matched separately from classifier.py's
# safety categories.
_IMAGE_REQUEST_RE = re.compile(
    r"\b(?:"
    r"(?:show|find|send|give)(?:\s+me)?\s+(?:a|an|the|some)?\s*"
    r"(?:picture|photo|image|illustration|drawing)s?(?:\s+of|\s+for)?|"
    r"(?:can|could|will)\s+you\s+(?:show|find|send|give)(?:\s+me)?\s+"
    r"(?:a|an|the|some)?\s*(?:picture|photo|image|illustration|drawing)s?(?:\s+of|\s+for)?|"
    r"(?:i\s+(?:want|would like)\s+(?:to see\s+)?)"
    r"(?:a|an|the|some)?\s*(?:picture|photo|image|illustration|drawing)s?(?:\s+of|\s+for)?|"
    r"(?:picture|photo|image|illustration|drawing)s?\s+of|"
    r"(?:generate|create|make|draw)\s+(?:me\s+)?(?:a|an|the)?\s*"
    r"(?:picture|photo|image|illustration|drawing)|"
    r"what\s+does\s+.+\s+look\s+like"
    r")\b",
    re.IGNORECASE,
)

# Strips the request phrasing so "show me a picture of a dinosaur" becomes a
# clean search term ("dinosaur") instead of polluting the image search query.
_LEAD_IN_RE = re.compile(
    r"^(show me|picture[s]? of|photo[s]? of|image[s]? of|draw (me|a|an)|"
    r"(send|find) me a picture of|can (i|you) see a picture of)\s+(a|an|the)?\s*",
    re.IGNORECASE,
)

# Age-band styling biases the search query rather than filtering results after
# the fact — Unsplash has no reliable "cartoon vs photo" content-type filter,
# but it does return different results for a differently worded query.
AGE_BAND_QUERY_STYLE = {
    "8-10": "cartoon illustration for kids",
    "11-13": "family friendly photo",
    "14-16": "photo",
}

# When the input classifier says REWRITE, the original wording is never sent
# to an external search API, even in modified form — it's swapped for a fixed
# safe topic instead. This keeps the fallback deterministic and guarantees no
# sensitive term ever leaves the app.
REWRITE_SEARCH_TOPICS = {
    "drugs": "medicine safety education",
    "eating_disorder": "healthy food",
    "gambling": "board game",
    "violence": "friendly cartoon adventure",
    "sexual": "friendly cartoon character",
}
DEFAULT_REWRITE_TOPIC = "safe learning illustration"

PLACEHOLDER_IMAGE_URL_ENV = "JUNI_PLACEHOLDER_IMAGE_URL"
DEFAULT_PLACEHOLDER_IMAGE_URL = "https://api.dicebear.com/7.x/bottts/svg?seed=juni-guardian&backgroundColor=b6e3f4"


def is_image_request(text: str) -> bool:
    return bool(_IMAGE_REQUEST_RE.search(text.lower()))


def get_safe_placeholder() -> str:
    return os.getenv(PLACEHOLDER_IMAGE_URL_ENV, DEFAULT_PLACEHOLDER_IMAGE_URL)


def _clean_query(text: str) -> str:
    # Phrasing can stack lead-ins ("show me" + "a picture of"), so strip
    # repeatedly until nothing more matches at the start.
    cleaned = text.strip()
    for _ in range(3):
        next_cleaned = _LEAD_IN_RE.sub("", cleaned, count=1).strip(" ?.!")
        if next_cleaned == cleaned:
            break
        cleaned = next_cleaned
    return cleaned or text.strip()


def _style_query(subject: str, age_band: str) -> str:
    style = AGE_BAND_QUERY_STYLE.get(age_band, "photo")
    return f"{subject} {style}".strip()


def _picsum_fallback(search_term: str) -> str:
    seed = quote_plus(search_term.lower().strip()) or "safechatgpt"
    return f"https://picsum.photos/seed/{seed}/600/400"


def _unsplash_search(search_term: str, access_key: str) -> Optional[str]:
    response = requests.get(
        UNSPLASH_SEARCH_URL,
        params={
            "query": search_term,
            "per_page": 1,
            "content_filter": "high",
            "orientation": "squarish",
            "client_id": access_key,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    return results[0]["urls"]["small"] if results else None


def _search_image(search_term: str) -> Tuple[Optional[str], str]:
    """Returns (image_url, source). source is one of:
    - "picsum": no UNSPLASH_ACCESS_KEY configured — this is the expected demo
      fallback, not an error, so it fails silently to a real (if unrelated) photo.
    - "unsplash": a real, content-matched result came back.
    - "error": a key IS configured but the request failed (network error,
      rate limit, bad key) or returned zero results. This does NOT fall back
      to picsum — swapping in an unrelated stock photo would hide a real
      problem from the child. The caller shows a friendly retry message instead.
    """
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        return _picsum_fallback(search_term), "picsum"

    try:
        url = _unsplash_search(search_term, access_key)
    except requests.exceptions.RequestException:
        logger.exception("Unsplash image search failed for %r", search_term)
        return None, "error"

    if not url:
        logger.info("Unsplash returned no results for %r", search_term)
        return None, "error"

    return url, "unsplash"


def fetch_image(query: str, age_band: str, session_id: Optional[str] = None) -> Optional[str]:
    # decide_for_input wraps classifier.classify() with the same ALLOW / REWRITE /
    # BLOCK / ESCALATE decision used for chat text, so an image request gets
    # exactly the same safety bar as a normal message.
    decision = decide_for_input(query, age_band)

    search_term = None
    if decision.action in {"BLOCK", "ESCALATE"}:
        image_url = get_safe_placeholder()
        source = "placeholder"
    elif decision.action == "REWRITE":
        topic = REWRITE_SEARCH_TOPICS.get(decision.category, DEFAULT_REWRITE_TOPIC)
        search_term = _style_query(topic, age_band)
        image_url, source = _search_image(search_term)
    else:
        search_term = _style_query(_clean_query(query), age_band)
        image_url, source = _search_image(search_term)

    append_log_entry({
        "stage": "Image",
        "context": query,
        "session_id": session_id,
        "search_term": search_term,
        "image_url": image_url,
        "image_source": source,
        **decision.__dict__,
    })
    return image_url
