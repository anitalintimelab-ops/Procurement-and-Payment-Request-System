import streamlit as st
import pandas as pd
import os
import base64

# --- 1. 系統大門設定 ---
st.set_page_config(page_title="時研-系統大門", layout="wide", page_icon="🏢")

st.markdown("""
<style>
.stApp { overflow-x: hidden; }
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
}
</style>
""", unsafe_allow_html=True)

B_DIR = os.path.dirname(os.path.abspath(__file__))
S_FILE = os.path.join(B_DIR, "staff_v2.csv")

def read_csv_robust(filepath):
    if not os.path.exists(filepath): 
        return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try:
            return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except Exception:
            continue
    return pd.DataFrame()

def load_staff():
    default_df = pd.DataFrame({
        "name": ["Andy", "Charles", "Eason", "Sunglin", "Anita"], 
        "status": ["在職"]*5, "password": ["0000"]*5, 
        "avatar": [""]*5, "line_uid": [""]*5 
    })
    df = read_csv_robust(S_FILE)
    if df is None or df.empty:
        df = default_df.copy()
        df.to_csv(S_FILE, index=False, encoding='utf-8-sig')
        return df
    if "status" not in df.columns: df["status"] = "在職"
    df["name"] = df["name"].str.strip()
    return df

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            if any(x in f.lower() for x in ["logo", "timelab"]) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                with open(os.path.join(B_DIR, f), "rb") as img:
                    return base64.b64encode(img.read()).decode()
    except Exception: pass
    return ""

# Session Init
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'user_status' not in st.session_state: st.session_state.user_status = "在職"

# --- 登入介面 ---
if st.session_state.user_id is None:
    logo_b64 = get_b64_logo()
    if logo_b64:
        st.markdown(f'<div style="text-align: center; margin-bottom: 30px;"><img src="data:image/png;base64,{logo_b64}" style="height: 100px; max-width: 100%;"></div>', unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>🏢 時研國際設計股份有限公司<br>管理系統入口</h1>", unsafe_allow_html=True)
    
    staff_df = load_staff()
    with st.form("login"):
        u = st.selectbox("身分", staff_df["name"].tolist())
        p = st.text_input("密碼", type="password")
        
        if st.form_submit_button("登入系統"):
            row = staff_df[staff_df["name"] == u].iloc[0]
            stored_p = str(row["password"]).strip().replace(".0", "")
            if str(p).strip() == stored_p or (str(p).strip() == "0000" and stored_p in ["nan", ""]):
                st.session_state.user_id = u
                st.session_state.user_status = row["status"] if pd.notna(row["status"]) else "在職"
                st.session_state.staff_df = staff_df
                st.rerun()
            else:
                st.error("密碼錯誤")
    st.stop()

# --- 登入成功大廳 ---
logo_b64 = get_b64_logo()
if logo_b64:
    st.markdown(f'<div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 20px;"><img src="data:image/png;base64,{logo_b64}" style="height: 60px;"></div>', unsafe_allow_html=True)

st.success(f"🎉 登入成功！歡迎回來，{st.session_state.user_id}。")
st.markdown("### 👈 請點擊畫面左邊的選單，進入對應的系統：")
st.markdown("- 📂 **1_採購單系統**\n- 📂 **2_請款單系統**\n- 📂 **3_報價單系統**")

st.divider()
if st.button("登出系統"):
    st.session_state.user_id = None
    st.rerun()
