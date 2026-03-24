import streamlit as st
import pandas as pd
import io

# ---------------- CONFIG ----------------
FREE_DAILY_LIMIT = 5

# ---------------- DB ----------------
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

# ---------------- CORE ----------------
from utils.excel_cleaner import (
    smart_clean_sheets_from_bytes,
    make_excel_bytes_from_sheets,
)
from utils.ai_insights import generate_ai_insights

# ---------------- INIT ----------------
st.set_page_config(page_title="SheetHub", layout="wide")
init_db()

# ---------------- 🔥 ULTRA UI ----------------
st.markdown("""
<style>

/* Background Glow */
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 20% 20%, #0ea5e9 0%, transparent 25%),
                radial-gradient(circle at 80% 80%, #22c55e 0%, transparent 25%),
                #020617;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #020617;
}

/* Typography */
h1, h2, h3 {
    color: #38bdf8;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(90deg, #22c55e, #4ade80);
    color: black;
    border-radius: 12px;
    padding: 12px 24px;
    font-weight: bold;
}

/* Upload Box */
[data-testid="stFileUploader"] {
    border: 2px dashed #38bdf8;
    border-radius: 15px;
    padding: 25px;
    background: rgba(255,255,255,0.03);
}

/* Glass Card */
.card {
    background: rgba(255,255,255,0.05);
    padding: 30px;
    border-radius: 20px;
    backdrop-filter: blur(12px);
    margin-bottom: 25px;
}

/* Hero */
.hero {
    text-align: center;
    padding: 40px 20px;
}

.hero h1 {
    font-size: 3rem;
}

.hero p {
    color: #94a3b8;
    font-size: 18px;
}

/* Features grid */
.features {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

.feature-box {
    background: rgba(255,255,255,0.05);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
}

/* Footer */
.footer {
    text-align: center;
    color: #64748b;
    font-size: 12px;
    padding: 20px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("email", None)

# ---------------- LOGIN ----------------
if st.session_state.user_id is None:
    st.markdown("<div class='hero'><h2>🔐 Login to SheetHub</h2></div>", unsafe_allow_html=True)

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

# ---------------- HERO ----------------
st.markdown("""
<div class='hero'>
<h1>📊 SheetHub</h1>
<p>Clean Excel data instantly. No formulas. No headaches.</p>
</div>
""", unsafe_allow_html=True)

# ---------------- FEATURES ----------------
st.markdown("""
<div class='features'>
<div class='feature-box'>⚡ Fast Cleaning</div>
<div class='feature-box'>🤖 AI Insights</div>
<div class='feature-box'>📊 Smart Charts</div>
</div>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("## 👤 Account")
st.sidebar.write(st.session_state.email)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ---------------- PLAN ----------------
st.sidebar.markdown("## 💳 Plan")
if is_pro:
    st.sidebar.success("PRO 🚀")
else:
    st.sidebar.info("Free (5/day)")

# ---------------- USAGE ----------------
if not is_pro:
    remaining = remaining_quota(user_id)
    st.sidebar.progress((FREE_DAILY_LIMIT - remaining) / FREE_DAILY_LIMIT)
    st.sidebar.caption(f"{remaining}/5 left")

# ---------------- MAIN ----------------
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("### 📂 Upload Excel Files")

files = st.file_uploader("", type=["xlsx"], accept_multiple_files=True)

if not is_pro:
    st.caption("🚀 Free: 5 files/day • PRO soon")

st.markdown("</div>", unsafe_allow_html=True)

# ---------------- LIMIT ----------------
if not is_pro and remaining_quota(user_id) <= 0:
    st.warning("Limit reached")
    st.stop()

# ---------------- PROCESS ----------------
if files:
    for file in files:

        if not is_pro and not can_use(user_id):
            st.error("Limit reached")
            break

        data = file.read()

        cleaned = smart_clean_sheets_from_bytes(
            data, True, True, ["total"], True, None, False
        )

        increment_usage(user_id)

        # Summary Card
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 🧾 Summary")

        for s, df in cleaned.items():
            st.write(f"{s} → {len(df)} rows")
            save_file_history(user_id, file.name, len(df), df.shape[1])

        st.markdown("</div>", unsafe_allow_html=True)

        # AI Card
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 🤖 AI Insights")

        for s, df in cleaned.items():
            for i in generate_ai_insights(df):
                st.write("•", i)

        st.markdown("</div>", unsafe_allow_html=True)

        # Download
        out = make_excel_bytes_from_sheets(cleaned)
        st.download_button("⬇️ Download File", out.getvalue(), f"cleaned_{file.name}")

# ---------------- FOOTER ----------------
st.markdown("""
<div class='footer'>
© 2026 SheetHub • Privacy • Terms • Refund
</div>
""", unsafe_allow_html=True)
