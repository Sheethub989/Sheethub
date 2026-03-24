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

# ---------------- 🎨 PREMIUM UI ----------------
st.markdown("""
<style>

/* BACKGROUND */
[data-testid="stAppViewContainer"] {
    background:
    radial-gradient(circle at 20% 30%, rgba(14,165,233,0.15), transparent 40%),
    radial-gradient(circle at 80% 70%, rgba(34,197,94,0.15), transparent 40%),
    #020617;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: #020617;
}

/* GLASS */
.glass {
    background: rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(10px);
    margin-bottom: 20px;
}

/* HERO */
.hero {
    text-align:center;
    margin-top:20px;
    margin-bottom:25px;
}

.hero h1 {
    font-size: 2.2rem;
    font-weight: 600;
}

.hero p {
    color: #94a3b8;
}

/* FEATURE PILLS */
.pill {
    display:inline-block;
    padding:8px 18px;
    border-radius:999px;
    background: rgba(255,255,255,0.08);
    margin:5px;
}

/* BUTTON */
.stButton>button {
    border-radius: 10px;
    height: 42px;
    font-weight: 600;
    background: linear-gradient(135deg, #22c55e, #16a34a);
    border: none;
    color: white;
}

.stButton>button:hover {
    transform: scale(1.02);
}

/* INPUT */
.stTextInput input {
    border-radius: 10px !important;
    padding: 10px !important;
}

/* LOGIN BOX */
.login-box {
    width: 340px;
    margin: auto;
    margin-top: 120px;
    padding: 30px;
    border-radius: 18px;
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(14px);
    text-align: center;
}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("email", None)

# ---------------- PREMIUM LOGIN FIX ----------------
if st.session_state.user_id is None:

    st.markdown("""
    <style>

    .stApp {
        background:
        radial-gradient(circle at 20% 20%, rgba(14,165,233,0.15), transparent 40%),
        radial-gradient(circle at 80% 80%, rgba(34,197,94,0.15), transparent 40%),
        #020617;
    }

    .login-container {
        text-align: center;
        padding-top: 80px;
    }

    .logo {
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .tagline {
        color: #94a3b8;
        margin-bottom: 30px;
        font-size: 14px;
    }

    .login-card {
        max-width: 400px;
        margin: auto;
        padding: 30px;
        border-radius: 18px;
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 20px 60px rgba(0,0,0,0.6);
    }

    .features {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-top: 20px;
        font-size: 12px;
        color: #94a3b8;
    }

    .feature-pill {
        padding: 6px 12px;
        border-radius: 20px;
        background: rgba(255,255,255,0.05);
    }

    .stTextInput input {
        border-radius: 12px !important;
        padding: 12px !important;
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }

    .stButton button {
        width: 100% !important;
        height: 45px;
        border-radius: 12px;
        background: linear-gradient(135deg, #22c55e, #16a34a);
        color: white;
        font-weight: 600;
        border: none;
    }

    .stButton button:hover {
        box-shadow: 0 0 20px rgba(34,197,94,0.7);
        transform: translateY(-1px);
    }

    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    st.markdown('<div class="logo">📊 SheetHub</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline">Clean Excel instantly • No formulas • No stress</div>', unsafe_allow_html=True)

    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    email = st.text_input("", placeholder="Enter your email")

    if st.button("🚀 Continue"):
        if "@" not in email:
            st.error("Enter valid email")
        else:
            st.session_state.user_id = get_or_create_user(email)
            st.session_state.email = email
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ✨ Feature highlights (THIS FIXES "EMPTY FEEL")
    st.markdown("""
    <div class="features">
        <div class="feature-pill">⚡ Fast Cleaning</div>
        <div class="feature-pill">🤖 AI Insights</div>
        <div class="feature-pill">📊 Smart Charts</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

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

if is_pro:
    st.sidebar.success("🚀 PRO ACTIVE")
else:
    st.sidebar.markdown("Free Plan")
    st.sidebar.markdown("<span style='color:#22c55e;'>🚀 PRO coming soon</span>", unsafe_allow_html=True)

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

        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown("### 🧾 Summary")
        for sheet, df in cleaned.items():
            st.write(f"{sheet} → {len(df)} rows")
            save_file_history(user_id, file.name, len(df), df.shape[1])
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.markdown("### 🤖 AI Insights")
        for sheet, df in cleaned.items():
            for insight in generate_ai_insights(df):
                st.write("•", insight)
        st.markdown('</div>', unsafe_allow_html=True)

        out = make_excel_bytes_from_sheets(cleaned)
        st.download_button("⬇️ Download Cleaned File", out.getvalue(), f"cleaned_{file.name}")

# ---------------- FOOTER ----------------
st.markdown("""
<div style="text-align:center; color:#64748b; margin-top:40px;">
© 2026 SheetHub • Privacy • Terms • Refund
</div>
""", unsafe_allow_html=True)
