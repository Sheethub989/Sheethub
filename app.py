import streamlit as st
import pandas as pd
import io
import uuid

# ---------------- CONFIG ----------------
FREE_DAILY_LIMIT = 5

# ---------------- IMPORTS ----------------
from utils.db import (
    init_db,
    get_or_create_user,
    can_use,
    increment_usage,
    remaining_quota,
    save_file_history,
    get_file_history,
    get_user_plan,
)

from utils.excel_cleaner import (
    smart_clean_sheets_from_bytes,
    make_excel_bytes_from_sheets,
)

from utils.ai_insights import generate_ai_insights

# ---------------- INIT ----------------
st.set_page_config(page_title="SheetHub", layout="wide")
init_db()

# ---------------- 🎨 ULTRA UI ----------------
st.markdown("""
<style>

/* BACKGROUND */
[data-testid="stAppViewContainer"] {
    background:
    radial-gradient(circle at 20% 30%, rgba(14,165,233,0.25), transparent 40%),
    radial-gradient(circle at 80% 70%, rgba(34,197,94,0.25), transparent 40%),
    #020617;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: #020617;
}

/* GLASS CARD */
.glass {
    background: rgba(255,255,255,0.05);
    border-radius: 18px;
    padding: 25px;
    backdrop-filter: blur(12px);
    margin-bottom: 20px;
}

/* HERO */
.hero {
    text-align:center;
    margin-top:20px;
    margin-bottom:30px;
}

.hero h1 {
    font-size: 2.5rem;
    font-weight: 700;
}

.hero p {
    color: #94a3b8;
}

/* FEATURE PILLS */
.pill {
    display:inline-block;
    padding:10px 20px;
    border-radius:999px;
    background: rgba(255,255,255,0.08);
    margin:5px;
}

/* BUTTON */
.stButton>button {
    background: linear-gradient(90deg, #22c55e, #4ade80);
    color: black;
    border-radius: 10px;
    font-weight: bold;
}

/* LOGIN CARD */
.login {
    max-width:400px;
    margin:auto;
    margin-top:100px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("email", None)

# ---------------- LOGIN ----------------
if st.session_state.user_id is None:

    st.markdown("""
    <div class="login glass">
        <h2 style="text-align:center;">🔐 Login to SheetHub</h2>
        <p style="text-align:center; color:#94a3b8;">Start cleaning Excel instantly</p>
    </div>
    """, unsafe_allow_html=True)

    email = st.text_input("", placeholder="Enter your email")

    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        login = st.button("🚀 Continue", use_container_width=True)

    if login:
        if "@" not in email:
            st.error("Enter valid email")
        else:
            st.session_state.user_id = get_or_create_user(email)
            st.session_state.email = email
            st.rerun()

    st.stop()

# ---------------- USER ----------------
user_id = st.session_state.user_id
is_pro = get_user_plan(user_id) == "pro"

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("## 👤 Account")
st.sidebar.write(st.session_state.email)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("## 💳 Plan")
st.sidebar.info("PRO 🚀" if is_pro else "Free")

remaining = remaining_quota(user_id)
used = FREE_DAILY_LIMIT - remaining

if not is_pro:
    st.sidebar.progress(used / FREE_DAILY_LIMIT)
    st.sidebar.caption(f"{remaining}/5 left")

st.sidebar.markdown("## ⚙️ Cleaning")
apply_standardize = st.sidebar.checkbox("Standardize", True)
remove_summary = st.sidebar.checkbox("Remove summary", True)
remove_dupes = st.sidebar.checkbox("Remove duplicates", True)
drop_missing = st.sidebar.checkbox("Remove missing", False)

# ---------------- HERO ----------------
st.markdown("""
<div class="hero">
<h1>📊 SheetHub</h1>
<p>Clean Excel data instantly. No formulas. No headaches.</p>
</div>
""", unsafe_allow_html=True)

# FEATURES
st.markdown("""
<div style="text-align:center;">
<span class="pill">⚡ Fast Cleaning</span>
<span class="pill">🤖 AI Insights</span>
<span class="pill">📊 Smart Charts</span>
</div>
""", unsafe_allow_html=True)

# ---------------- UPLOAD ----------------
st.markdown('<div class="glass">', unsafe_allow_html=True)

st.markdown("### 📂 Upload Excel Files")
files = st.file_uploader("", type=["xlsx"], accept_multiple_files=True)

st.markdown('</div>', unsafe_allow_html=True)

# ---------------- LIMIT ----------------
if not is_pro and remaining <= 0:
    st.warning("🚫 Daily limit reached")
    st.stop()

# ---------------- PROCESS ----------------
if files:
    for file in files:

        if not is_pro and not can_use(user_id):
            st.error("Limit reached")
            break

        cleaned = smart_clean_sheets_from_bytes(
            file.read(),
            apply_standardize,
            remove_summary,
            ["total"],
            remove_dupes,
            None,
            drop_missing,
        )

        increment_usage(user_id)

        # SUMMARY
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown("### 🧾 Summary")
        for sheet, df in cleaned.items():
            st.write(f"{sheet} → {len(df)} rows")
            save_file_history(user_id, file.name, len(df), df.shape[1])
        st.markdown('</div>', unsafe_allow_html=True)

        # AI
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown("### 🤖 AI Insights")
        for sheet, df in cleaned.items():
            for insight in generate_ai_insights(df):
                st.write("•", insight)
        st.markdown('</div>', unsafe_allow_html=True)

        # DOWNLOAD
        out = make_excel_bytes_from_sheets(cleaned)
        st.download_button("⬇️ Download Cleaned File", out.getvalue(), f"cleaned_{file.name}")

# ---------------- FOOTER ----------------
st.markdown("""
<div style="text-align:center; color:#64748b; margin-top:40px;">
© 2026 SheetHub • Privacy • Terms • Refund
</div>
""", unsafe_allow_html=True)
