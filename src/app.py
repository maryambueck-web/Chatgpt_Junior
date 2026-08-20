import logging
import time
import uuid

import streamlit as st
from chatgpt_adapter import call_chatgpt
from image_service import fetch_image, is_image_request
from policy_engine import build_system_prompt, decide_for_input, decide_for_output, make_rewrite_prompt
from shared_store import append_log_entry, bridge_secrets_to_env, load_settings
from theme import hide_page_nav, inject_base_styles

logger = logging.getLogger(__name__)

# A picsum.photos fallback resolves in milliseconds with no real network
# search, which makes the "Juni is finding that for you" spinner flash by
# unnoticed. Padding every image lookup out to this floor keeps the loading
# moment visible and consistent, whether the result took 20ms or 2s.
IMAGE_MIN_LOADING_SECONDS = 1.5
IMAGE_ERROR_MESSAGE = "Juni couldn't find that picture. Try asking differently!"

# A public deployment can be hit by more traffic (or one over-eager child)
# than a single ChatGPT/Unsplash API budget should absorb. This is a
# per-browser-session cap, not a global one — it protects against runaway
# usage from one user, not coordinated abuse across many.
RATE_LIMIT_MAX_MESSAGES = 15
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MESSAGE = "You're sending messages quickly! Please wait a moment before asking again."

GENERIC_ERROR_MESSAGE = "Something went wrong on my end. Please try asking again."

st.set_page_config(page_title="SafeChatGPT", page_icon="🛡️", layout="wide")

bridge_secrets_to_env()
inject_base_styles()
hide_page_nav()

age_band = load_settings()["age_band"]

if "stars" not in st.session_state:
    st.session_state.stars = 0

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "message_timestamps" not in st.session_state:
    st.session_state.message_timestamps = []

hero_placeholder = st.empty()


def render_hero() -> None:
    hero_placeholder.markdown(
        f"""
        <div class="hero-card">
            <div class="brand-row">
                <div class="brand-left">
                    <div class="brand-badge">🛡️</div>
                    <div class="main-title">SafeChatGPT</div>
                </div>
                <div class="live-indicator"><span class="live-dot"></span>System active</div>
            </div>
            <div class="muted">
                A protected ChatGPT experience for children when the official website is blocked by parents.
            </div>
            <div class="status-row">
                <span class="status-pill success">✅ Safety filter active</span>
                <span class="status-pill">🧠 Age-aware moderation</span>
                <span class="status-pill">🔒 Parent-controlled access</span>
                <span class="status-pill" style="background:rgba(246,201,69,.12);border-color:rgba(246,201,69,.30);color:#ffe9ad;">⭐ Knowledge stars: {st.session_state.stars}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fetch_image_with_min_wait(query: str, session_id: str):
    start = time.monotonic()
    image_url = fetch_image(query, age_band, session_id=session_id)
    remaining = IMAGE_MIN_LOADING_SECONDS - (time.monotonic() - start)
    if remaining > 0:
        time.sleep(remaining)
    return image_url


def retry_image(idx: int) -> None:
    original_query = st.session_state.messages[idx]["original_query"]
    with st.spinner("🌱 Juni is finding that for you..."):
        image_url = fetch_image_with_min_wait(original_query, st.session_state.session_id)
    if image_url:
        st.session_state.messages[idx] = {
            "role": "assistant", "type": "image", "content": image_url, "caption": original_query,
        }
    else:
        st.session_state.messages[idx] = {
            "role": "assistant", "type": "image_error", "content": IMAGE_ERROR_MESSAGE,
            "original_query": original_query,
        }
    st.rerun()


def render_assistant_message(msg: dict, idx: int) -> None:
    with st.chat_message(msg["role"]):
        if msg.get("type") == "image":
            st.image(msg["content"], caption=msg.get("caption"))
        elif msg.get("type") == "image_error":
            st.warning(msg["content"])
            if st.button("🔄 Try again", key=f"retry_{idx}"):
                retry_image(idx)
        else:
            st.write(msg["content"])


render_hero()

st.markdown(
    """
    <div class="chat-header">
        <div class="chat-header-title">💬 Live session</div>
        <div class="live-indicator"><span class="live-dot"></span>Active</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.write("Hi! I'm Juni, your learning guardian. What would you like to discover today?")

for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        render_assistant_message(msg, idx)

user_message = st.chat_input("Ask SafeChatGPT...")

if user_message:
    with st.chat_message("user"):
        st.write(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})

    now = time.monotonic()
    st.session_state.message_timestamps = [
        t for t in st.session_state.message_timestamps if now - t < RATE_LIMIT_WINDOW_SECONDS
    ]

    if len(st.session_state.message_timestamps) >= RATE_LIMIT_MAX_MESSAGES:
        st.session_state.messages.append({"role": "assistant", "content": RATE_LIMIT_MESSAGE})
        render_assistant_message(st.session_state.messages[-1], len(st.session_state.messages) - 1)
    else:
        st.session_state.message_timestamps.append(now)
        try:
            # Computed once up front — both the image branch and the text branch below
            # need the same ALLOW/REWRITE/BLOCK/ESCALATE decision for this message.
            input_decision = decide_for_input(user_message, age_band)

            if is_image_request(user_message):
                if input_decision.action in {"BLOCK", "ESCALATE"}:
                    append_log_entry({
                        "stage": "Image",
                        "context": user_message,
                        "session_id": st.session_state.session_id,
                        "search_term": None,
                        "image_url": None,
                        "image_source": "blocked",
                        **input_decision.__dict__,
                    })
                    st.session_state.messages.append({"role": "assistant", "content": input_decision.message})
                else:
                    # fetch_image re-runs the same safety check internally (cheap, no
                    # I/O) and is the single place that logs the "Image" stage entry —
                    # for REWRITE it searches a swapped-in safe topic without ever
                    # telling the child their request was changed.
                    with st.spinner("🌱 Juni is finding that for you..."):
                        image_url = fetch_image_with_min_wait(user_message, st.session_state.session_id)
                    if image_url:
                        st.session_state.messages.append({
                            "role": "assistant", "type": "image", "content": image_url, "caption": user_message,
                        })
                    else:
                        # A key IS configured but the search failed or found nothing —
                        # rather than silently swapping in an unrelated photo, offer a
                        # retry so the child can see something actually went wrong.
                        st.session_state.messages.append({
                            "role": "assistant", "type": "image_error", "content": IMAGE_ERROR_MESSAGE,
                            "original_query": user_message,
                        })

                render_assistant_message(st.session_state.messages[-1], len(st.session_state.messages) - 1)
            else:
                append_log_entry({"stage": "Input", "context": user_message, **input_decision.__dict__})

                if input_decision.action in {"BLOCK", "ESCALATE"}:
                    final_answer = input_decision.message
                else:
                    system_prompt = build_system_prompt(age_band)
                    model_messages = [{"role": "system", "content": system_prompt}]
                    model_messages += st.session_state.messages[-6:]
                    draft_answer = call_chatgpt(model_messages)

                    output_decision = decide_for_output(draft_answer, age_band)
                    append_log_entry({"stage": "Output", "context": draft_answer, **output_decision.__dict__})

                    if output_decision.action == "BLOCK":
                        final_answer = output_decision.message
                    elif input_decision.action == "REWRITE" or output_decision.action == "REWRITE":
                        rewrite_prompt = make_rewrite_prompt(age_band, user_message, draft_answer)
                        final_answer = call_chatgpt([
                            {"role": "system", "content": build_system_prompt(age_band)},
                            {"role": "user", "content": rewrite_prompt},
                        ])
                    else:
                        final_answer = draft_answer
                        st.session_state.stars += 1
                        render_hero()

                with st.chat_message("assistant"):
                    st.write(final_answer)
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
        except Exception:
            # A real user must never see a raw Streamlit traceback — log it
            # for the operator and show a friendly message instead.
            logger.exception("Unhandled error while processing a chat message")
            st.session_state.messages.append({"role": "assistant", "content": GENERIC_ERROR_MESSAGE})
            render_assistant_message(st.session_state.messages[-1], len(st.session_state.messages) - 1)

st.markdown("</div>", unsafe_allow_html=True)
