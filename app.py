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

# ---------------- 🎨 UI STYLE ----------------
st.markdown("""
<style>

/* BACKGROUND */
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 20% 20%, #0ea5e9 0%, transparent 25%),
                radial-gradient(circle at 80% 80%, #22c55e 0%, transparent 25%),
                #020617;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: #020617;
}

/* CARDS */
.card {
    background: rgba(255,255,255,0.05);
    padding: 25px;
    border-radius: 16px;
    margin-bottom: 20px;
}

/* BUTTON */
.stButton>button {
    background: linear-gradient(90deg, #22c55e, #4ade80);
    color: black;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: bold;
}

/* LOGIN BOX */
.login-box {
    max-width: 400px;
    margin: auto;
    margin-top: 120px;
    background: rgba(255,255,255,0.05);
    padding: 30px;
    border-radius: 15px;
    text-align: center;
}

/* UPLOAD BOX */
[data-testid="stFileUploader"] {
    border: 2px dashed #38bdf8;
    border-radius: 12px;
    padding: 20px;
}

/* TITLE */
.title {
    font-size: 2.2rem;
    font-weight: bold;
}

/* SUBTEXT */
.subtext {
    color: #94a3b8;
}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("email", None)

# ---------------- LOGIN ----------------
if st.session_state.user_id is None:

    st.markdown("""
    <div class="login-box">
        <h2>🔐 Login to SheetHub</h2>
    </div>
    """, unsafe_allow_html=True)

    email = st.text_input("Email")

    if st.button("Login"):
        if "@" not in email:
            st.error("Enter valid email")
        else:
            st.session_state.user_id = get_or_create_user(email)
            st.session_state.email = email
            st.rerun()

    st.stop()

user_id = st.session_state.user_id
is_pro = get_user_plan(user_id) == "pro"

# ---------------- SIDEBAR (RESTORED) ----------------
st.sidebar.markdown("## 👤 Account")
st.sidebar.write(st.session_state.email)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# PLAN
st.sidebar.markdown("## 💳 Plan")
if is_pro:
    st.sidebar.success("PRO 🚀")
else:
    st.sidebar.info("Free plan")

# USAGE
remaining = remaining_quota(user_id)
used = FREE_DAILY_LIMIT - remaining

if not is_pro:
    st.sidebar.progress(used / FREE_DAILY_LIMIT)
    st.sidebar.caption(f"{remaining}/5 left today")

# HISTORY
st.sidebar.markdown("## 🕓 File History")
history = get_file_history(user_id)

if not history:
    st.sidebar.caption("No files yet")
else:
    for name, rows, cols, _ in history:
        st.sidebar.write(f"📄 {name}")
        st.sidebar.caption(f"{rows} rows • {cols} cols")

# CLEAN OPTIONS
st.sidebar.markdown("## ⚙️ Cleaning Options")
apply_standardize = st.sidebar.checkbox("Standardize columns", True)
remove_summary = st.sidebar.checkbox("Remove summary rows", True)
remove_dupes = st.sidebar.checkbox("Remove duplicates", True)
drop_missing = st.sidebar.checkbox("Remove missing values", False)

# ---------------- HEADER ----------------
st.markdown('<div class="title">📊 SheetHub — Smart Excel Cleaner</div>', unsafe_allow_html=True)
st.markdown('<div class="subtext">Clean Excel data instantly. No formulas. No headaches.</div>', unsafe_allow_html=True)

# ---------------- UPLOAD ----------------
st.markdown('<div class="card">', unsafe_allow_html=True)

st.markdown("### 📂 Upload Excel Files")
files = st.file_uploader("", type=["xlsx"], accept_multiple_files=True)

if not is_pro:
    st.caption("Free: 5 files/day • PRO soon")

st.markdown('</div>', unsafe_allow_html=True)

# ---------------- LIMIT BLOCK ----------------
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
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🧾 Summary")

        for sheet, df in cleaned.items():
            st.write(f"{sheet} → {len(df)} rows")
            save_file_history(user_id, file.name, len(df), df.shape[1])

        st.markdown('</div>', unsafe_allow_html=True)

        # AI
        st.markdown('<div class="card">', unsafe_allow_html=True)
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
