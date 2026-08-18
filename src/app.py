import streamlit as st
from chatgpt_adapter import call_chatgpt
from policy_engine import build_system_prompt, decide_for_input, decide_for_output, make_rewrite_prompt

st.set_page_config(page_title="SafeChatGPT", page_icon="🛡️", layout="wide")

st.title("🛡️ SafeChatGPT")
st.caption("A protected ChatGPT web app for children when the official ChatGPT website is blocked by parents.")

with st.sidebar:
    st.header("Parent Controls")
    age_band = st.selectbox("Child age band", ["8-10", "11-13", "14-16"], index=1)
    show_logs = st.checkbox("Show safety decision log", value=True)
    st.info("In the project assumption, the official ChatGPT website is blocked for the child's account. This app is the only approved ChatGPT interface.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "logs" not in st.session_state:
    st.session_state.logs = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_message = st.chat_input("Ask SafeChatGPT...")

if user_message:
    with st.chat_message("user"):
        st.write(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})

    input_decision = decide_for_input(user_message, age_band)
    st.session_state.logs.append({"stage": "Input", **input_decision.__dict__})

    if input_decision.action in {"BLOCK", "ESCALATE"}:
        final_answer = input_decision.message
    else:
        system_prompt = build_system_prompt(age_band)
        model_messages = [{"role": "system", "content": system_prompt}]
        model_messages += st.session_state.messages[-6:]
        draft_answer = call_chatgpt(model_messages)

        output_decision = decide_for_output(draft_answer, age_band)
        st.session_state.logs.append({"stage": "Output", **output_decision.__dict__})

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

if show_logs:
    st.divider()
    st.subheader("Safety Decision Log")
    if st.session_state.logs:
        st.dataframe(st.session_state.logs, use_container_width=True)
    else:
        st.write("No safety decisions yet.")
