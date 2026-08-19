import streamlit as st
from chatgpt_adapter import call_chatgpt
from policy_engine import build_system_prompt, decide_for_input, decide_for_output, make_rewrite_prompt
from shared_store import append_log_entry, bridge_secrets_to_env, load_settings
from theme import hide_page_nav, inject_base_styles

st.set_page_config(page_title="SafeChatGPT", page_icon="🛡️", layout="wide")

bridge_secrets_to_env()
inject_base_styles()
hide_page_nav()

age_band = load_settings()["age_band"]

st.markdown(
    """
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
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_message = st.chat_input("Ask SafeChatGPT...")

if user_message:
    with st.chat_message("user"):
        st.write(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})

    input_decision = decide_for_input(user_message, age_band)
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

    with st.chat_message("assistant"):
        st.write(final_answer)
    st.session_state.messages.append({"role": "assistant", "content": final_answer})

st.markdown("</div>", unsafe_allow_html=True)
