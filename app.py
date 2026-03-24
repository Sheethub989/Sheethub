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

# ---------------- 🎨 PREMIUM UI ----------------
st.markdown("""
<style>

/* Background */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #020617, #0f172a);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #020617;
}

/* Text */
h1, h2, h3 {
    color: #38bdf8;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(90deg, #22c55e, #4ade80);
    color: black;
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: bold;
    border: none;
}

/* Upload Box */
[data-testid="stFileUploader"] {
    border: 2px dashed #38bdf8;
    border-radius: 15px;
    padding: 25px;
    background: rgba(255,255,255,0.02);
}

/* Card style */
.card {
    background: rgba(255,255,255,0.05);
    padding: 25px;
    border-radius: 15px;
    backdrop-filter: blur(10px);
    margin-bottom: 20px;
}

/* Center hero */
.hero {
    text-align: center;
    padding: 30px;
}

.small-text {
    color: #94a3b8;
    font-size: 14px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("email", None)

# ---------------- LOGIN ----------------
if st.session_state.user_id is None:
    st.markdown("<div class='hero'><h2>🔐 Login to SheetHub</h2></div>", unsafe_allow_html=True)

    email = st.text_input("Email address")

    if st.button("Login"):
        if "@" not in email:
            st.error("Enter valid email")
        else:
            st.session_state.user_id = get_or_create_user(email)
            st.session_state.email = email
            st.success("Logged in ✅")
            st.rerun()

    st.stop()

user_id = st.session_state.user_id
is_pro = get_user_plan(user_id) == "pro"

# ---------------- HERO ----------------
st.markdown("""
<div class='hero'>
<h1>📊 SheetHub</h1>
<p class='small-text'>
Clean, analyze & visualize Excel data in seconds 🚀
</p>
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
    st.sidebar.success("PRO 🚀 Unlimited")
else:
    st.sidebar.info("Free Plan (5/day)")

# ---------------- USAGE ----------------
st.sidebar.markdown("## 📊 Daily Usage")

if is_pro:
    st.sidebar.success("Unlimited 🚀")
else:
    remaining = remaining_quota(user_id)
    used = FREE_DAILY_LIMIT - remaining
    progress = max(0.0, min(used / FREE_DAILY_LIMIT, 1.0))

    st.sidebar.progress(progress)
    st.sidebar.caption(f"{remaining} / {FREE_DAILY_LIMIT} left")

# ---------------- HISTORY ----------------
st.sidebar.markdown("## 🕓 Recent Files")
for name, r, c, _ in get_file_history(user_id):
    st.sidebar.caption(f"{name} — {r}×{c}")

# ---------------- MAIN CARD ----------------
st.markdown("<div class='card'>", unsafe_allow_html=True)

st.markdown("### 📂 Upload Excel File")

files = st.file_uploader(
    "",
    type=["xlsx"],
    accept_multiple_files=True,
)

if not is_pro:
    st.caption("🚀 Free: 5 files/day • PRO coming soon")

st.markdown("</div>", unsafe_allow_html=True)

# ---------------- LIMIT ----------------
if not is_pro and remaining_quota(user_id) <= 0:
    st.warning("🚫 Daily limit reached (5/day)")
    st.stop()

# ---------------- PIPELINE ----------------
if files:
    for file in files:

        if not is_pro and not can_use(user_id):
            st.error("Limit reached")
            break

        file_bytes = file.read()

        try:
            raw_sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
            original_rows = {k: len(v) for k, v in raw_sheets.items()}
        except:
            st.error("Invalid file")
            continue

        cleaned = smart_clean_sheets_from_bytes(
            file_bytes,
            True,
            True,
            ["total","subtotal","grand total"],
            True,
            None,
            False,
        )

        increment_usage(user_id)

        st.markdown("<div class='card'>", unsafe_allow_html=True)

        st.markdown("### 🧾 Cleaning Summary")

        for sheet, df in cleaned.items():
            removed = original_rows.get(sheet, 0) - len(df)
            st.write(f"**{sheet}** → {len(df)} rows ({removed} removed)")
            save_file_history(user_id, file.name, len(df), df.shape[1])

        st.markdown("</div>", unsafe_allow_html=True)

        # AI
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### 🤖 AI Insights")

        for sheet, df in cleaned.items():
            if not df.empty:
                for i in generate_ai_insights(df):
                    st.write("•", i)

        st.markdown("</div>", unsafe_allow_html=True)

        # Download
        out = make_excel_bytes_from_sheets(cleaned)
        st.download_button(
            "⬇️ Download Cleaned File",
            out.getvalue(),
            f"cleaned_{file.name}",
        )

# ---------------- FOOTER ----------------
st.markdown("""
<hr>
<p style='text-align:center; color:#64748b; font-size:12px;'>
© 2026 SheetHub • Privacy • Terms • Refund
</p>
""", unsafe_allow_html=True)
