import streamlit as st
import pandas as pd
import io
import uuid
import plotly.express as px
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

# ---------------- CLEAN PREMIUM LOGIN ----------------
if st.session_state.user_id is None:

    st.markdown("""
    <style>
    .stApp {
        background:
        radial-gradient(circle at 20% 20%, rgba(14,165,233,0.15), transparent 40%),
        radial-gradient(circle at 80% 80%, rgba(34,197,94,0.15), transparent 40%),
        #020617;
    }

    .login-card {
        padding: 40px;
        border-radius: 20px;
        background: rgba(255,255,255,0.04);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 20px 60px rgba(0,0,0,0.6);
        text-align: center;
    }

    .title {
        font-size: 28px;
        font-weight: 600;
        margin-bottom: 5px;
    }

    .sub {
        font-size: 14px;
        color: #94a3b8;
        margin-bottom: 25px;
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
        font-weight: 600;
        background: linear-gradient(135deg, #22c55e, #16a34a);
        border: none;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    # CENTER USING COLUMNS (THIS FIXES EVERYTHING)
    left, center, right = st.columns([1, 1.2, 1])

    with center:
        

        st.markdown('<div class="title">📊 SheetHub</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub">Clean Excel instantly</div>', unsafe_allow_html=True)

        email = st.text_input("", placeholder="Enter your email")

        if st.button("🚀 Continue"):
            if "@" not in email:
                st.error("Enter valid email")
            else:
                st.session_state.user_id = get_or_create_user(email)
                st.session_state.email = email
                st.rerun()

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

# ---------------- ANALYTICS DASHBOARD ----------------

st.markdown("## 📊 Analytics Dashboard")

if 'cleaned' in locals():

    for sheet, df in cleaned.items():

        st.markdown(f"### 📄 {sheet}")

        # ---------------- METRICS ----------------

        total_rows = df.shape[0]
        total_cols = df.shape[1]
        missing_values = int(df.isnull().sum().sum())
        duplicate_rows = int(df.duplicated().sum())

        c1, c2, c3, c4 = st.columns([1,1,1,1])

        metrics = [
            ("📄 Rows", total_rows),
            ("📊 Columns", total_cols),
            ("⚠️ Missing", missing_values),
            ("🔁 Duplicates", duplicate_rows),
        ]

        for col, (title, value) in zip([c1, c2, c3, c4], metrics):

            with col:

                st.markdown(f"""
                <div style="
                    background: rgba(255,255,255,0.05);
                    padding: 22px;
                    border-radius: 18px;
                    border: 1px solid rgba(255,255,255,0.08);
                    text-align:center;
                    box-shadow: 0 0 20px rgba(0,255,180,0.08);
                ">
                    <h4 style='color:#9ca3af'>{title}</h4>
                    <h1 style='color:white'>{value}</h1>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("")

        # ---------------- CHART ----------------

        numeric_cols = df.select_dtypes(include="number").columns

        if len(numeric_cols) > 0:

            chart_col = numeric_cols[0]

            fig = px.line(
                df.head(50),
                y=chart_col,
                template="plotly_dark",
                title=f"{chart_col} Trend"
            )

            fig.update_layout(
                paper_bgcolor="#07111f",
                plot_bgcolor="#07111f",
                font_color="white",
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

        # ---------------- DATA PREVIEW ----------------

        st.markdown("### 👀 Data Preview")

        st.dataframe(
            df.head(),
            use_container_width=True
        )
        st.download_button(
            "⬇ Download Cleaned CSV",
            df.to_csv(index=False),
            file_name=f"{sheet}_cleaned.csv",
            mime="text/csv"
        )

        # ---------------- SAVE HISTORY ----------------

        save_file_history(
            user_id,
            file.name,
            total_rows,
            total_cols
        )
        # ---------------- SMART CHARTS ----------------

st.markdown("## 📈 Smart Charts")

if 'cleaned' in locals():

    for sheet, df in cleaned.items():

        st.markdown(f"### 📄 {sheet}")

        numeric_cols = df.select_dtypes(include="number").columns

        if len(numeric_cols) > 0:

            selected_col = st.selectbox(
                f"Select column for {sheet}",
                numeric_cols,
                key=sheet
            )

            chart_type = st.radio(
                "Chart Type",
                ["Line", "Bar", "Histogram"],
                horizontal=True,
                key=f"{sheet}_chart"
            )

            if chart_type == "Line":

                fig = px.line(
                    df.head(50),
                    y=selected_col,
                    template="plotly_dark"
                )

            elif chart_type == "Bar":

                fig = px.bar(
                    df.head(20),
                    y=selected_col,
                    template="plotly_dark"
                )

            else:

                fig = px.histogram(
                    df,
                    x=selected_col,
                    template="plotly_dark"
                )

            fig.update_layout(
                paper_bgcolor="#07111f",
                plot_bgcolor="#07111f",
                font_color="white",
                height=500
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info("No numeric columns found.")
            # ---------------- AI DATA SUMMARY ----------------

st.markdown("## 🤖 AI Dataset Summary")

if 'cleaned' in locals():

    for sheet, df in cleaned.items():

        st.markdown(f"### 📄 {sheet}")

        total_rows = df.shape[0]
        total_cols = df.shape[1]

        missing_values = int(df.isnull().sum().sum())
        duplicate_rows = int(df.duplicated().sum())

        numeric_cols = df.select_dtypes(include="number").columns
        text_cols = df.select_dtypes(include="object").columns

        insights = []

        # Dataset size
        if total_rows > 5000:
            insights.append("🚀 Large dataset detected. Performance optimization recommended.")
        else:
            insights.append("✅ Lightweight dataset detected.")

        # Missing values
        if missing_values > 0:
            insights.append(f"⚠️ Dataset contains {missing_values} missing values.")
        else:
            insights.append("✅ No missing values found.")

        # Duplicates
        if duplicate_rows > 0:
            insights.append(f"🔁 {duplicate_rows} duplicate rows detected.")
        else:
            insights.append("✅ No duplicate rows found.")

        # Numeric analysis
        if len(numeric_cols) > 0:

            for col in numeric_cols[:3]:

                avg = round(df[col].mean(), 2)
                max_val = round(df[col].max(), 2)
                min_val = round(df[col].min(), 2)

                insights.append(
                    f"📊 {col} → Avg: {avg} | Min: {min_val} | Max: {max_val}"
                )

        # Text analysis
        if len(text_cols) > 0:
            insights.append(
                f"📝 Dataset contains {len(text_cols)} text columns."
            )

        # PREMIUM AI CARDS
        for item in insights:

            st.markdown(f"""
            <div style="
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                padding: 16px;
                border-radius: 14px;
                margin-bottom: 12px;
                backdrop-filter: blur(10px);
                box-shadow: 0 0 20px rgba(0,255,180,0.04);
                color: white;
                font-size: 15px;
            ">
                {item}
            </div>
            """, unsafe_allow_html=True)


# ---------------- FOOTER ----------------
st.markdown("""
<div style="text-align:center; color:#64748b; margin-top:40px;">
© 2026 SheetHub • Privacy • Terms • Refund
</div>
""", unsafe_allow_html=True)
