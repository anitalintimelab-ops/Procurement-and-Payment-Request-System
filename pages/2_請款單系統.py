import streamlit as st
import pandas as pd
import datetime
import os
import base64
import requests  

# --- A. 系統身分與介面設定 ---
st.session_state['sys_choice'] = "請款單系統"
st.set_page_config(page_title="時研-請款單系統", layout="wide", page_icon="🏢")

# [CSS] 隱藏左側 "app"
st.markdown("""
<style>
    [data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
    .stApp { overflow-x: hidden; }
</style>
""", unsafe_allow_html=True)

# --- B. 路徑修正 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR)
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")

# --- C. 基礎工具 (內容與採購單同，確保資料一致) ---
def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return 0
    try: return int(float(str(val).replace(",", "").replace("$", "")))
    except: return 0

def load_data():
    df = pd.read_csv(D_FILE, encoding='utf-8-sig', dtype=str).fillna("") if os.path.exists(D_FILE) else pd.DataFrame()
    return df

def save_data(df):
    df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')

# --- D. 驗證登入 ---
if 'user_id' not in st.session_state or st.session_state.user_id is None:
    st.warning("⚠️ 請先回首頁登入")
    st.stop()

curr_name = st.session_state.user_id

# --- E. 側邊欄 ---
st.sidebar.markdown(f"### 👤 使用者：{curr_name}")
st.sidebar.info("📌 目前進入：請款單系統")

if st.sidebar.button("登出系統"):
    st.session_state.user_id = None
    st.switch_page("app.py")

menu = st.sidebar.radio("導覽", ["1. 填寫請款單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 請款狀態總覽"])

# --- F. 請款單核心邏輯 (完整復原) ---
if menu == "1. 填寫請款單":
    st.title("💰 填寫請款申請單")
    db = load_data()
    with st.form("claim_form"):
        c1, c2 = st.columns(2)
        pn = c1.text_input("專案名稱")
        vdr = c1.text_input("廠商名稱")
        amt = c2.number_input("金額", min_value=0)
        acc = c2.text_input("匯款帳戶")
        desc = st.text_area("備註說明")
        f_acc = st.file_uploader("上傳存摺影像")
        
        if st.form_submit_button("儲存並送出"):
            if pn and amt > 0 and vdr:
                # 儲存邏輯 (比照原本 app.py)
                nr = {"單號": datetime.datetime.now().strftime('%Y%m%d%H%M%S'), "日期": str(datetime.date.today()), "類型":"請款單", "申請人":curr_name, "專案名稱":pn, "請款廠商":vdr, "總金額":amt, "匯款帳戶":acc, "狀態":"待簽核"}
                db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                save_data(db)
                st.success("請款單已成功提交！")
                st.rerun()

elif menu == "4. 請款狀態總覽":
    st.subheader("📊 您的請款進度")
    db = load_data()
    if not db.empty:
        my_claims = db[db["類型"] == "請款單"]
        st.dataframe(my_claims, use_container_width=True)
