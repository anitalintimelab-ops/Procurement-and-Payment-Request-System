import streamlit as st
import pandas as pd
import datetime
import os
import base64
import requests  
import time

# --- A. 系統身分與介面設定 ---
st.session_state['sys_choice'] = "採購單系統"
st.set_page_config(page_title="時研-採購單系統", layout="wide", page_icon="🏢")

# [CSS] 隱藏左側選單的 "app" 項目，並優化手機版介面
st.markdown("""
<style>
    [data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
    .stApp { overflow-x: hidden; }
    @media screen and (max-width: 768px) {
        .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- B. 路徑修正：穿透資料夾定位至根目錄 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) # 取得 pages 的上一層 (根目錄)

D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"

# --- C. 基礎工具函式 ---
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

# --- D. 資料讀取與處理 ---
def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950']:
        try: return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except: continue
    return pd.DataFrame()

def load_data():
    df = read_csv_robust(D_FILE)
    if df is None or df.empty: return pd.DataFrame()
    if "專案執行人" in df.columns: df = df.rename(columns={"專案執行人": "專案負責人"})
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

# --- E. 驗證登入與初始化 ---
if 'user_id' not in st.session_state or st.session_state.user_id is None:
    st.warning("⚠️ 請先回首頁登入")
    st.stop()

if 'view_id' not in st.session_state: st.session_state.view_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None

curr_name = st.session_state.user_id
is_admin = (curr_name in ADMINS)

# --- F. 側邊欄與導覽 ---
st.sidebar.markdown(f"### 👤 使用者：{curr_name}")
st.sidebar.info("📌 目前進入：採購單系統")

if st.sidebar.button("登出系統"):
    st.session_state.user_id = None
    st.switch_page("app.py")

menu = st.sidebar.radio("導覽", ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽", "5. 系統設定"])

# --- G. 採購單核心邏輯 (完整復原) ---
def get_filtered_db():
    db = load_data()
    if db.empty: return db
    return db[db["類型"] == "採購單"]

if menu == "1. 填寫申請單":
    render_header()
    st.subheader("📝 填寫採購申請單")
    
    db = load_data()
    staff_df = read_csv_robust(S_FILE)
    staffs = staff_df["name"].tolist() if not staff_df.empty else ["Anita", "Andy"]

    with st.form("po_form"):
        c1, c2 = st.columns(2)
        pn = c1.text_input("專案名稱")
        exe = c1.selectbox("負責執行長", staffs)
        pi = c2.text_input("專案編號")
        amt = c2.number_input("預計採購金額", min_value=0)
        desc = st.text_area("說明")
        f_ims = st.file_uploader("上傳報價單/憑證", accept_multiple_files=True)
        
        if st.form_submit_button("💾 儲存並產生單號"):
            if pn and pi and amt > 0:
                today = datetime.date.today().strftime('%Y%m%d')
                count = len(db[db['單號'].str.startswith(today)]) if not db.empty else 0
                tid = f"{today}-{count+1:02d}"
                b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else ""
                
                nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"採購單", "申請人":curr_name, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "總金額":amt, "請款說明":desc, "影像Base64":b_ims, "狀態":"已儲存", "提交時間":""}
                db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                save_data(db)
                st.session_state.last_id = tid
                st.success(f"已儲存！單號為：{tid}")
                st.rerun()

    if st.session_state.last_id:
        if st.button("🚀 正式提交申請 (送出簽核)"):
            fresh_db = load_data()
            idx = fresh_db[fresh_db["單號"]==st.session_state.last_id].index[0]
            fresh_db.at[idx, "狀態"] = "待簽核"
            fresh_db.at[idx, "提交時間"] = get_taiwan_time()
            save_data(fresh_db)
            send_line_message(f"🔔【採購單待簽核】\n單號：{st.session_state.last_id}\n有一筆新採購單需執行長簽核。")
            st.session_state.last_id = None
            st.success("申請已提交！")
            st.rerun()

    st.divider()
    st.subheader("📋 我的採購申請紀錄")
    my_po = get_filtered_db()
    if not my_po.empty:
        if not is_admin: my_po = my_po[my_po["申請人"] == curr_name]
        st.dataframe(my_po[["單號", "日期", "專案名稱", "總金額", "狀態"]], use_container_width=True)

elif menu == "2. 專案執行長簽核":
    render_header()
    st.subheader("🔍 採購單審核區")
    db = get_filtered_db()
    p_df = db[(db["狀態"] == "待簽核") & (db["專案負責人"] == curr_name)]
    if p_df.empty: st.info("目前無待簽核單據")
    else:
        for i, r in p_df.iterrows():
            with st.expander(f"單號：{r['單號']} - {r['專案名稱']}"):
                st.write(f"金額：{r['總金額']:,} | 說明：{r['請款說明']}")
                if st.button("✅ 核准", key=f"ok_{i}"):
                    fresh_db = load_data()
                    idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    fresh_db.at[idx, "狀態"] = "已核准"
                    save_data(fresh_db)
                    st.rerun()

elif menu == "5. 系統設定":
    render_header()
    st.subheader("⚙️ 系統管理與備份還原")
    if os.path.exists(D_FILE):
        with open(D_FILE, "rb") as f:
            st.download_button("⬇️ 下載資料庫備份", f, file_name="時研資料備份.csv")
    up_db = st.file_uploader("⬆️ 上傳備份還原")
    if up_db and st.button("確認還原"):
        with open(D_FILE, "wb") as f: f.write(up_db.getbuffer())
        st.success("還原成功！")
        st.rerun()
