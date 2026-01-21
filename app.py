import streamlit as st
import pandas as pd
import datetime
import os
import base64

# --- 1. 系統環境設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff.csv")

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"]
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
    df_s = ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita"]
    if os.path.exists(S_FILE):
        try:
            return pd.read_csv(S_FILE)["name"].tolist()
        except: pass
    return df_s

def save_staff(s_list):
    pd.DataFrame({"name": s_list}).to_csv(S_FILE, index=False)

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            fn = f.lower()
            if any(x in fn for x in [".jpg",".png",".jpeg"]):
                if "timelab" in fn or "logo" in fn:
                    p = os.path.join(B_DIR, f); im = open(p, "rb")
                    return base64.b64encode(im.read()).decode()
    except: pass
    return ""

def clean_for_js(h_str):
    return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff' not in st.session_state: st.session_state.staff = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入畫面邏輯 ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    st.info("請選取您的身分以進入系統")
    u_list = ["--- 請選擇 ---"] + st.session_state.staff
    sel_u = st.selectbox("我的身分：", u_list)
    if st.button("確認進入"):
        if sel_u != "--- 請選擇 ---":
            st.session_state.user_id = sel_u
            st.rerun()
    st.stop()

curr_name = st.session_state.user_id
is_admin = (curr_name == "Anita")

# --- 3. 側邊欄：顯示身分與管理工具 ---
st.sidebar.markdown("### 👤 目前登入：" + curr_name)
if is_admin:
    st.sidebar.success("系統權限：管理員")
    with st.sidebar.expander("⚙️ 管理工具：新增同事"):
        new_p = st.text_input("輸入新同事姓名")
        if st.button("➕ 確認新增"):
            if new_p and new_p not in st.session_state.staff:
                st.session_state.staff.append(new_p)
                save_staff(st.session_state.staff)
                st.rerun()
else:
    st.sidebar.info("
