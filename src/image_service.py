import logging
import os
import re
import time
from typing import Optional, Tuple
from urllib.parse import quote_plus

import requests

from policy_engine import decide_for_input
from shared_store import append_log_entry

logger = logging.getLogger(__name__)

UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"
REQUEST_TIMEOUT_SECONDS = 6

# Total attempts for a single fetch_image() call, including the first try.
# Retries only help for transient failures (timeout, connection reset, 429
# rate limit, 5xx) — a bad/missing key or zero results won't change on retry,
# so those return immediately instead of wasting the attempt budget.
UNSPLASH_MAX_ATTEMPTS = 3
UNSPLASH_RETRY_BACKOFF_SECONDS = 0.6
_NON_RETRYABLE_STATUS_CODES = {401, 403}


def _clean_env(name: str) -> str:
    # A key copy-pasted into a platform's secrets UI with a trailing newline
    # or space is indistinguishable from "wrong key" once it hits Unsplash's
    # API — this is a common, silent cause of "it works locally, not deployed".
    return (os.getenv(name) or "").strip()

# A child asking to *see* something phrases it very differently from a child
# asking a question, so this is matched separately from classifier.py's
# safety categories.
#
# Two families of pattern here: the first block requires an explicit visual
# noun (picture/photo/image/...) and is unambiguous. The second block covers
# how children actually talk — "show me a flower", "I want to see a cat" —
# with no visual noun at all. That second block is restricted to the
# INDEFINITE article (a/an) only, not "the"/"some": "show me A flower" reads
# as a new, generic object (wants to see something), while "show me THE
# steps/answer/way" refers back to something abstract already in the
# conversation — allowing "the" here turned "show me the steps to solve
# this" into a false-positive image request instead of a homework question.
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
    r"what\s+does\s+.+\s+look\s+like|"
    r"show\s+me\s+(?:a|an)\s+\w+|"
    r"(?:can|could|will)\s+you\s+show\s+me\s+(?:a|an)\s+\w+|"
    r"(?:can|could|would)\s+i\s+see\s+(?:a|an)\s+\w+|"
    r"i\s+(?:want|would like)\s+to\s+see\s+(?:a|an)\s+\w+"
    r")\b",
    re.IGNORECASE,
)

# Strips the request phrasing so "show me a picture of a dinosaur" becomes a
# clean search term ("dinosaur") instead of polluting the image search query.
_LEAD_IN_RE = re.compile(
    r"^(show me|picture[s]? of|photo[s]? of|image[s]? of|draw (me|a|an)|"
    r"(send|find) me a picture of|can (i|you) see a picture of|"
    r"(can|could|would) i see|i (want|would like) to see)\s+(a|an|the)?\s*",
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


def get_unsplash_status() -> dict:
    """Diagnostic info for the Guardian Command Center — never exposes the full key.
    Surfacing this is the fix for "it's silently using the fallback and nobody
    noticed": a missing/blank key produces no error, just unrelated photos.
    """
    access_key = _clean_env("UNSPLASH_ACCESS_KEY")
    if not access_key:
        return {"configured": False, "preview": None}
    preview = f"{access_key[:4]}…{access_key[-4:]}" if len(access_key) > 10 else "***"
    return {"configured": True, "preview": preview}


def _search_image(search_term: str) -> Tuple[Optional[str], str]:
    """Returns (image_url, source). source is one of:
    - "picsum": no UNSPLASH_ACCESS_KEY configured — this is the expected demo
      fallback, not an error, so it fails silently to a real (if unrelated) photo.
    - "picsum_rate_limited": a key IS configured but Unsplash's free Demo tier
      (50 requests/hour) is exhausted. This falls back to picsum too, rather
      than erroring — a quota reset next hour isn't something the child or
      even the parent can act on, so showing *some* photo beats a repeated
      "couldn't find that picture" error during a live demo or busy session.
    - "unsplash": a real, content-matched result came back.
    - "error": a key IS configured but every attempt failed for a reason that
      IS worth surfacing (bad key, network error) or returned zero results.
      This does not fall back to picsum — swapping in an unrelated stock
      photo would hide a real, fixable problem. The caller shows a friendly
      retry message instead.
    """
    access_key = _clean_env("UNSPLASH_ACCESS_KEY")
    if not access_key:
        logger.info("UNSPLASH_ACCESS_KEY not set — using picsum.photos fallback for %r", search_term)
        return _picsum_fallback(search_term), "picsum"

    for attempt in range(1, UNSPLASH_MAX_ATTEMPTS + 1):
        try:
            url = _unsplash_search(search_term, access_key)
            if url:
                return url, "unsplash"
            # Zero results for THIS term won't change by retrying the same
            # request — a differently worded query might, but that's a new
            # fetch_image() call, not a reason to burn the retry budget here.
            logger.info("Unsplash returned zero results for %r", search_term)
            return None, "error"
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 429:
                # An hourly quota won't reset within a few retries, so don't
                # waste the attempt budget on it — degrade immediately.
                logger.warning(
                    "Unsplash rate limit hit (HTTP 429) for %r — the free Demo tier allows "
                    "50 requests/hour. Falling back to picsum.photos for this request; this "
                    "resets automatically within the hour.",
                    search_term,
                )
                return _picsum_fallback(search_term), "picsum_rate_limited"
            if status in _NON_RETRYABLE_STATUS_CODES:
                logger.error(
                    "Unsplash rejected the request with HTTP %s for %r — this usually means "
                    "UNSPLASH_ACCESS_KEY is missing, wrong, or has stray whitespace on this "
                    "deployment (check it was actually saved in the platform's secrets, not just "
                    "declared). Not retrying.",
                    status, search_term,
                )
                return None, "error"
            logger.warning(
                "Unsplash HTTP %s on attempt %d/%d for %r",
                status, attempt, UNSPLASH_MAX_ATTEMPTS, search_term,
            )
        except requests.exceptions.RequestException as exc:
            logger.warning(
                "Unsplash request error (%s) on attempt %d/%d for %r",
                type(exc).__name__, attempt, UNSPLASH_MAX_ATTEMPTS, search_term,
            )

        if attempt < UNSPLASH_MAX_ATTEMPTS:
            time.sleep(UNSPLASH_RETRY_BACKOFF_SECONDS * attempt)

    logger.error("Unsplash search failed after %d attempts for %r", UNSPLASH_MAX_ATTEMPTS, search_term)
    return None, "error"


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
