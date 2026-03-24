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
st.set_page_config(page_title="SheetHub", layout="centered")
init_db()

# ---------------- 🎨 CUSTOM UI ----------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #020617, #0f172a);
}
[data-testid="stSidebar"] {
    background: #020617;
}
h1, h2, h3 {
    color: #38bdf8;
}
.stButton>button {
    background-color: #22c55e;
    color: black;
    border-radius: 10px;
    font-weight: bold;
}
[data-testid="stFileUploader"] {
    border: 2px dashed #38bdf8;
    border-radius: 12px;
    padding: 20px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("email", None)

# ---------------- LOGIN ----------------
if st.session_state.user_id is None:
    st.markdown("""
    <h2 style='text-align:center;'>🔐 Login to SheetHub</h2>
    """, unsafe_allow_html=True)

    email = st.text_input("Email address")

    if st.button("Login"):
        if "@" not in email:
            st.error("Please enter a valid email")
        else:
            st.session_state.user_id = get_or_create_user(email)
            st.session_state.email = email
            st.success("Logged in successfully ✅")
            st.rerun()

    st.stop()

user_id = st.session_state.user_id
is_pro = get_user_plan(user_id) == "pro"

# ---------------- HEADER ----------------
st.markdown("""
<h1 style='text-align:center;'>📊 SheetHub</h1>
<p style='text-align:center; color:#94a3b8;'>
Smart Excel Cleaner — Clean, Analyze & Visualize in seconds 🚀
</p>
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
    st.sidebar.info("Free plan (5/day)")

# ---------------- USAGE ----------------
st.sidebar.markdown("## 📊 Daily Usage")

if is_pro:
    st.sidebar.success("Unlimited usage 🚀")
else:
    remaining = remaining_quota(user_id)
    used = FREE_DAILY_LIMIT - remaining
    progress = max(0.0, min(used / FREE_DAILY_LIMIT, 1.0))

    st.sidebar.progress(progress)
    st.sidebar.caption(f"{remaining} / {FREE_DAILY_LIMIT} files left today")

# ---------------- HISTORY ----------------
st.sidebar.markdown("## 🕓 Recent Files")
history = get_file_history(user_id)

if not history:
    st.sidebar.caption("No files yet")
else:
    for name, r, c, _ in history:
        st.sidebar.caption(f"{name} — {r}×{c}")

# ---------------- OPTIONS ----------------
st.sidebar.markdown("## 🧹 Cleaning Options")
apply_standardize = st.sidebar.checkbox("Standardize column names", True)
remove_summary = st.sidebar.checkbox("Remove summary rows", True)
remove_dupes = st.sidebar.checkbox("Remove duplicates (EmployeeID)", True)
drop_missing = st.sidebar.checkbox("Remove rows with missing values", False)

summary_keywords = st.sidebar.text_input(
    "Summary keywords",
    "total,subtotal,grand total,avg,average,sum"
).split(",")

# ---------------- PRO CTA ----------------
st.sidebar.markdown("---")
st.sidebar.markdown("## 🚀 PRO Coming Soon")
st.sidebar.caption("""
• Unlimited files  
• Faster processing  
• Priority features  
""")

# ---------------- LIMIT ----------------
if not is_pro and remaining_quota(user_id) <= 0:
    st.warning("🚫 Free limit reached (5/day). Come back tomorrow or upgrade soon.")
    st.stop()

# ---------------- UPLOAD ----------------
st.markdown("### 📂 Upload Excel files")

files = st.file_uploader(
    "",
    type=["xlsx"],
    accept_multiple_files=True,
)

if not is_pro:
    st.caption("🚀 Free: 5 files/day • PRO coming soon")

# ---------------- PIPELINE ----------------
any_success = False

if files:
    for file in files:
        if not is_pro and not can_use(user_id):
            st.error("🚫 Daily limit reached.")
            break

        file_bytes = file.read()

        try:
            raw_sheets = pd.read_excel(
                io.BytesIO(file_bytes),
                sheet_name=None,
                engine="openpyxl",
            )
            original_rows = {k: len(v) for k, v in raw_sheets.items()}
        except Exception:
            st.error("❌ Invalid Excel file.")
            continue

        try:
            cleaned = smart_clean_sheets_from_bytes(
                file_bytes,
                apply_standardize,
                remove_summary,
                summary_keywords,
                remove_dupes,
                None,
                drop_missing,
            )
        except Exception as e:
            st.error(str(e))
            continue

        any_success = True
        increment_usage(user_id)

        st.markdown("### 🧾 Cleaning Summary")
        for sheet, df in cleaned.items():
            removed = original_rows.get(sheet, 0) - len(df)
            st.write(
                f"• **{sheet}** → {len(df)} rows × {df.shape[1]} columns "
                f"(Removed {removed})"
            )
            save_file_history(user_id, file.name, len(df), df.shape[1])

        # AI INSIGHTS
        st.markdown("## 🤖 AI Insights")
        for sheet, df in cleaned.items():
            if not df.empty:
                with st.expander(f"Insights for {sheet}", expanded=True):
                    for insight in generate_ai_insights(df):
                        st.write("•", insight)

        # DOWNLOAD
        out = make_excel_bytes_from_sheets(cleaned)
        st.download_button(
            f"Download cleaned_{file.name}",
            out.getvalue(),
            f"cleaned_{file.name}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

if any_success:
    st.success("All files processed successfully ✅")
