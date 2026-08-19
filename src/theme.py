import streamlit as st

BASE_CSS = """
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

.status-pill.warning {
    background: rgba(250, 178, 25, 0.12);
    border-color: rgba(250, 178, 25, 0.30);
    color: #ffe9b8;
}

.status-pill.critical {
    background: rgba(208, 59, 59, 0.14);
    border-color: rgba(208, 59, 59, 0.35);
    color: #ffd6d6;
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

.vision-card {
    background: linear-gradient(135deg, rgba(23, 48, 68, 0.82), rgba(24, 37, 62, 0.78));
    border: 1px solid rgba(110, 231, 183, 0.25);
    border-radius: 18px;
    padding: 1.25rem 1.35rem;
    margin: 1.2rem 0 1.5rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 12px 24px rgba(2, 6, 23, 0.20);
}

.vision-heading {
    color: var(--accent-2);
    font-family: var(--mono);
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}

.vision-title {
    color: var(--text);
    font-size: 1.35rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
}

.vision-copy {
    color: var(--muted);
    line-height: 1.55;
}

.vision-points {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.65rem;
    margin-top: 1rem;
}

@media (max-width: 900px) {
    .vision-points { grid-template-columns: 1fr; }
}

.vision-point {
    background: rgba(8, 13, 23, 0.34);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 12px;
    padding: 0.7rem 0.8rem;
    color: #dff8ff;
    font-size: 0.88rem;
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

.alert-banner {
    border-radius: 18px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.9rem;
    border: 1px solid var(--line);
    position: relative;
    z-index: 1;
}

.alert-banner.critical {
    background: rgba(208, 59, 59, 0.14);
    border-color: rgba(208, 59, 59, 0.4);
}

.alert-banner.warning {
    background: rgba(250, 178, 25, 0.12);
    border-color: rgba(250, 178, 25, 0.35);
}

.alert-banner.clear {
    background: rgba(52, 211, 153, 0.10);
    border-color: rgba(52, 211, 153, 0.3);
}

.alert-title {
    font-weight: 700;
    font-size: 1.05rem;
    margin-bottom: 0.3rem;
}

.alert-item {
    background: rgba(8, 13, 23, 0.45);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.7rem 0.9rem;
    margin-top: 0.6rem;
}

.alert-item .alert-meta {
    font-family: var(--mono);
    font-size: 0.72rem;
    color: var(--muted);
    margin-bottom: 0.3rem;
}

.alert-item .alert-message {
    font-size: 0.92rem;
}

.stMarkdown h3 {
    letter-spacing: -0.03em;
}
"""


def inject_base_styles(extra_css: str = "") -> None:
    st.markdown(f"<style>{BASE_CSS}{extra_css}</style>", unsafe_allow_html=True)


def hide_page_nav() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"],
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="stSidebar"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )
