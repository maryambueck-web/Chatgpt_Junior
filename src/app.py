import html
import os

import streamlit as st
from chatgpt_adapter import call_chatgpt
from policy_engine import build_system_prompt, decide_for_input, decide_for_output, make_rewrite_prompt

st.set_page_config(page_title="SafeChatGPT", page_icon="🛡️", layout="wide")

# Streamlit Community Cloud stores secrets in st.secrets, not in the process
# environment, so bridge them into os.environ for the local-dev-style os.getenv()
# calls in chatgpt_adapter.py to pick up.
try:
    for _key in ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"):
        if _key in st.secrets and not os.getenv(_key):
            os.environ[_key] = st.secrets[_key]
except Exception:
    pass

STATUS_STYLES = {
    "ALLOW": {"color": "#0ca30c", "bg": "rgba(12, 163, 12, 0.14)", "icon": "✅"},
    "REWRITE": {"color": "#fab219", "bg": "rgba(250, 178, 25, 0.14)", "icon": "✏️"},
    "BLOCK": {"color": "#ec835a", "bg": "rgba(236, 131, 90, 0.16)", "icon": "⛔"},
    "ESCALATE": {"color": "#d03b3b", "bg": "rgba(208, 59, 59, 0.18)", "icon": "🚨"},
}

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            --bg: #0b1220;
            --panel: #121b2b;
            --panel-soft: #1a2438;
            --panel-strong: #202d46;
            --line: rgba(148, 163, 184, 0.20);
            --text: #edf6ff;
            --muted: #a8b6d3;
            --accent: #67d5ff;
            --accent-2: #6ee7b7;
            --warning: #f59e0b;
            --danger: #f87171;
            --success: #34d399;
            --mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace;
            --sans: 'Space Grotesk', system-ui, -apple-system, sans-serif;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 10% 15%, rgba(103, 213, 255, 0.16), transparent 42%),
                radial-gradient(circle at 90% 12%, rgba(139, 92, 246, 0.16), transparent 40%),
                radial-gradient(circle at 50% 100%, rgba(110, 231, 183, 0.08), transparent 45%),
                url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cg fill='none' stroke='rgba(103,213,255,0.16)' stroke-width='1'%3E%3Cpath d='M20 20 L80 45 L140 25 M80 45 L70 110 M70 110 L20 140 M70 110 L130 130 M20 20 L15 90'/%3E%3C/g%3E%3Cg fill='rgba(110,231,183,0.28)'%3E%3Ccircle cx='20' cy='20' r='2.2'/%3E%3Ccircle cx='80' cy='45' r='2.2'/%3E%3Ccircle cx='140' cy='25' r='2.2'/%3E%3Ccircle cx='70' cy='110' r='2.2'/%3E%3Ccircle cx='20' cy='140' r='2.2'/%3E%3Ccircle cx='130' cy='130' r='2.2'/%3E%3Ccircle cx='15' cy='90' r='2.2'/%3E%3C/g%3E%3C/svg%3E") repeat,
                linear-gradient(180deg, #05070d 0%, #0b1220 55%, #0a0f1a 100%);
            background-attachment: fixed;
            color: var(--text);
            font-family: var(--sans);
        }

        [data-testid="stSidebar"] {
            background: rgba(10, 16, 27, 0.86);
            backdrop-filter: blur(14px);
            border-right: 1px solid var(--line);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
            position: relative;
            z-index: 1;
        }

        @keyframes scan {
            0% { transform: translateX(-120%); }
            100% { transform: translateX(220%); }
        }

        @keyframes pulse-dot {
            0%, 100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.55); }
            50% { box-shadow: 0 0 0 6px rgba(52, 211, 153, 0); }
        }

        .hero-card {
            background: linear-gradient(135deg, rgba(12, 23, 38, 0.88), rgba(19, 32, 52, 0.86));
            border: 1px solid rgba(125, 211, 252, 0.2);
            border-radius: 24px;
            padding: 2rem 1.6rem;
            box-shadow: 0 18px 40px rgba(8, 15, 27, 0.45);
            margin-bottom: 1.7rem;
            position: relative;
            overflow: hidden;
        }

        .hero-card::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(120deg, rgba(103, 213, 255, 0.10), transparent 38%, rgba(139, 92, 246, 0.10));
            pointer-events: none;
        }

        .hero-card::after {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            height: 2px;
            width: 30%;
            background: linear-gradient(90deg, transparent, var(--accent), transparent);
            animation: scan 3.4s linear infinite;
        }

        .brand-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.8rem;
            margin-bottom: 0.7rem;
            position: relative;
            z-index: 1;
        }

        .brand-left {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .brand-badge {
            width: 48px;
            height: 48px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
            background: linear-gradient(135deg, #58d3ff, #8b5cf6);
            box-shadow: 0 10px 22px rgba(103, 213, 255, 0.30);
        }

        .main-title {
            font-size: 3rem;
            font-weight: 700;
            margin: 0;
            letter-spacing: -0.04em;
            line-height: 1.1;
        }

        .live-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: var(--mono);
            font-size: 0.76rem;
            letter-spacing: 0.08em;
            color: var(--accent-2);
            text-transform: uppercase;
        }

        .live-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
            animation: pulse-dot 1.8s infinite;
        }

        .muted {
            color: var(--muted);
            font-size: 1.08rem;
            position: relative;
            z-index: 1;
        }

        .status-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-top: 1rem;
            position: relative;
            z-index: 1;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.42rem 0.8rem;
            border-radius: 999px;
            font-size: 0.84rem;
            background: rgba(103, 213, 255, 0.12);
            border: 1px solid rgba(103, 213, 255, 0.30);
            color: #dff8ff;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }

        .status-pill.success {
            background: rgba(52, 211, 153, 0.10);
            border-color: rgba(52, 211, 153, 0.25);
            color: #d9fff1;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.8rem;
            margin-top: 1.5rem;
            position: relative;
            z-index: 1;
        }

        @media (max-width: 900px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }

        .stat-tile {
            background: rgba(8, 13, 23, 0.6);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 0.85rem 1rem;
        }

        .stat-label {
            font-family: var(--mono);
            font-size: 0.68rem;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: var(--muted);
        }

        .stat-value {
            font-family: var(--sans);
            font-size: 1.8rem;
            font-weight: 700;
            margin-top: 0.15rem;
        }

        .sidebar-card {
            background: linear-gradient(180deg, rgba(21, 30, 46, 0.82), rgba(13, 19, 30, 0.9));
            border: 1px solid rgba(103, 213, 255, 0.18);
            border-radius: 18px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 10px 18px rgba(2, 6, 23, 0.18);
        }

        .sidebar-eyebrow {
            font-family: var(--mono);
            font-size: 0.7rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--accent);
            margin-bottom: 0.3rem;
        }

        .sidebar-status {
            font-family: var(--mono);
            font-size: 0.76rem;
            color: var(--accent-2);
            display: flex;
            align-items: center;
            gap: 0.4rem;
            margin-top: 0.6rem;
        }

        .sidebar-card .stSelectbox > div,
        .sidebar-card .stCheckbox > div,
        .sidebar-card .stButton > button {
            border-radius: 12px;
        }

        .section-card {
            background: rgba(17, 24, 39, 0.7);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            margin-top: 1.2rem;
        }

        .chat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.2rem 0.4rem 0.7rem;
        }

        .chat-header-title {
            font-weight: 700;
            font-size: 1.05rem;
        }

        .chat-container {
            background: rgba(15, 23, 42, 0.56);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 0.4rem 0.5rem 0.8rem;
        }

        div[data-testid="stChatMessage"] {
            background: linear-gradient(180deg, rgba(16, 25, 38, 0.82), rgba(11, 18, 29, 0.78));
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 16px;
            padding: 0.8rem 0.9rem;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.10);
        }

        .stChatInput {
            border-radius: 18px;
            border: 1px solid rgba(248, 113, 113, 0.75);
            background: rgba(16, 22, 31, 0.88);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 12px 24px rgba(0, 0, 0, 0.18);
        }

        .telemetry-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 0.7rem;
            margin: 0.6rem 0 1rem;
            font-family: var(--mono);
            font-size: 0.75rem;
        }

        .legend-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            border: 1px solid var(--line);
        }

        .telemetry-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.88rem;
            overflow: hidden;
            border-radius: 14px;
            border: 1px solid var(--line);
        }

        .telemetry-table th {
            font-family: var(--mono);
            font-size: 0.7rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
            text-align: left;
            background: rgba(15, 23, 42, 0.9);
            padding: 0.6rem 0.8rem;
            border-bottom: 1px solid var(--line);
        }

        .telemetry-table td {
            padding: 0.55rem 0.8rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.10);
            background: rgba(15, 23, 42, 0.55);
            vertical-align: top;
        }

        .telemetry-table tr:last-child td {
            border-bottom: none;
        }

        .decision-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
            font-family: var(--mono);
            font-weight: 600;
            font-size: 0.76rem;
            white-space: nowrap;
        }

        .stMarkdown h3 {
            letter-spacing: -0.03em;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "logs" not in st.session_state:
    st.session_state.logs = []

decision_counts = {"ALLOW": 0, "REWRITE": 0, "BLOCK": 0, "ESCALATE": 0}
for entry in st.session_state.logs:
    if entry["action"] in decision_counts:
        decision_counts[entry["action"]] += 1
messages_reviewed = len(st.session_state.logs)

st.markdown(
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
        </div>
        <div class="stats-grid">
            <div class="stat-tile">
                <div class="stat-label">Messages reviewed</div>
                <div class="stat-value" style="color: var(--accent);">{messages_reviewed}</div>
            </div>
            <div class="stat-tile">
                <div class="stat-label">Allowed</div>
                <div class="stat-value" style="color: {STATUS_STYLES['ALLOW']['color']};">{decision_counts['ALLOW']}</div>
            </div>
            <div class="stat-tile">
                <div class="stat-label">Rewritten</div>
                <div class="stat-value" style="color: {STATUS_STYLES['REWRITE']['color']};">{decision_counts['REWRITE']}</div>
            </div>
            <div class="stat-tile">
                <div class="stat-label">Blocked / escalated</div>
                <div class="stat-value" style="color: {STATUS_STYLES['BLOCK']['color']};">{decision_counts['BLOCK'] + decision_counts['ESCALATE']}</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-eyebrow'>🛰️ Control panel</div>", unsafe_allow_html=True)
    st.header("Parent Controls")
    age_band = st.selectbox("Child age band", ["8-10", "11-13", "14-16"], index=1)
    show_logs = st.checkbox("Show safety decision log", value=True)
    st.info("In the project assumption, the official ChatGPT website is blocked for the child's account. This app is the only approved ChatGPT interface.")
    st.markdown("<div class='sidebar-status'><span class='live-dot'></span>Filter engine: online</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

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

st.markdown("</div>", unsafe_allow_html=True)

if show_logs:
    st.divider()
    st.subheader("🛰️ Safety Telemetry Log")
    if st.session_state.logs:
        legend_chips = "".join(
            f"<span class='legend-chip'>{style['icon']} "
            f"<span style='color:{style['color']};'>{action}</span></span>"
            for action, style in STATUS_STYLES.items()
        )
        st.markdown(f"<div class='telemetry-legend'>{legend_chips}</div>", unsafe_allow_html=True)

        rows = ""
        for entry in reversed(st.session_state.logs):
            style = STATUS_STYLES.get(entry["action"], {"color": "#a8b6d3", "bg": "rgba(148,163,184,0.12)", "icon": "•"})
            badge = (
                f"<span class='decision-badge' style='color:{style['color']}; background:{style['bg']};'>"
                f"{style['icon']} {html.escape(entry['action'])}</span>"
            )
            rows += (
                "<tr>"
                f"<td>{html.escape(entry['stage'])}</td>"
                f"<td>{badge}</td>"
                f"<td>{html.escape(entry['category'])}</td>"
                f"<td>{html.escape(entry['severity'])}</td>"
                f"<td>{html.escape(entry['explanation'])}</td>"
                "</tr>"
            )

        st.markdown(
            f"""
            <table class="telemetry-table">
                <thead>
                    <tr>
                        <th>Stage</th>
                        <th>Decision</th>
                        <th>Category</th>
                        <th>Severity</th>
                        <th>Explanation</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.write("No safety decisions yet.")
