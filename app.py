import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import os
import base64

# --- 1. 系統環境設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")

# 建立連線並強制停用快取
conn = st.connection("gsheets", type=GSheetsConnection)

# 定義簽核名單
MANAGERS = ["Anita 林敬芸", "Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Wish 宋威績"]

def load_data():
    try:
        # 強制 ttl=0 清除快取，徹底解決 400 報錯
        df = conn.read(worksheet="database", ttl=0).fillna("")
        return df
    except Exception as e:
        st.error(f"❌ database 分頁讀取失敗。請確認分頁名稱是否為 database (全小寫)。錯誤：{e}")
        # 如果讀取失敗，返回空表以防當機
        cols = ["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"]
        return pd.DataFrame(columns=cols)

def load_staff():
    try:
        # 讀取人員清單
        df = conn.read(worksheet="staff", ttl=0).fillna("在職").reset_index(drop=True)
        return df
    except Exception as e:
        st.warning(f"⚠️ staff 人員分頁連線中... 目前使用緊急備著名單。")
        # 備用名單包含林敬芸與宋威績
        d = {"name": ["Anita 林敬芸", "Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Wish 宋威績"], "status": ["在職"] * 6}
        return pd.DataFrame(d)

# 初始化資料
st.session_state.db = load_data()
st.session_state.staff_df = load_staff()

# 登入識別
if st.session_state.get('user_id') is None:
    st.header("🏢 時研國際 - 內部管理系統 (雲端同步版)")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    sel_u = st.selectbox("我的身分：", u_list)
    if st.button("確認進入"):
        if sel_u != "--- 請選擇 ---":
            st.session_state.user_id = sel_u
            st.rerun()
    st.stop()

# ... (其餘 HTML 與表單邏輯維持不變) ...
