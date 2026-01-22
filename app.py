import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import os
import base64

st.set_page_config(page_title="時研-管理系統", layout="wide")

# 建立連線
conn = st.connection("gsheets", type=GSheetsConnection)

MANAGERS = ["Anita", "Anita 林敬芸", "Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Wish 宋威績"]

def load_data():
    try:
        # 強制讀取 database 工作表
        df = conn.read(worksheet="database", ttl=0).fillna("")
        return df
    except Exception as e:
        st.error(f"❌ 無法讀取 database 分頁，請檢查名稱是否有多餘空格。錯誤：{e}")
        return pd.DataFrame(columns=["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"])

def load_staff():
    try:
        # 強制讀取 staff 工作表
        df = conn.read(worksheet="staff", ttl=0).fillna("在職").reset_index(drop=True)
        return df
    except Exception as e:
        st.warning(f"⚠️ 無法讀取 staff 人員分頁，請檢查分頁名稱。目前使用內建名單。")
        d = {"name": ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita 林敬芸"], "status": ["在職"] * 5}
        return pd.DataFrame(d)

# --- 保留您原本所有的 HTML 拼接與功能邏輯，此處省略以節省長度，請維持與之前版本一致 ---

# 初始化資料
st.session_state.db = load_data()
st.session_state.staff_df = load_staff()

# 登入邏輯修正：支援「Anita 林敬芸」
if st.session_state.get('user_id') is None:
    st.header("🏢 時研國際 - 內部管理系統")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    sel_u = st.selectbox("我的身分：", u_list)
    if st.button("確認進入"):
        if sel_u != "--- 請選擇 ---":
            st.session_state.user_id = sel_u
            st.rerun()
    st.stop()

curr_name = st.session_state.user_id
is_admin = ("Anita" in curr_name) # 確保包含林敬芸版本
