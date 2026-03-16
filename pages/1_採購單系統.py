import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re
import time
import requests  
import json 

# --- 加入這行，將此分頁強制鎖定為採購單系統 ---
st.session_state['sys_choice'] = "採購單系統"

# --- 1. 系統設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide", page_icon="🏢")

# [手機版 RWD 響應式優化 CSS]
st.markdown("""
<style>
.stApp { overflow-x: hidden; }
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    table { word-wrap: break-word !important; font-size: 13px !important; }
    th, td { padding: 5px !important; }
}
</style>
""", unsafe_allow_html=True)

B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# [工具] 取得台灣時間
def get_taiwan_time():
    tw_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    return tw_time.strftime('%Y-%m-%d %H:%M')

# [工具] 金額清洗 (極度安全版)
def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": 
        return 0
    s_val = str(val).replace(",", "").replace("$", "").replace("，", "").replace(" ", "")
    try:
        return int(float(s_val))
    except Exception:
        return 0

# [工具] 名字清洗
def clean_name(val):
    if pd.isna(val) or val is None or str(val).strip() == "": 
        return ""
    return str(val).strip().split(" ")[0]

# [工具] 跳轉至修改頁面
def navigate_to_edit(eid):
    st.session_state.edit_id = eid
    st.session_state.menu_radio = "1. 填寫申請單"

# [工具] 追蹤在線人數
def get_online_users(curr_user):
    try:
        if not curr_user: 
            return 1
        now = time.time()
        df = pd.DataFrame(columns=["user", "time"])
        if os.path.exists(O_FILE):
            try: 
                df = pd.read_csv(O_FILE)
            except Exception: 
                pass
            
        if "user" not in df.columns or "time" not in df.columns:
            df = pd.DataFrame(columns=["user", "time"])
            
        df = df[df["user"] != curr_user]
        df = pd.concat([df, pd.DataFrame([{"user": curr_user, "time": now}])], ignore_index=True)
        df["time"] = pd.to_numeric(df["time"], errors='coerce').fillna(now)
        df = df[now - df["time"] <= 300]
        
        try: 
            df.to_csv(O_FILE, index=False)
        except Exception: 
            pass
        return len(df["user"].unique())
    except Exception:
        return 1

# [更新工具] LINE 精準群發推播功能
def get_line_credentials():
    if os.path.exists(L_FILE):
        try:
            with open(L_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                t = lines[0].strip() if len(lines) > 0 else ""
                u = lines[1].strip() if len(lines) > 1 else ""
                return t, u
        except Exception: 
            pass
    return "", ""

def save_line_credentials(token, user_id):
    try:
        with open(L_FILE, "w", encoding="utf-8") as f:
            f.write(f"{token.strip()}\n{user_id.strip()}")
    except Exception: 
        pass

# 全面改用 LINE 官方群發 (Broadcast) 機制
def send_line_message(msg, target_name=""):
    token, _ = get_line_credentials()
    if not token: 
        return  
    
    url = "https://api.line
