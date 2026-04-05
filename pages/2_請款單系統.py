import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  
import json
import io
import threading

# --- 1. 系統鎖定與介面設定 ---
st.session_state['sys_choice'] = "請款單系統"
st.set_page_config(page_title="時研-請款單系統", layout="wide", page_icon="🏢")

# ==========================================
# 🎨 核心 CSS 魔法：終極解決文字空白與手機排版問題
# ==========================================
st.markdown("""
<style>
/* 隱藏預設導覽列與防止 x 軸溢出 */
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
.stApp { overflow-x: hidden; }

/* 整體背景漸變 */
.stApp {
    background: linear-gradient(180deg, #D9EAFB 0%, #EBDCF1 100%);
}

/* 側邊欄渐变和文字顏色 */
[data-testid="stSidebar"] {
    background: linear-gradient(135deg, #4A00E0 0%, #8E2DE2 100%), radial-gradient(circle at 70% 30%, rgba(255, 255, 255, 0.1) 0%, transparent 40%);
    background-blend-mode: overlay;
    color: white !important;
}
[data-testid="stSidebar"] * {
    color: white !important;
}

/* 側邊欄展開區塊 (Expander) 強制透明背景與白字 */
[data-testid="stSidebar"] details,
[data-testid="stSidebar"] details summary,
[data-testid="stSidebar"] div[data-testid="stExpanderDetails"] {
    background-color: transparent !important;
    background: transparent !important;
    border: none !important;
}
[data-testid="stSidebar"] details summary * {
    color: white !important;
}
[data-testid="stSidebar"] div[data-testid="stExpanderDetails"] p,
[data-testid="stSidebar"] div[data-testid="stExpanderDetails"] label,
[data-testid="stSidebar"] div[data-testid="stExpanderDetails"] span {
    color: white !important;
}
[data-testid="stSidebar"] [data-testid="stDataFrame"] * {
    color: black !important;
}

/* ★ 終極修正 1：所有上傳區塊 (Upload) 包含側邊欄與主頁，文字與圖示絕對強制黑色 */
div[data-testid="stFileUploader"] * {
    color: #000000 !important; 
    fill: #000000 !important;
}
div[data-testid="stFileUploader"] section {
    background-color: #ffffff !important; 
}
div[data-testid="stFileUploader"] button {
    background-color: #f0f2f6 !important;
    border: 1px solid #c0c4cc !important;
    color: #000000 !important;
}
div[data-testid="stFileUploader"] button * {
    color: #000000 !important;
    font-weight: bold !important;
}

/* 「目前系統」標籤，直接白字 */
[data-testid="stSidebar"] code {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    color: white !important;
    padding: 0 !important;
    font-size: 15px !important;
    box-shadow: none !important;
}

/* 側邊欄按鈕 (如：登出系統)，變成淺綠色，字體黑色 */
[data-testid="stSidebar"] .stButton > button {
    background-color: #9DC350 !important; 
    border: none !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] .stButton > button, 
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span,
[data-testid="stSidebar"] .stButton > button div,
[data-testid="stSidebar"] .stButton > button * {
    color: black !important;
    font-weight: 900 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #8bb340 !important; 
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.3) !important;
}

/* 側邊欄 Logo 文字 */
[data-testid="stSidebar"] .时研logo {
    color: white !important;
    font-size: 20px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 20px;
}
[data-testid="stSidebarNav"] ul li div:hover {
    background-color: rgba(0, 191, 255, 0.2);
}

/* 卡片與主要內容區域 */
[data-testid="stForm"], div.stExpander > div[role="button"], [data-testid="stDataFrame"] {
    background-color: rgba(240, 244, 248, 0.8) !important;
    backdrop-filter: blur(10px);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.2);
}
[data-testid="stForm"] *, div.stExpander * {
    color: #1E293B;
}

/* 縮小輸入框、下拉選單與按鈕 */
.stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stNumberInput input {
    border-radius: 8px !important;
    border: 1px solid #CBD5E1 !important;
    background-color: rgba(224, 231, 255, 0.5) !important;
    color: #1E293B !important;
    padding-top: 4px !important;
    padding-bottom: 4px !important;
    min-height: 32px !important;
    height: auto !important;
    transition: all 0.3s ease;
}
.stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
    background-color: #ffffff !important;
}

.stButton>button, .stFormSubmitButton>button, .stPopover>button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: 1px solid #3b82f6 !important;
    background-color: #ffffff !important;
    color: #00BFFF !important; 
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    padding: 4px 12px !important;
    min-height: 32px !important;  
    height: auto !important;
    line-height: 1.4 !important;
}
.stButton>button:hover, .stFormSubmitButton>button:hover, .stPopover>button:hover {
    background-color: rgba(0, 191, 255, 0.1) !important;
    border-color: #3b82f6 !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
    color: #00BFFF !important;
}

/* 手機版直式排版 */
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1rem !important; padding-left: 0.2rem !important; padding-right: 0.2rem !important; }
    div[data-testid="stHorizontalBlock"] { 
        display: flex !important;
        flex-direction: row !important; 
        flex-wrap: nowrap !important; 
        overflow-x: auto !important; 
        padding-bottom: 5px; 
        gap: 10px !important; 
        justify-content: flex-start !important; 
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { 
        flex: 0 0 max-content !important; 
        width: max-content !important; 
        min-width: max-content !important; 
        max-width: max-content !important;
        padding: 0 !important; 
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div { width: max-content !important; }
    div[data-testid="column"] p { font-size: 13px !important; white-space: nowrap !important; margin-bottom: 0 !important; }
    .stButton > button { padding: 2px 6px !important; font-size: 13px !important; min-height: 28px !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 側邊欄 Logo 文字 ---
st.sidebar.markdown("<h2 class='时研logo'>時研國際設計股份有限公司</h2>", unsafe_allow_html=True)

# --- 2. 路徑定位與 GitHub 金鑰設定 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) 
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 
G_FILE = os.path.join(B_DIR, "github_credentials.txt") 

P_FILE = os.path.join(B_DIR, "projects.csv")
V_FILE = os.path.join(B_DIR, "vendors.csv")

ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- GitHub 自動同步引擎 ---
def _background_github_sync(filepath):
    token, repo = "", ""
    if os.path.exists(G_FILE):
        try:
            with open(G_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                token = "".join(c for c in lines[0] if c.isascii()).strip() if len(lines)>0 else ""
                repo = "".join(c for c in lines[1] if c.isascii()).strip() if len(lines)>1 else ""
        except: pass

    if not token or not repo or not os.path.exists(filepath): 
        return
        
    try:
        filename = os.path.basename(filepath)
        url = f"https://api.github.com/repos/{repo}/contents/{filename}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        
        r = requests.get(url, headers=headers, timeout=5)
        sha = r.json().get("sha") if r.status_code == 200 else None
        
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode()
            
        data = {"message": f"Auto sync {filename} from TimeLab System", "content": content}
        if sha: data["sha"] = sha
        requests.put(url, headers=headers, json=data, timeout=10)
    except:
        pass 

def sync_to_github(filepath):
    threading.Thread(target=_background_github_sync, args=(filepath,), daemon=True).start()

# --- 3. 基礎工具 ---
def get_taiwan_time(): 
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return 0
    try: return int(float(str(val).replace(",", "").replace("$", "").replace(" ", "")))
    except: return 0

def clean_name(val): 
    return str(val).strip().split(" ")[0] if pd.notna(val) and str(val).strip() != "" else ""

def safe_str(val): 
    if pd.isna(val) or val is None: return ""
    s = str(val).strip()
    if s.lower() in ["nan", "none", ""]: return ""
    return s

def get_fallback_date(r):
    d = safe_str(r.get("日期")).replace("/", "-")
    if d: return d
    d = safe_str(r.get("單號"))[:8]
    if len(d) == 8 and d.isdigit():
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return "2026-03-18"

def get_online_users(curr_user):
    try:
        now = time.time()
        df = pd.read_csv(O_FILE) if os.path.exists(O_FILE) else pd.DataFrame(columns=["user", "time"])
        df = df[df["user"] != curr_user]
        df = pd.concat([df, pd.DataFrame([{"user": curr_user, "time": now}])], ignore_index=True)
        df = df[now - pd.to_numeric(df["time"], errors='coerce').fillna(0) <= 300]
        df.to_csv(O_FILE, index=False); return len(df["user"].unique())
    except: return 1

def get_line_credentials():
    if os.path.exists(L_FILE):
        try:
            with open(L_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                return lines[0].strip() if len(lines) > 0 else "", lines[1].strip() if len(lines) > 1 else ""
        except: pass
    return "", ""

def save_line_credentials(token, user_id):
    try:
        with open(L_FILE, "w", encoding="utf-8") as f: f.write(f"{token.strip()}\n{user_id.strip()}")
        sync_to_github(L_FILE)
    except: pass

def send_line_message(msg):
    token, _ = get_line_credentials()
    if token:
        try: requests.post("https://api.line.me/v2/bot/message/broadcast", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, json={"messages": [{"type": "text", "text": msg}]}, timeout=5)
        except: pass

def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try: return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except: continue
    return pd.DataFrame()

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "代申請人", "專案負責人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱", "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", "刪除原因", "駁回原因", "匯款狀態", "匯款日期", "支付條件", "支付期數", "請款狀態", "已請款金額", "尚未請款金額", "最後採購金額"]
    df = read_csv_robust(D_FILE)
    if df is None or df.empty: return pd.DataFrame(columns=cols)
    try:
        df.columns = [c.strip() for c in df.columns]
        if "專案執行人" in df.columns: df = df.rename(columns={"專案執行人": "專案負責人"})
        for c in cols:
            if
