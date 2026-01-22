import streamlit as st
import pandas as pd
import datetime
import os
import base64

# --- 1. 系統環境設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v5.csv") 

# 人員順序：Anita 排在 蔡松霖 之後
MANAGERS = ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita 林敬芸", "Wish 宋威績"]

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"]
    if os.path.exists(D_FILE):
        try:
            df = pd.read_csv(D_FILE).fillna("")
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: pass
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.reset_index(drop=True).to_csv(D_FILE, index=False)

def load_staff():
    if os.path.exists(S_FILE):
        try:
            df = pd.read_csv(S_FILE, dtype={'password': str}).fillna("在職")
            if "password" not in df.columns: df["password"] = "0000"
            return df.reset_index(drop=True)
        except: pass
    d = {"name": MANAGERS, "status": ["在職"] * len(MANAGERS), "password": ["0000"] * len(MANAGERS)}
    return pd.DataFrame(d)

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False)

def clean_for_js(h_str):
    return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# 初始化 session 狀態
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入識別 (密碼預設 0000) ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    
    sel_u = st.selectbox("我的身分：", u_list)
    if sel_u != "--- 請選擇 ---":
        input_pwd = st.text_input("輸入密碼 (預設 0000)：", type="password")
        if st.button("確認進入"):
            correct_pwd = st.session_state.staff_df[st.session_state.staff_df["name"] == sel_u]["password"].values[0]
            if input_pwd == str(correct_pwd):
                st.session_state.user_id = sel_u
                st.rerun()
            else:
                st.error("❌ 密碼錯誤，請再試一次。")
    st.stop()

curr_name = st.session_state.user_id
is_admin = ("Anita" in curr_name)

# --- 3. 側邊欄：個人密碼與管理員工具 ---
st.sidebar.markdown(f"### 👤 {curr_name}，您好")

with st.sidebar.expander("🔒 修改個人密碼"):
    new_p1 = st.text_input("輸入新密碼", type="password")
    new_p2 = st.text_input("確認新密碼", type="password")
    if st.button("確認修改"):
        if new_p1 and new_p1 ==
