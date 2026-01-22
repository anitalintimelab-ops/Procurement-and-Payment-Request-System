import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import os
import base64

st.set_page_config(page_title="時研-管理系統", layout="wide")

# 1. 建立連線並強制停用快取
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 定義核心讀取函數
def load_data():
    try:
        # 使用 ttl=0 強制每次都從雲端抓最新的，避免 400 錯誤被快取
        df = conn.read(worksheet="database", ttl=0).fillna("")
        return df
    except Exception as e:
        st.error(f"❌ database 分頁讀取失敗。請檢查試算表內是否有 'database' 這個標籤。錯誤：{e}")
        return pd.DataFrame(columns=["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"])

def load_staff():
    try:
        df = conn.read(worksheet="staff", ttl=0).fillna("在職").reset_index(drop=True)
        return df
    except Exception as e:
        st.warning(f"⚠️ staff 人員清單讀取失敗。目前使用緊急備用名單。")
        return pd.DataFrame({"name": ["Anita 林敬芸", "Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Wish 宋威績"], "status": ["在職"]*6})

# 3. 初始化資料庫
st.session_state.db = load_data()
st.session_state.staff_df = load_staff()

# --- 這裡接您原本所有的 HTML 拼接、表單、簽核中心與列印功能程式碼 ---
# 請確保維持原本的功能細項不變
