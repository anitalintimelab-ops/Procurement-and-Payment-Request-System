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
st.session_state['sys_choice'] = "體驗會測試系統" 
st.set_page_config(page_title="時研-體驗測試版", layout="wide", page_icon="🏢")

# ==========================================
# 🎨 核心 CSS 魔法：系統介面純淨美化升級
# ==========================================
st.markdown("""
<style>
/* 測試版專用：隱藏正式區選單 */
[data-testid="stSidebarNav"] ul li a[href*="1_"] { display: none !important; }
[data-testid="stSidebarNav"] ul li a[href*="2_"] { display: none !important; }
[data-testid="stSidebarNav"] ul li a[href*="3_"] { display: none !important; }

/* 隱藏預設導覽列與防止 x 軸溢出 */
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
.stApp { overflow-x: hidden; }

/* 整體背景漸變 */
.stApp {
    background: linear-gradient(180deg, #FFF3E0 0%, #FFE0B2 100%);
}

/* 側邊欄渐變和文字顏色 */
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

/* 確保上傳拖曳區的背景是白色的，文字是黑色的 */
div[data-testid="stFileUploader"] section { background-color: #ffffff !important; border: 2px dashed #cbd5e1 !important; }
div[data-testid="stFileUploader"] label, div[data-testid="stFileUploadDropzone"] p, div[data-testid="stFileUploadDropzone"] span, div[data-testid="stFileUploadDropzone"] small { color: #1E293B !important; }
div[data-testid="stFileUploadDropzone"] > div > svg { fill: #64748B !important; }

/* 1. 殺掉所有深色背景！讓黑黑一坨徹底消失！ */
div[data-testid="stUploadedFile"], 
div[data-testid="stUploadedFile"] * {
    background-color: transparent !important;
    background: transparent !important;
}

/* 2. 隱藏 Streamlit 原廠醜醜的圖示 */
div[data-testid="stUploadedFile"] svg {
    display: none !important;
}

/* 3. 強制將圖示容器替換成微軟 Excel 的彩色 SVG 向量圖形 */
div[data-testid="stUploadedFile"] > div > div:first-child {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath fill='%23185C37' d='M21,14L7,16v15l14,2V14z'/%3E%3Cpath fill='%2321A366' d='M21,14v19l20-2V16L21,14z'/%3E%3Cpath fill='%23107C41' d='M41,48H7c-2.2,0-4-1.8-4-4V4c0-2.2,1.8-4,4-4h34c2.2,0,4,1.8,4,4v40C45,46.2,43.2,48,41,48z'/%3E%3Cpath fill='%2333C481' d='M41,16H21v17h20V16z'/%3E%3Cpath fill='%23FFFFFF' d='M36.2,27.1l-3.3-5.2h-3l2.2,3.8c0.1,0.2,0.2,0.4,0.2,0.6c0,0.1-0.1,0.3-0.2,0.6l-2.4,4.2h3.1l2-3.6 c0.1-0.2,0.2-0.3,0.3-0.5c0.1,0.2,0.2,0.4,0.3,0.5l2.1,3.6h2.9l-3.5-5.3l3.2-4.9h-3L36.2,27.1z'/%3E%3C/svg%3E") !important;
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
}

/* 4. 恢復右邊的刪除按鈕 (X) 的顯示，並變成紅色 */
div[data-testid="stUploadedFile"] button svg {
    display: block !important;
    fill: #ef4444 !important; /* 紅色更顯眼 */
    width: 18px !important;
    height: 18px !important;
}

/* 5. 確保檔名與大小的文字是深色清晰的 */
div[data-testid="stUploadedFile"] div[data-testid="stText"],
div[data-testid="stUploadedFile"] p,
div[data-testid="stUploadedFile"] span,
div[data-testid="stUploadedFile"] small {
    color: #1E293B !important;
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
.stTextInput div[data-baseweb="input"], .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stNumberInput div[data-baseweb="input"] {
    border-radius: 8px !important;
    border: 1px solid #CBD5E1 !important;
    background-color: rgba(224, 231, 255, 0.5) !important;
    transition: all 0.3s ease;
    overflow: hidden !important;
}
.stTextInput input, .stNumberInput input {
    background-color: transparent !important;
    color: #1E293B !important;
    padding-top: 4px !important;
    padding-bottom: 4px !important;
    min-height: 32px !important;
    height: auto !important;
    border: none !important;
}
.stSelectbox div[data-baseweb="select"], .stTextArea textarea {
    color: #1E293B !important;
    padding-top: 4px !important;
    padding-bottom: 4px !important;
    min-height: 32px !important;
    height: auto !important;
}
.stTextInput div[data-baseweb="input"]:focus-within, .stSelectbox div[data-baseweb="select"]:focus-within, .stTextArea textarea:focus, .stNumberInput div[data-baseweb="input"]:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
    background-color: #ffffff !important;
}
.stTextInput div[data-baseweb="input"] div {
    background-color: transparent !important;
}

/* 側邊欄輸入框與下拉選單強制黑字與黑色箭頭 */
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] *,
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox svg {
    color: #1E293B !important;
    fill: #1E293B !important;
}
div[data-baseweb="popover"] ul[data-testid="stSelectboxVirtualDropdown"] li {
    color: #1E293B !important;
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

/* 手機版直式排版拒絕拉伸 */
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1rem !important; padding-left: 0.2rem !important; padding-right: 0.2rem !important; }
    div[data-testid="stHorizontalBlock"] { 
        display: flex !important;
        flex-direction: row !important; 
        flex-wrap: nowrap !important; 
        overflow-x: auto !important; 
        padding-bottom: 5px; 
        gap: 6px !important; 
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

.mobile-camera-only { display: none !important; }
@media screen and (max-width: 768px) {
    .mobile-camera-only {
        display: flex !important; align-items: center !important; justify-content: center !important; margin-top: 28px !important;
    }
    .mobile-camera-only [data-testid="stPopover"] { display: block !important; }
    .mobile-camera-only [data-testid="stPopover"] > button {
        width: 48px !important; height: 48px !important; border-radius: 12px !important; padding: 0 !important; border: 2px solid #cbd5e1 !important; background-color: #f8fafc !important; display: flex !important; align-items: center !important; justify-content: center !important; box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
    }
    .mobile-camera-only [data-testid="stPopover"] > button p { font-size: 24px !important; margin: 0 !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 側邊欄 Logo 文字 ---
st.sidebar.markdown("<h2 class='时研logo'>時研國際設計股份有限公司</h2>", unsafe_allow_html=True)

# =========================================================================
# ★ 核心改動：讀取的資料庫檔案全面加上 "demo_" 前綴，建立平行的「體驗會宇宙」 ★
# =========================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) 
D_FILE = os.path.join(B_DIR, "demo_database.csv")
S_FILE = os.path.join(B_DIR, "demo_staff.csv")
O_FILE = os.path.join(B_DIR, "demo_online.csv")
L_FILE = os.path.join(B_DIR, "demo_line_credentials.txt") 
G_FILE = os.path.join(B_DIR, "demo_github_credentials.txt") 

P_FILE = os.path.join(B_DIR, "demo_projects.csv")
V_FILE = os.path.join(B_DIR, "demo_vendors.csv")

ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- GitHub 自動同步引擎 (Base64 防攔截版) ---
def _background_github_sync(filepath):
    token, repo = "", ""
    if os.path.exists(G_FILE):
        try:
            with open(G_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                raw_t = "".join(c for c in lines[0] if c.isascii()).strip() if len(lines)>0 else ""
                repo = "".join(c for c in lines[1] if c.isascii()).strip() if len(lines)>1 else ""
                if raw_t.startswith("ghp_"): token = raw_t
                else:
                    try: token = base64.b64decode(raw_t).decode()
                    except: token = raw_t
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
            
        data = {"message": f"Auto sync {filename} from TimeLab System (DEMO)", "content": content}
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
            if c not in df.columns: df[c] = ""
        for c in ["總金額", "已請款金額", "尚未請款金額"]:
            df[c] = df[c].apply(clean_amount)
            
        # 廣泛性修復：若不小心將 LINE 通知文字貼到狀態欄
        if "狀態" in df.columns:
            df.loc[df["狀態"].astype(str).str.contains("需要財務長", na=False), "狀態"] = "待複審"
            df.loc[df["狀態"].astype(str).str.contains("需要執行長", na=False), "狀態"] = "待簽核"

        return df[cols]
    except:
        return pd.DataFrame(columns=cols)

def save_data(df):
    try: 
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
        sync_to_github(D_FILE) 
    except: st.error("⚠️ 檔案鎖定中！請關閉電腦上的 CSV。"); st.stop()

def load_staff():
    df = read_csv_robust(S_FILE)
    default_roles = {"Andy": "執行長", "Charles": "執行長&財務長", "Eason": "執行長", "Sunglin": "執行長", "Anita": "管理員"}
    
    if df is None or df.empty: 
        return pd.DataFrame({
            "name": DEFAULT_STAFF, 
            "status": ["在職"]*5, 
            "password": ["0000"]*5,
            "role": [default_roles.get(n, "使用者") for n in DEFAULT_STAFF],
            "line_uid": [""]*5
        })
    
    if "role" not in df.columns: df["role"] = df["name"].apply(lambda x: default_roles.get(x, "使用者"))
    else: df["role"] = df.apply(lambda row: default_roles.get(row["name"], "使用者") if pd.isna(row.get("role")) or str(row.get("role")).strip() == "" else row["role"], axis=1)
    
    if "line_uid" not in df.columns: df["line_uid"] = ""
    if "status" not in df.columns: df["status"] = "在職"
    
    return df

def save_staff(df): 
    df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')
    sync_to_github(S_FILE) 

def load_projects():
    if not os.path.exists(P_FILE):
        pd.DataFrame(columns=["負責執行長", "專案名稱", "專案編號"]).to_csv(P_FILE, index=False, encoding='utf-8-sig')
    return read_csv_robust(P_FILE)

def save_projects(df):
    df.to_csv(P_FILE, index=False, encoding='utf-8-sig')
    sync_to_github(P_FILE) 

def load_vendors():
    if not os.path.exists(V_FILE):
        pd.DataFrame(columns=["請款廠商", "匯款帳戶"]).to_csv(V_FILE, index=False, encoding='utf-8-sig')
    return read_csv_robust(V_FILE)

def save_vendors(df):
    df.to_csv(V_FILE, index=False, encoding='utf-8-sig')
    sync_to_github(V_FILE) 

# --- 4. 請款單資料打包解析器 ---
def parse_req_json(desc_raw):
    try:
        if "[請款單資料]" in desc_raw:
            return json.loads(desc_raw.split("[請款單資料]")[1].strip())
    except: pass
    return {"desc": desc_raw, "net_amt": 0, "tax_amt": 0, "fee": 0, "inv_no": "", "acc_name": "", "ims_names": []}

# --- 5. HTML 渲染 ---
def render_html(row):
    amt = clean_amount(row['總金額'])
    data = parse_req_json(row.get("請款說明", ""))
    
    app_name = safe_str(row.get('申請人'))
    proxy_name = safe_str(row.get('代申請人'))
    display_app = f"{app_name} ({proxy_name} 代申請)" if proxy_name and proxy_name != app_name else app_name
    if not display_app: display_app = "尚未指定"
        
    legacy_net = amt if data.get("net_amt", 0) == 0 and data.get("tax_amt", 0) == 0 else data.get("net_amt", 0)
    fee = data.get("fee", 0)
    tax = data.get("tax_amt", 0)
    stt = safe_str(row.get("狀態")).strip()

    sub_time = safe_str(row.get("提交時間"))[:16].strip()
    fst_appr = clean_name(row.get("初審人")).strip()
    fst_time = safe_str(row.get("初審時間"))[:16].strip()
    sec_appr = clean_name(row.get("複審人")).strip()
    sec_time = safe_str(row.get("複審時間"))[:16].strip()

    fallback_date = get_fallback_date(row)

    if stt in ["待簽核", "待初審", "待複審", "已核准", "已駁回"]:
        if not sub_time: sub_time = f"{fallback_date} 12:00"
        elif len(sub_time) <= 10: sub_time = f"{sub_time} 12:00"
        s_submit = f"{display_app} {sub_time}".strip()
    else:
        s_submit = "" 

    if stt in ["待複審", "已核准"]:
        if not fst_appr: fst_appr = clean_name(row.get("專案負責人"))
        if not fst_time: fst_time = f"{fallback_date} 13:00"
        elif len(fst_time) <= 10: fst_time = f"{fst_time} 13:00"
        s_first = f"{fst_appr} {fst_time}".strip()
    else:
        s_first = ""

    if stt == "已核准":
        if not sec_appr: sec_appr = CFO_NAME
        if not sec_time: sec_time = f"{fallback_date} 14:00"
        elif len(sec_time) <= 10: sec_time = f"{sec_time} 14:00"
        s_second = f"{sec_appr} {sec_time}".strip()
    else:
        s_second = ""

    h = f'<div style="padding:40px;border:4px solid #000;background:#fff;color:#000;font-family:sans-serif;max-width:900px;margin:auto;">'
    h += f'<div style="text-align:center;"><h1 style="margin-bottom:10px;font-size:32px;letter-spacing:2px;">Time Lab 時研國際設計股份有限公司</h1></div>'
    h += f'<div style="text-align:center;"><h2 style="margin-top:0px;margin-bottom:15px;font-size:24px;letter-spacing:5px;">請款單 (展示版)</h2></div>'
    h += f'<hr style="border-top: 3px solid black; margin-bottom: 3px;">'
    h += f'<hr style="border-top: 1px solid black; margin-top: 0px; margin-bottom: 20px;">'
    
    h += '<table style="width:100%;border-collapse:collapse;font-size:15px;border:2px solid black;" border="1">'
    h += f'<tr><td width="15%" style="padding:8px;">單號</td><td width="35%" style="padding:8px;">{safe_str(row.get("單號"))}</td><td width="15%" style="padding:8px;">負責執行長</td><td width="35%" style="padding:8px;">{safe_str(row.get("專案負責人"))}</td></tr>'
    h += f'<tr><td style="padding:8px;">專案</td><td style="padding:8px;">{safe_str(row.get("專案名稱"))}</td><td style="padding:8px;">編號</td><td style="padding:8px;">{safe_str(row.get("專案編號"))}</td></tr>'
    h += f'<tr><td style="padding:8px;">申請人</td><td style="padding:8px;">{display_app}</td><td style="padding:8px;">廠商</td><td style="padding:8px;">{safe_str(row.get("請款廠商"))}</td></tr>'
    h += f'<tr><td style="padding:8px;">匯款帳戶</td><td colspan="3" style="padding:8px;">{safe_str(row.get("匯款帳戶"))}</td></tr>'
    
    desc_html = data.get("desc","").replace("\n", "<br>")
    inv_str = f"發票/憑證: {safe_str(data.get('inv_no',''))}<br>" if safe_str(data.get('inv_no','')) else ""
    h += f'<tr><td style="padding:8px;">說明</td><td colspan="3" style="padding:8px;">{inv_str}{desc_html}</td></tr>'
    
    cur = safe_str(row.get("幣別")) or "TWD"
    h += f'<tr><td colspan="3" align="right" style="padding:8px;">金額 (未稅)</td><td align="right" style="padding:8px;">{cur} {legacy_net:,}</td></tr>'
    h += f'<tr><td colspan="3" align="right" style="padding:8px;">稅額</td><td align="right" style="padding:8px;">{cur} {tax:,}</td></tr>'
    h += f'<tr><td colspan="3" align="right" style="padding:8px;">手續費</td><td align="right" style="padding:8px;">{cur} {fee:,}</td></tr>'
    h += f'<tr><td colspan="3" align="right" style="padding:8px;"><b>實付 / 請款總額</b></td><td align="right" style="padding:8px;"><b>{cur} {amt:,}</b></td></tr></table>'
    
    h += f'<p style="font-size:15px;margin-top:20px;line-height:1.6;">提交: {s_submit} | 初審: {s_first} | 複審: {s_second}</p></div>'
    return h

def render_inline_preview(r, prefix_key):
    with st.container():
        st.markdown(f"#### 🔍 單號 {r['單號']} 預覽 (體驗版)")
        st.markdown(render_html(r), unsafe_allow_html=True)
        all_files = []
        acc_img = safe_str(r.get("帳戶影像Base64"))
        if acc_img: all_files.append(acc_img)

        req_img = safe_str(r.get("影像Base64"))
        if req_img:
            chunks = req_img.split('|') if '|' in req_img else req_img.split(',') if ',' in req_img else [req_img]
            for chunk in chunks:
                c = chunk.strip()
                if c.startswith('data:'): c = c.split('base64,')[-1]
                if c: all_files.append(c)

        if all_files:
            for idx, f_b64 in enumerate(all_files):
                try:
                    pad = f_b64 + "=" * ((4 - len(f_b64) % 4) % 4)
                    raw = base64.b64decode(pad)
                    if raw.startswith(b'PK\x03\x04') or raw.startswith(b'\xd0\xcf\x11\xe0'):
                        try:
                            st.dataframe(pd.read_excel(io.BytesIO(raw)), use_container_width=True)
                        except:
                            st.error("⚠️ 無法預覽此 Excel。請確保 requirements.txt 包含 openpyxl。")
                    else: st.image(raw, use_container_width=True)
                except Exception: pass 
        
        if st.button("❌ 關閉預覽", key=f"close_{prefix_key}"):
            st.session_state.req_view_id = None
            st.rerun()
        st.markdown("---")

def render_html_with_attachments(row):
    h = render_html(row)
    all_files = []
    acc_img = safe_str(row.get("帳戶影像Base64"))
    if acc_img: all_files.append(acc_img)
    req_img = safe_str(row.get("影像Base64"))
    if req_img:
        chunks = req_img.split('|') if '|' in req_img else req_img.split(',') if ',' in req_img else [req_img]
        for chunk in chunks:
            c = chunk.strip()
            if c.startswith('data:'): c = c.split('base64,')[-1]
            if c: all_files.append(c)

    if all_files:
        h += '<div style="max-width:900px;margin:auto;padding-top:30px;page-break-before:always;">'
        for idx, f_b64 in enumerate(all_files):
            try:
                pad = f_b64 + "=" * ((4 - len(f_b64) % 4) % 4)
                raw = base64.b64decode(pad)
                if raw.startswith(b'PK\x03\x04') or raw.startswith(b'\xd0\xcf\x11\xe0'):
                    try:
                        df_ex = pd.read_excel(io.BytesIO(raw))
                        html_table = df_ex.to_html(index=False).replace('\n', '')
                        css_rules = "<style>.xls-tbl { width: 100%; border-collapse: collapse; font-size: 11px; table-layout: fixed; } .xls-tbl th, .xls-tbl td { border: 1px solid #000; padding: 4px; word-wrap: break-word; overflow-wrap: break-word; white-space: normal; word-break: break-all; } .xls-tbl th { background-color: #f0f0f0; } .xls-tbl tr { page-break-inside: avoid !important; }</style>"
                        html_table = html_table.replace('<table', f'{css_rules}<table class="xls-tbl"')
                        h += f"{html_table}<br><br>"
                    except Exception as e:
                        h += f"<div style='color:red;'>⚠️ Excel轉換列印失敗。請確保您的 GitHub `requirements.txt` 中已加入 `openpyxl` 套件。</div><br>"
                else:
                    mime = "image/png" if raw.startswith(b'\x89PNG') else "image/jpeg"
                    h += f'<img src="data:{mime};base64,{pad}" style="max-width:100%; margin-bottom:20px; border:none;"><br><br>'
            except Exception:
                pass
        h += '</div>'
    return h

def clean_for_js(h_str): return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

def render_upload_popover(container, r, prefix):
    with container.popover("📎 附件"):
        st.write("**上傳附件 (圖/Excel)**")
        nf_acc = st.file_uploader("存摺", type=["png", "jpg", "xlsx", "xls"], key=f"{prefix}_a")
        nf_ims = st.file_uploader("憑證", type=["png", "jpg", "xlsx", "xls"], accept_multiple_files=True, key=f"{prefix}_i")
        if st.button("💾 儲存附件", key=f"{prefix}_b"):
            fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
            jd = parse_req_json(fresh_db.at[idx, "請款說明"])
            
            if nf_acc: 
                fresh_db.at[idx, "帳戶影像Base64"] = base64.b64encode(nf_acc.getvalue()).decode()
                jd["acc_name"] = nf_acc.name
            if nf_ims: 
                fresh_db.at[idx, "影像Base64"] = "|".join([base64.b64encode(f.getvalue()).decode() for f in nf_ims])
                jd["ims_names"] = [f.name for f in nf_ims]
            
            if nf_acc or nf_ims:
                packed_desc = "[請款單資料]\n" + json.dumps(jd, ensure_ascii=False)
                fresh_db.at[idx, "請款說明"] = packed_desc
                save_data(fresh_db); st.rerun()

# --- 6. Session 初始化與防呆重載 ---
if st.session_state.get('user_id') is None: st.switch_page("app.py")

if 'staff_df' not in st.session_state: 
    st.session_state.staff_df = load_staff()
else:
    if "role" not in st.session_state.staff_df.columns:
        st.session_state.staff_df = load_staff()

# 離職防護網
curr_name = st.session_state.user_id
curr_user_info = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name]
if not curr_user_info.empty and curr_user_info.iloc[0].get("status") == "離職":
    st.error("🚫 您的帳號已被標註為「離職」，無法存取系統。")
    time.sleep(2)
    st.session_state.user_id = None
    st.switch_page("app.py")
    st.stop()

for k in ['req_edit_id', 'req_last_id', 'req_view_id
