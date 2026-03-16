import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  
import json 

# --- A. 系統身分鎖定 ---
st.session_state['sys_choice'] = "請款單系統"

# --- B. 介面設定 ---
st.set_page_config(page_title="時研-請款單系統", layout="wide", page_icon="🏢")

# [CSS] 隱藏左側選單中的 "app" 項目
st.markdown("""
<style>
    [data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
    .stApp { overflow-x: hidden; }
</style>
""", unsafe_allow_html=True)

# --- C. 路徑修正邏輯 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) 
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

# [以下邏輯與請款單完全一致，但 sys_choice 已鎖定]
# ... 基礎工具函式 (與採購單同) ...

def get_filtered_db():
    db = load_data()
    return db[db["類型"].isin(["請款單", "請購單"])]

# --- F. 側邊欄與登出 ---
st.sidebar.markdown(f"### 👤 {st.session_state.user_id}")
st.sidebar.info(f"📌 目前系統：`請款單系統`")

if st.sidebar.button("登出系統"):
    st.session_state.user_id = None
    st.switch_page("app.py")
