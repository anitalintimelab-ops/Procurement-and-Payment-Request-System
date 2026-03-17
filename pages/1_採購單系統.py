import streamlit as st
import pandas as pd
import datetime
import os
import base64
import requests  
import time

# --- A. 系統身分鎖定 ---
st.session_state['sys_choice'] = "採購單系統"

# --- B. 介面設定 ---
st.set_page_config(page_title="時研-採購單系統", layout="wide", page_icon="🏢")

# [CSS] 隱藏左側 "app" 並優化 RWD
st.markdown("""
<style>
    [data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
    .stApp { overflow-x: hidden; }
    @media screen and (max-width: 768px) {
        .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- C. 路徑定位 (穿透至根目錄) ---
B_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"

# --- D. 核心工具 (原封不動移植) ---
def get_taiwan_time():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return 0
    s_val = str(val).replace(",", "").replace("$", "").replace("，", "").replace(" ", "")
    try: return int(float(s_val))
    except: return 0

def clean_name(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return ""
    return str(val).strip().split(" ")[0]

def send_line_message(msg):
    if os.path.exists(L_FILE):
        try:
            with open(L_FILE, "r", encoding="utf-8") as f:
                token = f.read().splitlines()[0].strip()
                url = "https://api.line.me/v2/bot/message/broadcast"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
                requests.post(url, headers=headers, json={"messages": [{"type": "text", "text": msg}]}, timeout=5)
        except: pass

def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950']:
        try: return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except: continue
    return pd.DataFrame()

def load_data():
    df = read_csv_robust(D_FILE)
    if df is None or df.empty: return pd.DataFrame()
    for col in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]:
        if col in df.columns: df[col] = df[col].apply(clean_amount)
    return df

def save_data(df):
    df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            if any(x in f.lower() for x in ["logo", "timelab"]) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                with open(os.path.join(B_DIR, f), "rb") as img: return base64.b64encode(img.read()).decode()
    except: pass
    return ""

def render_header():
    logo_b64 = get_b64_logo()
    if logo_b64:
        st.markdown(f'<div style="display:flex;align-items:center;justify-content:center;gap:15px;"><img src="data:image/png;base64,{logo_b64}" style="height:60px;"><h2>時研國際設計股份有限公司</h2></div>', unsafe_allow_html=True)
    else: st.title("時研國際設計股份有限公司")
    st.divider()

# --- E. 登入檢查與側邊欄 ---
if 'user_id' not in st.session_state or st.session_state.user_id is None:
    st.warning("⚠️ 請先回首頁登入")
    st.stop()

curr_name = st.session_state.user_id
is_admin = (curr_name in ADMINS)

st.sidebar.markdown(f"### 👤 {curr_name}")
st.sidebar.info("📌 目前系統：採購單系統")

if st.sidebar.button("登出系統"):
    st.session_state.user_id = None
    st.switch_page("app.py")

menu = st.sidebar.radio("導覽", ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽", "5. 系統設定"])

# --- F. 功能邏輯 (採購專用) ---
db = load_data()

if menu == "1. 填寫申請單":
    render_header()
    st.subheader("📝 填寫採購申請單")
    staffs = read_csv_robust(S_FILE)["name"].tolist() if os.path.exists(S_FILE) else ["Anita"]
    
    with st.form("po_form"):
        c1, c2 = st.columns(2)
        pn = c1.text_input("專案名稱")
        exe = c1.selectbox("負責執行長", staffs)
        pi = c2.text_input("專案編號")
        amt = c2.number_input("預計採購金額", min_value=0)
        desc = st.text_area("說明")
        f_ims = st.file_uploader("上傳憑證", accept_multiple_files=True)
        if st.form_submit_button("💾 儲存申請"):
            if pn and pi and amt > 0:
                tid = f"PO{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
                nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"採購單", "申請人":curr_name, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "總金額":amt, "請款說明":desc, "狀態":"已儲存"}
                db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                save_data(db)
                st.success(f"已儲存！單號：{tid}")
                st.rerun()

elif menu == "4. 表單狀態總覽":
    render_header()
    st.dataframe(db[db["類型"] == "採購單"], use_container_width=True)

elif menu == "5. 系統設定":
    render_header()
    st.subheader("⚙️ 資料還原")
    up = st.file_uploader("上傳備份 CSV")
    if up and st.button("確認還原"):
        with open(D_FILE, "wb") as f: f.write(up.getbuffer())
        st.success("資料已還原！")
        st.rerun()
