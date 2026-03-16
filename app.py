import streamlit as st
import pandas as pd
import os
import base64

# --- 1. 系統大門設定 ---
st.set_page_config(page_title="時研-系統入口", layout="wide", page_icon="🏢", initial_sidebar_state="collapsed")

# [隱藏側邊欄 CSS]
if st.session_state.get("user_id") is None:
    st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        [data-testid="stSidebar"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 強制定位到根目錄
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

# --- 登入介面 ---
if st.session_state.user_id is None:
    logo_b64 = get_b64_logo()
    if logo_b64:
        st.markdown(f'<div style="text-align: center; margin-bottom: 30px;"><img src="data:image/png;base64,{logo_b64}" style="height: 100px;"></div>', unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>🏢 時研國際設計股份有限公司<br>管理系統入口</h1>", unsafe_allow_html=True)
    
    staff_df = load_staff()
    
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        with st.form("login_form"):
            u = st.selectbox("身分", staff_df["name"].tolist())
            p = st.text_input("密密碼", type="password")
            target_sys = st.selectbox("進入系統", ["1_採購單系統", "2_請款單系統", "3_報價單系統"])
            
            if st.form_submit_button("登入系統", use_container_width=True):
                # 登入前重新讀取最新檔案
                current_staff = load_staff()
                row = current_staff[current_staff["name"] == u].iloc[0]
                stored_p = str(row["password"]).strip().replace(".0", "")
                
                if str(p).strip() == stored_p or (str(p).strip() == "0000" and stored_p in ["nan", ""]):
                    st.session_state.user_id = u
                    st.session_state.user_status = row["status"] if pd.notna(row["status"]) else "在職"
                    st.switch_page(f"pages/{target_sys}.py")
                else:
                    st.error("密碼錯誤")
    st.stop()

st.title(f"🎉 您已登入為：{st.session_state.user_id}")
if st.button("登出系統"):
    st.session_state.user_id = None
    st.rerun()
