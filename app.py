import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re
import time

# --- 1. 系統環境與權限定義 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"
STAFF_LIST = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- 2. 自動救援資料 (已更新欄位名稱) ---
def init_rescue_data():
    """如果不小心資料不見了，這個函式會自動把 1/21~1/29 的資料生出來"""
    if not os.path.exists(D_FILE):
        data = {
            "單號": ["20260121-01", "20260121-02", "20260129-03", "20260129-04", "20260129-05", "20260129-06"],
            "日期": ["2026-01-21", "2026-01-21", "2026-01-29", "2026-01-29", "2026-01-29", "2026-01-29"],
            "類型": ["請款單", "請款單", "請款單", "請款單", "請款單", "請款單"],
            "申請人": ["Anita", "Andy", "Charles", "Sunglin", "Eason", "Anita"],
            "專案負責人": ["Andy", "Andy", "Andy", "Andy", "Andy", "Andy"], # 已更名
            "專案名稱": ["20260120ST001", "10111111", "10111111", "10111111", "10111111", "元大方圓"],
            "專案編號": ["豪哥", "Test02", "2022222", "2022222", "2022222", "YUAN01"],
            "請款說明": ["測試說明1", "測試說明2", "2168", "2168", "2168", "工程款"],
            "總金額": ["5555", "555555", "555555", "555555", "555555", "500000"],
            "幣別": ["TWD"]*6,
            "付款方式": ["匯款(扣30手續費)"]*6,
            "請款廠商": ["廠商A", "廠商B", "20260", "20260", "20260", "元大"],
            "匯款帳戶": [""]*6, "帳戶影像Base64": [""]*6,
            "狀態": ["待初審", "已核准", "草稿", "草稿", "草稿", "待初審"],
            "影像Base64": [""]*6, 
            "提交時間": ["2026-01-21 10:00", "2026-01-21 11:00", "", "", "", "2026-01-29 15:57"],
            "申請人信箱": ["Anita", "Andy", "Charles", "Sunglin", "Eason", "Anita"],
            "初審人": ["", "Charles", "", "", "", ""],
            "初審時間": ["", "2026-01-21 14:00", "", "", "", ""],
            "複審人": ["", "Charles", "", "", "", ""],
            "複審時間": ["", "2026-01-21 15:00", "", "", "", ""],
            "刪除人": [""]*6, "刪除時間": [""]*6, "刪除原因": [""]*6
        }
        df = pd.DataFrame(data).astype(str)
        df.to_csv(D_FILE, index=False, encoding='utf-8-sig')

init_rescue_data()

# --- 3. 核心功能函式 ---
def validate_password(pw):
    has_letter = bool(re.search(r'[a-zA-Z]', pw))
    digit_count = len(re.findall(r'\d', pw))
    return has_letter and 4 <= digit_count <= 6

def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    encodings = ['utf-8-sig', 'utf-8', 'cp950', 'big5'] 
    for enc in encodings:
        try:
            df = pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
            return df
        except:
            continue
    return pd.DataFrame()

def load_data():
    # 更新欄位名稱：專案負責人
    cols = ["單號", "日期", "類型", "申請人", "專案負責人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱",
            "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", "刪除原因"]
    
    df = read_csv_robust(D_FILE)
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    
    # [關鍵] 自動資料遷移：如果舊檔案有 "專案執行人"，自動改成 "專案負責人"
    if "專案執行人" in df.columns:
        df = df.rename(columns={"專案執行人": "專案負責人"})
    
    for c in cols:
        if c not in df.columns: df[c] = ""
            
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    return df[cols]

def save_data(df):
    try:
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError:
        st.error("⚠️ 嚴重警告：無法寫入檔案！請檢查 `database.csv` 是否正由 Excel 開啟中。")
        st.stop()

def load_staff():
    default_df = pd.DataFrame({
        "name": STAFF_LIST,
        "status": ["在職"] * 5,
        "password": ["0000"] * 5
    })
    df = read_csv_robust(S_FILE)
    if df is None or df.empty or "password" not in df.columns:
        default_df.to_csv(S_FILE, index=False, encoding='utf-8-sig')
        return default_df
    
    df["name"] = df["name"].str.strip()
    df["password"] = df["password"].str.strip()
    return df

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

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

# 初始化 Session State
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()

if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None
if 'form_key' not in st.session_state: st.session_state.form_key = 0 

# --- 4. 登入識別 ---
if st.session_state.user_id is None:
    st
