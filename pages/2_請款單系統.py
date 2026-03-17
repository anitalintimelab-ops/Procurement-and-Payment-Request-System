import streamlit as st
import pandas as pd
import datetime
import os
import base64
import requests  

# --- A. 系統身分鎖定 ---
st.session_state['sys_choice'] = "請款單系統"

# --- B. 介面設定 ---
st.set_page_config(page_title="時研-請款單系統", layout="wide", page_icon="🏢")

# [CSS] 隱藏左側 "app"
st.markdown("<style>[data-testid='stSidebarNav'] ul li:nth-child(1) { display: none !important; }</style>", unsafe_allow_html=True)

# --- C. 路徑定位 ---
B_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")

def load_data():
    if os.path.exists(D_FILE):
        return pd.read_csv(D_FILE, encoding='utf-8-sig', dtype=str).fillna("")
    return pd.DataFrame()

def save_data(df):
    df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')

# --- D. 登入檢查 ---
if 'user_id' not in st.session_state or st.session_state.user_id is None:
    st.warning("⚠️ 請先回首頁登入")
    st.stop()

st.sidebar.markdown(f"### 👤 {st.session_state.user_id}")
if st.sidebar.button("登出系統"):
    st.session_state.user_id = None
    st.switch_page("app.py")

menu = st.sidebar.radio("導覽", ["1. 填寫請款單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 請款狀態總覽"])

# --- E. 請款邏輯 ---
if menu == "1. 填寫請款單":
    st.title("💰 請款申請")
    db = load_data()
    with st.form("claim"):
        pn = st.text_input("專案名稱")
        vdr = st.text_input("請款廠商")
        amt = st.number_input("金額", min_value=0)
        if st.form_submit_button("送出申請"):
            if pn and amt > 0:
                nr = {"單號": datetime.datetime.now().strftime('%Y%m%d%H%M'), "類型":"請款單", "申請人":st.session_state.user_id, "專案名稱":pn, "請款廠商":vdr, "總金額":amt, "狀態":"待簽核"}
                db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                save_data(db)
                st.success("申請成功！")
                st.rerun()

elif menu == "4. 請款狀態總覽":
    db = load_data()
    st.dataframe(db[db["類型"] == "請款單"], use_container_width=True)
