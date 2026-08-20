import html
import os
from datetime import datetime

import streamlit as st
from chatgpt_adapter import get_chatgpt_status
from image_service import get_unsplash_status
from shared_store import (
    bridge_secrets_to_env,
    clear_log,
    get_pin_lockout,
    load_log,
    load_settings,
    record_failed_pin_attempt,
    reset_pin_attempts,
    save_settings,
)
from theme import hide_page_nav, inject_base_styles

st.set_page_config(page_title="SafeChatGPT — Guardian Command Center", page_icon="🛰️", layout="wide")

bridge_secrets_to_env()
inject_base_styles()
hide_page_nav()

STATUS_STYLES = {
    "ALLOW": {"color": "#0ca30c", "bg": "rgba(12, 163, 12, 0.14)", "icon": "✅"},
    "REWRITE": {"color": "#fab219", "bg": "rgba(250, 178, 25, 0.14)", "icon": "✏️"},
    "BLOCK": {"color": "#ec835a", "bg": "rgba(236, 131, 90, 0.16)", "icon": "⛔"},
    "ESCALATE": {"color": "#d03b3b", "bg": "rgba(208, 59, 59, 0.18)", "icon": "🚨"},
}

if "parent_authenticated" not in st.session_state:
    st.session_state.parent_authenticated = False

if not st.session_state.parent_authenticated:
    st.markdown(
        """
        <div class="hero-card">
            <div class="brand-row">
                <div class="brand-left">
                    <div class="brand-badge">🛰️</div>
                    <div class="main-title">Guardian Command Center</div>
                </div>
            </div>
            <div class="muted">Enter the parent PIN to view safety alerts and settings.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    lockout_until = get_pin_lockout()
    if lockout_until:
        minutes_left = max(1, int((lockout_until - datetime.now()).total_seconds() // 60) + 1)
        st.error(f"Too many incorrect PIN attempts. Try again in about {minutes_left} minute(s).")
    else:
        pin_input = st.text_input("Parent PIN", type="password")
        if st.button("Unlock"):
            if pin_input == os.getenv("PARENT_PIN", "1234"):
                reset_pin_attempts()
                st.session_state.parent_authenticated = True
                st.rerun()
            else:
                record_failed_pin_attempt()
                # The attempt just recorded may be the one that trips the
                # lockout. Rerun immediately so the top-of-script check picks
                # it up on a clean render — otherwise the PIN input/button
                # (already drawn earlier in this same run) would stay visible
                # alongside the lockout message, which reads as contradictory.
                if get_pin_lockout():
                    st.rerun()
                else:
                    st.error("Incorrect PIN.")
    st.stop()

if os.getenv("PARENT_PIN", "1234") == "1234":
    st.warning(
        "⚠️ You're using the default PIN (1234). Set your own `PARENT_PIN` in `.env` "
        "(or your deployment's secrets) before letting a child use this for real."
    )

log = load_log()
decision_counts = {"ALLOW": 0, "REWRITE": 0, "BLOCK": 0, "ESCALATE": 0}
for entry in log:
    if entry["action"] in decision_counts:
        decision_counts[entry["action"]] += 1

escalate_entries = [e for e in log if e["action"] == "ESCALATE"]
block_entries = [e for e in log if e["action"] == "BLOCK"]

st.markdown(
    f"""
    <div class="hero-card">
        <div class="brand-row">
            <div class="brand-left">
                <div class="brand-badge">🛰️</div>
                <div class="main-title">Guardian Command Center</div>
            </div>
            <div class="live-indicator"><span class="live-dot"></span>Monitoring</div>
        </div>
        <div class="muted">
            Automated safety feedback from your child's SafeChatGPT sessions — no need to read every message yourself.
        </div>
        <div class="stats-grid">
            <div class="stat-tile">
                <div class="stat-label">Messages reviewed</div>
                <div class="stat-value" style="color: var(--accent);">{len(log)}</div>
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

st.markdown(
    f"""
    <div class="vision-card">
        <div class="vision-heading">◉ Parents' Vision · Live Mode</div>
        <div class="vision-title">Give your child the benefits of AI, with you still in control.</div>
        <div class="vision-copy">
            ChatGPT Junior is the approved learning space: helpful questions stay available,
            unsafe requests are stopped, and the dashboard gives you live visibility without
            requiring you to read every conversation.
        </div>
        <div class="vision-points">
            <div class="vision-point">🛡️ Age-appropriate answers</div>
            <div class="vision-point">🔒 Other AI-switch attempts blocked</div>
            <div class="vision-point">📡 {len(block_entries) + len(escalate_entries)} live alert(s) for your attention</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("🔔 Automated Feedback")

if not escalate_entries and not block_entries:
    st.markdown(
        """
        <div class="alert-banner clear">
            <div class="alert-title">✅ No safety concerns detected</div>
            <div class="muted">Every message so far was either allowed or safely rewritten. You'll see an alert here the moment something needs your attention.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _stage_label(entry: dict) -> str:
    return f"📸 {entry['stage']}" if entry["stage"] == "Image" else entry["stage"]


def _alert_snippet(text: str, limit: int = 220) -> str:
    # Blocked/escalated "context" can be a multi-paragraph ChatGPT answer. A
    # blank line inside it ends the surrounding <div>'s HTML block early (per
    # CommonMark), so every alert-item after it in the list renders as literal
    # text instead of a styled card — collapsing to one line prevents that.
    collapsed = " ".join(text.split())
    if len(collapsed) > limit:
        collapsed = collapsed[: limit - 1].rstrip() + "…"
    return collapsed


if escalate_entries:
    items = "".join(
        f"""
        <div class="alert-item">
            <div class="alert-meta">{html.escape(e['timestamp'])} · {html.escape(_stage_label(e))} · {html.escape(e['category'])}</div>
            <div class="alert-message">&ldquo;{html.escape(_alert_snippet(e['context']))}&rdquo;</div>
        </div>
        """
        for e in reversed(escalate_entries)
    )
    st.markdown(
        f"""
        <div class="alert-banner critical">
            <div class="alert-title">🚨 {len(escalate_entries)} urgent alert(s) — your child may need support</div>
            <div class="muted">These messages matched self-harm or crisis language and were redirected to trusted-adult guidance instead of a normal answer.</div>
            {items}
        </div>
        """,
        unsafe_allow_html=True,
    )

if block_entries:
    items = "".join(
        f"""
        <div class="alert-item">
            <div class="alert-meta">{html.escape(e['timestamp'])} · {html.escape(_stage_label(e))} · {html.escape(e['category'])}</div>
            <div class="alert-message">&ldquo;{html.escape(_alert_snippet(e['context']))}&rdquo;</div>
        </div>
        """
        for e in reversed(block_entries)
    )
    st.markdown(
        f"""
        <div class="alert-banner warning">
            <div class="alert-title">⛔ {len(block_entries)} blocked attempt(s)</div>
            <div class="muted">Your child asked for something outside the allowed topics, or tried to bypass SafeChatGPT (including switching to another AI). Nothing unsafe was sent or shown.</div>
            {items}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
st.markdown("<div class='sidebar-eyebrow'>🛰️ Settings</div>", unsafe_allow_html=True)
settings = load_settings()
age_band = st.selectbox(
    "Child age band",
    ["8-10", "11-13", "14-16"],
    index=["8-10", "11-13", "14-16"].index(settings["age_band"]),
)
if age_band != settings["age_band"]:
    save_settings({**settings, "age_band": age_band})
    st.success(f"Age band updated to {age_band}.")

if st.button("Clear safety log"):
    clear_log()
    st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# A missing/blank API key produces no error anywhere — just a mock ChatGPT
# reply or an unrelated picsum.photos photo — so this is the only place that
# makes a silent misconfiguration visible instead of looking like a bug.
st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
st.markdown("<div class='sidebar-eyebrow'>🔌 Integration Status</div>", unsafe_allow_html=True)
chatgpt_status = get_chatgpt_status()
unsplash_status = get_unsplash_status()
if chatgpt_status["configured"]:
    st.success(f"ChatGPT: connected ({chatgpt_status['model']})")
else:
    st.warning("ChatGPT: not configured — running in mock mode")
if unsplash_status["configured"]:
    st.success(f"Unsplash: connected (key {unsplash_status['preview']})")
else:
    st.warning("Unsplash: not configured — images use the picsum.photos fallback (real but unrelated photos)")
st.markdown("</div>", unsafe_allow_html=True)

st.divider()
st.subheader("🛰️ Full Safety Telemetry Log")
if log:
    legend_chips = "".join(
        f"<span class='legend-chip'>{style['icon']} "
        f"<span style='color:{style['color']};'>{action}</span></span>"
        for action, style in STATUS_STYLES.items()
    )
    st.markdown(f"<div class='telemetry-legend'>{legend_chips}</div>", unsafe_allow_html=True)

    rows = ""
    for entry in reversed(log):
        style = STATUS_STYLES.get(entry["action"], {"color": "#a8b6d3", "bg": "rgba(148,163,184,0.12)", "icon": "•"})
        badge = (
            f"<span class='decision-badge' style='color:{style['color']}; background:{style['bg']};'>"
            f"{style['icon']} {html.escape(entry['action'])}</span>"
        )
        image_url = entry.get("image_url")
        preview = (
            f"<img src='{html.escape(image_url)}' alt='' style='width:48px;height:48px;object-fit:cover;border-radius:8px;border:1px solid var(--line);' />"
            if image_url
            else "—"
        )
        rows += (
            "<tr>"
            f"<td>{html.escape(entry['timestamp'])}</td>"
            f"<td>{html.escape(_stage_label(entry))}</td>"
            f"<td>{badge}</td>"
            f"<td>{html.escape(entry['category'])}</td>"
            f"<td>{html.escape(entry['severity'])}</td>"
            f"<td>{preview}</td>"
            f"<td>{html.escape(entry['explanation'])}</td>"
            "</tr>"
        )

    st.markdown(
        f"""
        <table class="telemetry-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Stage</th>
                    <th>Decision</th>
                    <th>Category</th>
                    <th>Severity</th>
                    <th>Preview</th>
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
