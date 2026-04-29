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

/* ========================================================= */
/* ★ 終極殺手鐧：徹底摧毀黑色方塊，強制顯示微軟 Excel 彩色圖示 */
/* ========================================================= */

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
/* ========================================================= */

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

/* 側邊欄輸入框與下拉選單強制黑字與黑色箭頭，避免白底白字隱形 */
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
            if c not in df.columns: df[c] = ""
        for c in ["總金額", "已請款金額", "尚未請款金額"]:
            df[c] = df[c].apply(clean_amount)
        return df[cols]
    except:
        return pd.DataFrame(columns=cols)

def save_data(df):
    try: 
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
        sync_to_github(D_FILE) 
    except: st.error("⚠️ 檔案鎖定中！請關閉電腦上的 database.csv。"); st.stop()

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
    h += f'<div style="text-align:center;"><h2 style="margin-top:0px;margin-bottom:15px;font-size:24px;letter-spacing:5px;">請款單</h2></div>'
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

for k in ['req_edit_id', 'req_last_id', 'req_view_id', 'req_print_id', 'req_last_msg', 'req_review_id', 'req_review_type']: 
    if k not in st.session_state: st.session_state[k] = None

if 'req_uploader_key' not in st.session_state: st.session_state.req_uploader_key = 0

curr_role = "使用者"
if not curr_user_info.empty:
    curr_role = curr_user_info.iloc[0].get("role", "使用者")

is_admin = (curr_role == "管理員") or (curr_name in ADMINS)
is_active = (st.session_state.user_status == "在職")

# --- 7. 左側側邊欄 ---
st.sidebar.markdown(f"**📌 目前系統：** <code>{st.session_state.sys_choice}</code>", unsafe_allow_html=True)
st.sidebar.divider()

avatar_b64 = ""
try: avatar_b64 = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0].get("avatar", "")
except: pass

if avatar_b64: st.sidebar.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:15px;"><img src="data:image/jpeg;base64,{avatar_b64}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;border:3px solid #eee;"><span style="font-size:22px;font-weight:bold;color:#333;">{curr_name}</span></div>', unsafe_allow_html=True)
else: st.sidebar.markdown(f"### 👤 {curr_name}")

st.sidebar.info(f"🟢 目前在線人數：**{get_online_users(curr_name)}** 人")

with st.sidebar.expander("📸 修改大頭貼"):
    new_avatar = st.file_uploader("上傳圖片", type=["jpg", "png"], key="req_side_avatar")
    if st.button("更新大頭貼", key="req_update_avatar") and new_avatar:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "avatar"] = base64.b64encode(new_avatar.getvalue()).decode()
        save_staff(s_df); st.session_state.staff_df = s_df; st.rerun()

with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password", key="req_side_pw")
    if st.button("更新密碼", key="req_update_pw") and len(new_pw) >= 4:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "password"] = str(new_pw); save_staff(s_df); st.success("成功")

if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.success("管理員專屬區塊")
    
    with st.sidebar.expander("🔑 所有人員密碼清單"):
        st.dataframe(st.session_state.staff_df[["name", "password"]], hide_index=True)
        st.write("**恢復預設密碼 (0000)**")
        reset_target = st.selectbox("選擇人員", st.session_state.staff_df["name"].tolist(), key="req_rst_sel")
        if st.button("確認恢復預設", key="req_rst_btn"):
            s_df = load_staff()
            idx = s_df[s_df["name"] == reset_target].index[0]
            s_df.at[idx, "password"] = "0000"
            save_staff(s_df)
            st.session_state.staff_df = s_df
            st.success(f"{reset_target} 密碼已重置")
            
    with st.sidebar.expander("➕ 新增人員"):
        n = st.text_input("姓名", key="req_new_staff_name")
        new_role = st.selectbox("系統層級", ["使用者", "執行長", "執行長&財務長", "管理員"], key="req_new_staff_role")
        if st.button("新增", key="req_add_staff"):
            s_df = load_staff()
            if n and n not in s_df["name"].values:
                new_row = pd.DataFrame([{"name": n, "status": "在職", "password": "0000", "avatar": "", "line_uid": "", "role": new_role}])
                s_df = pd.concat([s_df, new_row], ignore_index=True)
                save_staff(s_df)
                st.session_state.staff_df = s_df
                st.success("人員新增成功")
                st.rerun()
            elif n in s_df["name"].values:
                st.error("人員已存在")

    with st.sidebar.expander("⚙️ 人員設定 (狀態, 層級 & LINE ID)"):
        edited_staff = st.data_editor(
            st.session_state.staff_df[["name", "status", "role", "line_uid"]], 
            column_config={
                "name": st.column_config.TextColumn("姓名", disabled=True),
                "status": st.column_config.SelectboxColumn("狀態", options=["在職", "離職"]),
                "role": st.column_config.SelectboxColumn("系統層級", options=["使用者", "執行長", "執行長&財務長", "管理員"])
            }, 
            hide_index=True, 
            key="req_staff_editor_admin"
        )
        if st.button("💾 儲存人員設定", key="req_save_staff_admin"):
            s_df = load_staff()
            for idx, row in edited_staff.iterrows():
                s_df.at[idx, "status"] = row["status"]
                s_df.at[idx, "role"] = row["role"]
                s_df.at[idx, "line_uid"] = str(row["line_uid"]).strip() if pd.notna(row["line_uid"]) else ""
            save_staff(s_df)
            st.session_state.staff_df = s_df
            st.rerun()

if st.sidebar.button("登出系統", key="req_logout"): st.session_state.user_id = None; st.switch_page("app.py")

if is_admin:
    menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽", "5. 請款狀態/系統設定"]
else:
    menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽"]
    
menu = st.sidebar.radio("導覽", menu_options, key="req_menu_radio")

if "req_prev_state_menu" not in st.session_state:
    st.session_state.req_prev_state_menu = menu
if "req_prev_state_user" not in st.session_state:
    st.session_state.req_prev_state_user = st.session_state.user_id

if menu != st.session_state.req_prev_state_menu or st.session_state.user_id != st.session_state.req_prev_state_user:
    st.session_state.req_view_id = None
    st.session_state.req_print_id = None
    st.session_state.req_edit_id = None
    st.session_state.req_review_id = None 
    st.session_state.req_prev_state_menu = menu
    st.session_state.req_prev_state_user = st.session_state.user_id
    st.rerun()

# ================= ★ 全域霸氣 Logo (RWD 完美自適應) ★ =================
st.markdown("""
    <style>
    .global-logo-container { 
        width: 100%; 
        text-align: center; 
        margin-bottom: 25px; 
        margin-top: 10px; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        gap: 15px; 
        flex-wrap: wrap; 
        box-sizing: border-box; 
    }
    .global-logo-en { 
        font-size: clamp(24px, 5vw, 38px); 
        font-weight: 500; 
        font-family: "Times New Roman", Times, serif; 
        color: #3E3024; 
        white-space: nowrap; 
    }
    .global-logo-tw { 
        font-size: clamp(16px, 4vw, 32px); 
        font-weight: 900; 
        color: #2C3E50; 
        letter-spacing: 1px; 
        font-family: "Microsoft JhengHei", "PingFang TC", sans-serif; 
        word-break: break-word; 
        line-height: 1.2;
    }
    @media screen and (max-width: 768px) {
        .global-logo-container { 
            flex-direction: column !important; 
            gap: 5px !important; 
            width: 100% !important;
            max-width: 100vw !important;
        }
        .global-logo-en {
            font-size: 26px !important;
            white-space: normal !important;
        }
        .global-logo-tw { 
            font-size: 18px !important;
            margin-left: 0 !important; 
            display: block !important; 
            text-align: center !important; 
            white-space: normal !important; 
        }
    }
    </style>
    <div class='global-logo-container'>
        <span class='global-logo-en'>T<span style='color: #C19A6B;'>i</span>me Lab</span>
        <span class='global-logo-tw'>時研國際設計股份有限公司</span>
    </div>
""", unsafe_allow_html=True)

# ================= ★ 獨立全螢幕簽核視窗邏輯 ★ =================
if st.session_state.get('req_review_id'):
    st.subheader(f"📝 簽核預覽視窗 - 單號: {st.session_state.req_review_id}")
    r_df = load_data()
    r_df = r_df[r_df["單號"]==st.session_state.req_review_id]
    
    if r_df.empty:
        st.warning("⚠️ 找不到該單號資料，可能已被刪除。")
        if st.button("❌ 關閉視窗"): st.session_state.req_review_id = None; st.rerun()
    else:
        r = r_df.iloc[0]
        sign_type = st.session_state.req_review_type
        
        c_btn1, c_btn2, c_btn3, _ = st.columns([1.5, 1.5, 1.5, 5])
        if c_btn1.button("⬅️ 關閉視窗"): 
            st.session_state.req_review_id = None; st.rerun()
            
        can_sign = (r["專案負責人"] == curr_name if sign_type == "EXE" else curr_name == CFO_NAME) and is_active and curr_name != "Anita"
        
        if c_btn2.button("✅ 確認核准", disabled=not can_sign):
            fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
            if sign_type == "EXE":
                fresh_db.loc[idx, ["狀態", "初審人", "初審時間"]] = ["待複審", curr_name, get_taiwan_time()]
                sys_name = st.session_state.get('sys_choice', '請款單系統')
                send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{r['單號']}\n專案名稱：{r['專案名稱']}\n執行長已核准，有一筆表單需要財務長 ({CFO_NAME}) 進行簽核！")
            else:
                fresh_db.loc[idx, ["狀態", "複審人", "複審時間"]] = ["已核准", curr_name, get_taiwan_time()]
            save_data(fresh_db); st.success("已核准！"); time.sleep(0.5)
            st.session_state.req_review_id = None; st.rerun()
            
        if can_sign:
            with c_btn3.popover("❌ 駁回單據"):
                reason = st.text_input("請輸入駁回原因")
                if st.button("確認駁回", key="btn_rej_conf"):
                    fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    field_prefix = "初審" if sign_type == "EXE" else "複審"
                    fresh_db.loc[idx, ["狀態", "駁回原因", f"{field_prefix}人", f"{field_prefix}時間"]] = ["已駁回", reason, curr_name, get_taiwan_time()]
                    save_data(fresh_db); st.success("已駁回！"); time.sleep(0.5)
                    st.session_state.req_review_id = None; st.rerun()
        else:
            c_btn3.button("❌ 駁回單據", disabled=True)

        st.divider()
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
            for f_b64 in all_files:
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

# 如果沒有進入簽核視窗，則顯示正常選單頁面
else:
    # --- 8. 簽核列表渲染模組 ---
    def render_signing_table(df_list, sign_type, is_history=False):
        if df_list.empty:
            st.info("目前無相關紀錄")
            return
        
        chk_disabled = (curr_name == "Anita")
        
        if not is_history:
            col_all, _ = st.columns([1, 9])
            select_all = col_all.checkbox("☑️ 全選", key=f"sel_all_{sign_type}", disabled=chk_disabled)
            
            display_df = df_list[["單號", "專案名稱", "總金額"]].copy()
            display_df["總金額"] = display_df["總金額"].apply(lambda x: f"${clean_amount(x):,}")
            display_df = display_df.rename(columns={"總金額": "金額"})
            display_df.insert(0, "選擇", select_all)
            
            edited_df = st.data_editor(
                display_df,
                column_config={"選擇": st.column_config.CheckboxColumn("選擇", default=False, disabled=chk_disabled)},
                disabled=["單號", "專案名稱", "金額"],
                hide_index=True,
                use_container_width=True,
                key=f"editor_{sign_type}_{select_all}"
            )
            
            selected_ids = edited_df[edited_df["選擇"] == True]["單號"].tolist()

            st.markdown("---")
            batch_c1, batch_c2, _ = st.columns([2.5, 2.5, 5])
            
            is_btn_disabled = (len(selected_ids) == 0) or (curr_name == "Anita")
            
            if batch_c1.button(f"✅ 確認核准 (已選 {len(selected_ids)} 筆)", disabled=is_btn_disabled, key=f"bat_ok_{sign_type}"):
                fresh_db = load_data()
                success_count = 0
                for sel_id in selected_ids:
                    r_match = df_list[df_list["單號"] == sel_id].iloc[0]
                    if (r_match["專案負責人"] == curr_name if sign_type == "EXE" else curr_name == CFO_NAME) and is_active and curr_name != "Anita":
                        idx = fresh_db[fresh_db["單號"]==sel_id].index[0]
                        if sign_type == "EXE":
                            fresh_db.loc[idx, ["狀態", "初審人", "初審時間"]] = ["待複審", curr_name, get_taiwan_time()]
                            sys_name = st.session_state.get('sys_choice', '請款單系統')
                            send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{sel_id}\n專案名稱：{r_match['專案名稱']}\n執行長已核准，有一筆表單需要財務長 ({CFO_NAME}) 進行簽核！")
                        else:
                            fresh_db.loc[idx, ["狀態", "複審人", "複審時間"]] = ["已核准", curr_name, get_taiwan_time()]
                        success_count += 1
                if success_count > 0:
                    save_data(fresh_db); st.success(f"成功核准 {success_count} 筆單據！"); time.sleep(1); st.rerun()

            if is_btn_disabled:
                batch_c2.button(f"❌ 駁回單據 (已選 {len(selected_ids)} 筆)", disabled=True, key=f"fake_rej_{sign_type}")
            else:
                with batch_c2.popover(f"❌ 駁回單據 (已選 {len(selected_ids)} 筆)"):
                    reason = st.text_input("請統一輸入駁回原因", key=f"rej_batch_{sign_type}")
                    if st.button("確認批次駁回"):
                        fresh_db = load_data()
                        success_count = 0
                        for sel_id in selected_ids:
                            r_match = df_list[df_list["單號"] == sel_id].iloc[0]
                            if (r_match["專案負責人"] == curr_name if sign_type == "EXE" else curr_name == CFO_NAME) and is_active and curr_name != "Anita":
                                idx = fresh_db[fresh_db["單號"]==sel_id].index[0]
                                field_prefix = "初審" if sign_type == "EXE" else "複審"
                                fresh_db.loc[idx, ["狀態", "駁回原因", f"{field_prefix}人", f"{field_prefix}時間"]] = ["已駁回", reason, curr_name, get_taiwan_time()]
                                success_count += 1
                        if success_count > 0:
                            save_data(fresh_db); st.success(f"成功駁回 {success_count} 筆單據！"); time.sleep(1); st.rerun()
                        
            st.write("👉 **或選擇單號進入專屬簽核視窗：**")
            col_sel, col_btn_v, _ = st.columns([2.5, 2.5, 5])
            sel_id_view = col_sel.selectbox("選擇預覽單號", df_list["單號"].tolist(), label_visibility="collapsed", key=f"sel_v_{sign_type}")
            if col_btn_v.button("📄 開啟預覽/簽核"):
                st.session_state.req_review_id = sel_id_view
                st.session_state.req_review_type = sign_type
                st.rerun()
                
        else:
            if is_admin:
                cols_header = st.columns([1.2, 2.0, 1.2, 1.2, 1.2, 3.0])
                headers = ["單號", "專案名稱", "負責執行長", "申請人", "請款金額", "操作"]
            else:
                cols_header = st.columns([1.2, 1.8, 1.0, 2.4])
                headers = ["單號", "專案名稱", "金額", "操作"]

            for c, h in zip(cols_header, headers): c.write(f"**{h}**")

            for i, r in df_list.iterrows():
                if is_admin:
                    c = st.columns([1.2, 2.0, 1.2, 1.2, 1.2, 3.0])
                    c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"]); c[4].write(f"${clean_amount(r['總金額']):,}")
                    btn_c = c[5]
                else:
                    c = st.columns([1.2, 1.8, 1.0, 2.4])
                    p_name = str(r["專案名稱"])
                    if len(p_name) > 8: p_name = p_name[:7] + "..."
                    c[0].write(r["單號"]); c[1].write(p_name); c[2].write(f"${clean_amount(r['總金額']):,}")
                    btn_c = c[3]

                with btn_c:
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    if btn_col1.button("預覽", key=f"sv_{sign_type}_{r['單號']}_{is_history}"):
                        st.session_state.req_view_id = r["單號"]; st.rerun()
                    btn_col2.write(f"[{r['狀態']}]")

    # ================= 各頁面顯示邏輯 =================
    if menu == "1. 填寫申請單":
        st.subheader("📝 填寫請款申請單")
        if st.session_state.get('req_last_msg'): st.success(st.session_state.req_last_msg); st.session_state.req_last_msg = None

        p_db = load_projects(); v_db = load_vendors()

        with st.expander("➕ 新增專案 / 廠商至資料庫"):
            tb1, tb2 = st.tabs(["📂 新增專案", "🏢 新增廠商"])
            with tb1:
                pc1, pc2, pc3, pc4 = st.columns([1, 2, 2, 1])
                new_p_exe = pc1.selectbox("所屬執行長", st.session_state.staff_df["name"].apply(clean_name).tolist(), key="new_p_exe")
                new_p_name = pc2.text_input("新專案名稱", key="new_p_name")
                new_p_id = pc3.text_input("新專案編號", key="new_p_id")
                if pc4.button("➕ 儲存專案"):
                    if new_p_name and new_p_id:
                        p_db = load_projects(); p_db = pd.concat([p_db, pd.DataFrame([{"負責執行長": new_p_exe, "專案名稱": new_p_name, "專案編號": new_p_id}])], ignore_index=True)
                        save_projects(p_db); st.success(f"已存入 {new_p_name} 資料庫！"); time.sleep(1); st.rerun()
                    else: st.error("請填寫完整資訊")
            with tb2:
                vc1, vc2, vc3 = st.columns([2, 2, 1])
                new_v_name = vc1.text_input("新廠商名稱", key="new_v_name")
                new_v_acc = vc2.text_input("新匯款帳戶", key="new_v_acc")
                if vc3.button("➕ 儲存廠商"):
                    if new_v_name and new_v_acc:
                        v_db = load_vendors(); v_db = pd.concat([v_db, pd.DataFrame([{"請款廠商": new_v_name, "匯款帳戶": new_v_acc}])], ignore_index=True)
                        save_vendors(v_db); st.success(f"已存入 {new_v_name} 資料庫！"); time.sleep(1); st.rerun()
                    else: st.error("請填寫完整資訊")

        db = load_data()
        
        active_staffs = st.session_state.staff_df[st.session_state.staff_df["status"] == "在職"]["name"].apply(clean_name).tolist()
        
        up_key = st.session_state.req_uploader_key
        net_key = f"n_{up_key}"
        tax_key = f"t_{up_key}"
        
        dv = {"app": curr_name, "pn": "", "pi": "", "exe": active_staffs[0] if active_staffs else "", "net_amt": 0, "tax_amt": 0, "desc": "", "ib64": "", "cur": "TWD", "ab64":"", "vdr":"", "acc":"", "pay":"匯款(扣30手續費)", "inv_no":"", "acc_name": "", "ims_names": []}
        
        if st.session_state.req_edit_id:
            match_r = db[db["單號"]==st.session_state.req_edit_id]
            if not match_r.empty:
                r = match_r.iloc[0]; jd = parse_req_json(r["請款說明"])
                legacy_net = clean_amount(r["總金額"]) if jd.get("net_amt", 0) == 0 and jd.get("tax_amt", 0) == 0 else jd.get("net_amt", 0)
                dv.update({"app": r["申請人"], "pn": r["專案名稱"], "pi": r["專案編號"], "exe": r["專案負責人"], "net_amt": legacy_net, "tax_amt": jd.get("tax_amt", 0), "desc": jd.get("desc", ""), "ib64": r["影像Base64"], "cur": r.get("幣別","TWD"), "ab64": r["帳戶影像Base64"], "vdr": r.get("請款廠商",""), "acc": r.get("匯款帳戶",""), "pay": r.get("付款方式","匯款(扣30手續費)"), "inv_no": jd.get("inv_no", ""), "acc_name": jd.get("acc_name", ""), "ims_names": jd.get("ims_names", [])})

        app_options = active_staffs.copy()
        if dv["app"] and dv["app"] not in app_options: app_options.append(dv["app"])
        exe_options = active_staffs.copy()
        if dv["exe"] and dv["exe"] not in exe_options: exe_options.append(dv["exe"])

        # 初始化 Session State
        if net_key not in st.session_state: st.session_state[net_key] = int(dv["net_amt"])
        if tax_key not in st.session_state: st.session_state[tax_key] = int(dv["tax_amt"])

        def calc_tax():
            st.session_state[tax_key] = int(st.session_state[net_key] * 0.05)

        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            app_val = c1.selectbox("申請人", app_options, index=app_options.index(dv["app"]) if dv["app"] in app_options else 0) if curr_name == "Anita" else curr_name
            if curr_name != "Anita": c1.text_input("申請人", value=app_val, disabled=True)
            exe = c2.selectbox("負責執行長", exe_options, index=exe_options.index(dv["exe"]) if dv["exe"] in exe_options else 0)
            
            filtered_p = p_db[p_db["負責執行長"] == exe]
            p_names = filtered_p["專案名稱"].unique().tolist(); p_options = [""] + p_names + ["➕ 手動輸入"]
            pn_idx = p_options.index("➕ 手動輸入") if dv["pn"] and dv["pn"] not in p_names else p_options.index(dv["pn"]) if dv["pn"] in p_options else 0
                
            pn_sel = c3.selectbox("專案名稱", p_options, index=pn_idx)
            if pn_sel == "➕ 手動輸入": pn = c3.text_input("✍️ 手動輸入專案名稱", value=dv["pn"] if dv["pn"] not in p_names else "")
            else: pn = pn_sel
                
            auto_id = filtered_p[filtered_p["專案名稱"] == pn]["專案編號"].iloc[0] if pn_sel != "➕ 手動輸入" and pn in filtered_p["專案名稱"].values else dv["pi"]
            pi = c4.text_input("專案編號 (可手寫修改)", value=auto_id)
            
            cx1, cx2, cx3, cx4 = st.columns(4)
            curr = cx1.selectbox("幣別", ["TWD", "USD", "EUR"], index=["TWD", "USD", "EUR"].index(dv["cur"]) if dv["cur"] in ["TWD", "USD", "EUR"] else 0)
            
            net_amt = cx2.number_input("金額 (未稅)", min_value=0, key=net_key, on_change=calc_tax)
            tax_amt = cx3.number_input("稅額", min_value=0, key=tax_key)
            cx4.text_input("總計金額 (未稅+稅額)", value=f"{int(net_amt) + int(tax_amt):,}", disabled=True)
            
            v_names = v_db["請款廠商"].unique().tolist(); v_options = [""] + v_names + ["➕ 手動輸入"]
            vdr_idx = v_options.index("➕ 手動輸入") if dv["vdr"] and dv["vdr"] not in v_names else v_options.index(dv["vdr"]) if dv["vdr"] in v_options else 0
                
            cv1, cv2, cv3 = st.columns(3)
            vdr_sel = cv1.selectbox("請款廠商", v_options, index=vdr_idx)
            if vdr_sel == "➕ 手動輸入": vdr = cv1.text_input("✍️ 手動輸入廠商名稱", value=dv["vdr"] if dv["vdr"] not in v_names else "")
            else: vdr = vdr_sel
                
            auto_acc = v_db[v_db["請款廠商"] == vdr]["匯款帳戶"].iloc[0] if vdr_sel != "➕ 手動輸入" and vdr in v_db["請款廠商"].values else dv["acc"]
            acc = cv2.text_input("匯款帳戶 (可手寫修改)", value=auto_acc)
            inv_no = cv3.text_input("發票號碼或憑證 (非必填)", value=dv["inv_no"])
            
            pay_idx = ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"].index(dv["pay"]) if dv["pay"] in ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"] else 2
            pay = st.radio("付款方式", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], index=pay_idx, horizontal=True)
            
            desc = st.text_area("請款說明", value=dv["desc"])
            st.info("💡 **提示：系統會自動加總「金額(未稅) + 稅額」，若選擇「扣30手續費」，最終存檔總金額會自動扣除 30 元。**")
            
            f_acc = st.file_uploader("上傳存摺/匯款資料 (圖/Excel)", type=["png", "jpg", "xlsx", "xls"], key=f"req_f_acc_{up_key}")
            f_ims = st.file_uploader("上傳請款憑證 (圖/Excel)", type=["png", "jpg", "xlsx", "xls"], accept_multiple_files=True, key=f"req_f_ims_{up_key}")
            
            del_acc = False; del_ims = []; existing_ims = []; existing_ims_names = dv["ims_names"]
            
            if st.session_state.req_edit_id:
                st.markdown("---"); st.markdown("### 📎 現有附件管理 (勾選以刪除)")
                
                acc_img_str = safe_str(dv["ab64"])
                if acc_img_str and len(acc_img_str) > 50:
                    disp_acc = dv["acc_name"] if dv["acc_name"] else "存摺/匯款資料"
                    del_acc = st.checkbox(f"🗑️ 刪除目前已上傳之「{disp_acc}」")
                    
                req_img_str = safe_str(dv["ib64"])
                if req_img_str:
                    chunks = req_img_str.split('|') if '|' in req_img_str else req_img_str.split(',') if ',' in req_img_str else [req_img_str]
                    for chunk in chunks:
                        c = chunk.strip()
                        if c.startswith('data:'): c = c.split('base64,')[-1]
                        if c and len(c) > 50: existing_ims.append(c)
                    
                    if existing_ims:
                        st.write("**已上傳之請款憑證：**")
                        for idx, _ in enumerate(existing_ims):
                            disp_name = existing_ims_names[idx] if idx < len(existing_ims_names) else f"舊版憑證 {idx+1}"
                            if st.checkbox(f"🗑️ 刪除 {disp_name}", key=f"del_im_{idx}"): del_ims.append(idx)
                                
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.req_edit_id:
                c_btn1, c_btn2, c_btn3, c_btn4, c_btn5, c_btn6 = st.columns(6)
                btn_save = c_btn1.button("💾 存檔", use_container_width=True)
                btn_submit = c_btn2.button("🚀 提交", use_container_width=True)
                btn_preview = c_btn3.button("🔍 預覽", use_container_width=True)
                btn_print = c_btn4.button("🖨️ 列印", use_container_width=True)
                btn_next = c_btn5.button("🆕 下一筆申請", use_container_width=True)
                btn_cancel = c_btn6.button("❌ 不存檔", use_container_width=True)
            else:
                c_btn1, c_btn2, c_btn3, c_btn4, c_btn5 = st.columns(5)
                btn_save = c_btn1.button("💾 存檔", use_container_width=True)
                btn_submit = c_btn2.button("🚀 提交", use_container_width=True)
                btn_preview = c_btn3.button("🔍 預覽", use_container_width=True)
                btn_print = c_btn4.button("🖨️ 列印", use_container_width=True)
                btn_next = c_btn5.button("🆕 下一筆申請", use_container_width=True)
                btn_cancel = False

            if btn_cancel:
                st.session_state.req_edit_id = None; st.session_state.req_last_msg = "🚫 已取消修改，未儲存任何變更。"; st.session_state.req_uploader_key += 1; st.rerun()
                
            elif btn_save or btn_submit or btn_preview or btn_print:
                fee = 30 if pay == "匯款(扣30手續費)" else 0
                total_amt = net_amt + tax_amt - fee
                if not pn or (net_amt + tax_amt) <= 0: st.error("⚠️ 請填寫「專案名稱」且金額須大於 0")
                else:
                    if f_acc: b_acc = base64.b64encode(f_acc.getvalue()).decode(); acc_name_save = f_acc.name
                    else: b_acc = "" if del_acc else safe_str(dv["ab64"]); acc_name_save = "" if del_acc else dv["acc_name"]

                    retained_ims = [img for i, img in enumerate(existing_ims) if i not in del_ims]
                    safe_existing_names = dv["ims_names"] + [f"舊版憑證 {i+1}" for i in range(len(existing_ims) - len(dv["ims_names"]))]
                    retained_names = [name for i, name in enumerate(safe_existing_names[:len(existing_ims)]) if i not in del_ims]
                    new_ims_b64 = [base64.b64encode(f.getvalue()).decode() for f in f_ims] if f_ims else []
                    new_ims_names = [f.name for f in f_ims] if f_ims else []
                    final_ims_list = retained_ims + new_ims_b64
                    final_names_list = retained_names + new_ims_names
                    b_ims = "|".join(final_ims_list)
                    packed_desc = "[請款單資料]\n" + json.dumps({"net_amt": net_amt, "tax_amt": tax_amt, "fee": fee, "inv_no": inv_no, "desc": desc, "acc_name": acc_name_save, "ims_names": final_names_list}, ensure_ascii=False)
                    f_db = load_data(); proxy_app = curr_name if (curr_name == "Anita" and app_val != curr_name) else ""
                    
                    if st.session_state.req_edit_id:
                        idx = f_db[f_db["單號"]==st.session_state.req_edit_id].index[0]
                        f_db.loc[idx, ["申請人", "代申請人", "專案名稱", "專案編號", "專案負責人", "總金額", "請款說明", "請款廠商", "匯款帳戶", "付款方式", "影像Base64", "帳戶影像Base64", "幣別", "狀態"]] = [app_val, proxy_app, pn, pi, exe, total_amt, packed_desc, vdr, acc, pay, b_ims, b_acc, curr, "已存檔未提交"]
                        tid = st.session_state.req_edit_id; msg_prefix = "修改完畢並存檔"
                    else:
                        tid = f"{datetime.date.today().strftime('%Y%m%d')}-{len(f_db[f_db['單號'].str.startswith(datetime.date.today().strftime('%Y%m%d'))])+1:02d}"
                        nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"請款單", "申請人":app_val, "代申請人":proxy_app, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":packed_desc, "總金額":total_amt, "幣別":curr, "請款廠商":vdr, "匯款帳戶":acc, "付款方式":pay, "狀態":"已存檔未提交", "影像Base64":b_ims, "帳戶影像Base64":b_acc}
                        f_db = pd.concat([f_db, pd.DataFrame([nr])], ignore_index=True); msg_prefix = "存檔成功"
                    
                    save_data(f_db)

                    if btn_submit:
                        f_db = load_data(); idx = f_db[f_db["單號"]==tid].index[0]
                        f_db.loc[idx, ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]; save_data(f_db)
                        sys_name = st.session_state.get('sys_choice', '請款單系統')
                        send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{tid}\n專案名稱：{pn}\n有一筆新的表單需要執行長 ({exe}) 進行簽核！")
                        st.session_state.req_edit_id = None; st.session_state.req_last_msg = f"🚀 單據 {tid} 已成功提交簽核！"
                    else:
                        st.session_state.req_edit_id = tid  
                        if btn_preview: st.session_state.req_view_id = tid; st.session_state.req_last_msg = f"📄 單據 {tid} 已{msg_prefix}，正在產生預覽..."
                        elif btn_print: st.session_state.req_print_id = tid; st.session_state.req_last_msg = f"🖨️ 單據 {tid} 已{msg_prefix}，正在準備列印..."
                        else: st.session_state.req_last_msg = f"📄 單據 {tid} 已{msg_prefix}！您可以繼續修改或點擊提交。"
                    
                    st.session_state.req_uploader_key += 1; st.rerun()

            if btn_next: st.session_state.req_edit_id = None; st.session_state.req_last_id = None; st.session_state.req_last_msg = None; st.session_state.req_uploader_key += 1; st.rerun()

        st.divider(); st.subheader("📋 申請追蹤清單")
        f_db = load_data(); my_db = f_db[f_db["類型"]=="請款單"]
        if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
        
        if is_admin:
            cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
            headers = ["申請單號", "專案名稱", "負責執行長", "申請人", "請款總金額", "狀態", "操作"]
        else:
            cols = st.columns([1.2, 1.8, 1.0, 1.5, 2.5])
            headers = ["單號", "專案名稱", "金額", "狀態", "操作"]

        for c, h in zip(cols, headers): c.write(f"**{h}**")
        
        for i, r in my_db.iterrows():
            if is_admin:
                c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
                c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"]); c[4].write(f"{r.get('幣別','TWD')} ${clean_amount(r['總金額']):,}")
                stt_col, btn_col = c[5], c[6]
            else:
                p_name = str(r["專案名稱"])
                if len(p_name) > 8: p_name = p_name[:7] + "..."
                c = st.columns([1.2, 1.8, 1.0, 1.5, 2.5])
                c[0].write(r["單號"]); c[1].write(p_name); c[2].write(f"${clean_amount(r['總金額']):,}")
                stt_col, btn_col = c[3], c[4]
            
            stt_raw = safe_str(r.get("狀態")).strip()
            stt_display = "已存檔未提交" if stt_raw in ["已儲存", "草稿"] else stt_raw
            color = "blue" if stt_display == "已存檔未提交" else "orange" if "待" in stt_display else "green" if stt_display == "已核准" else "red" if stt_display == "已駁回" else "gray"
            stt_col.markdown(f":{color}[**{stt_display}**]")
            
            with btn_col:
                b1, b2, b3, b4, b5, b6 = st.columns(6)
                app_name = safe_str(r.get("申請人")); proxy_name = safe_str(r.get("代申請人"))
                is_own = (curr_name in app_name) or (curr_name in proxy_name) or (curr_name == "Anita")
                can_edit = (stt_raw in ["已儲存", "草稿", "已駁回", "已存檔未提交"]) and is_own and is_active
                
                if b1.button("提交", key=f"s{i}", disabled=not can_edit):
                    fdb = load_data(); fdb.loc[fdb["單號"]==r["單號"], ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]; save_data(fdb)
                    sys_name = st.session_state.get('sys_choice', '請款單系統')
                    send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{r['單號']}\n專案名稱：{r['專案名稱']}\n有一筆新的表單需要執行長 ({r['專案負責人']}) 進行簽核！"); st.rerun()
                if b2.button("預覽", key=f"v{i}"): st.session_state.req_view_id = r["單號"]; st.rerun()
                
                if b3.button("列印", key=f"p{i}"): 
                    html_str = clean_for_js(render_html_with_attachments(r))
                    js_code = f"<script>var w=window.open('');w.document.write('{html_str}');w.document.close();setTimeout(function(){{w.print();w.close();}}, 1000);</script>"
                    st.components.v1.html(js_code, height=0)
                    
                if b4.button("修改", key=f"e{i}", disabled=not can_edit): 
                    st.session_state.req_edit_id = r["單號"]
                    st.session_state.req_uploader_key += 1
                    st.rerun()
                if can_edit:
                    with b5.popover("刪除"):
                        reason = st.text_input("刪除原因", key=f"d_res_{i}")
                        if st.button("確認", key=f"d{i}"):
                            if reason: fresh_db = load_data(); fresh_db.loc[fresh_db["單號"]==r["單號"], ["狀態", "刪除人", "刪除時間", "刪除原因"]] = ["已刪除", curr_name, get_taiwan_time(), reason]; save_data(fresh_db); st.rerun()
                            else: st.error("請輸入原因")
                else: b5.button("刪除", disabled=True, key=f"fake_d_{i}")
                render_upload_popover(b6, r, f"up{i}")

    # ================= 頁面 2: 專案執行長簽核 =================
    elif menu == "2. 專案執行長簽核":
        st.subheader("👨‍💼 專案執行長簽核管理")
        f_db = load_data(); req_db = f_db[f_db["類型"]=="請款單"]
        t1, t2 = st.tabs(["⏳ 待簽核清單", "📜 歷史紀錄 (已核准/已駁回)"])
        with t1:
            pending = req_db[req_db["狀態"].isin(["待簽核", "待初審"])]
            if not is_admin: pending = pending[pending["專案負責人"] == curr_name]
            render_signing_table(pending, "EXE")
        with t2:
            history_exe = req_db[req_db["狀態"].isin(["已核准", "已駁回", "待複審"])]
            if not is_admin: history_exe = history_exe[(history_exe["初審人"] == curr_name) | (history_exe["專案負責人"] == curr_name) | (history_exe["申請人"] == curr_name) | (history_exe["代申請人"] == curr_name)]
            render_signing_table(history_exe, "EXE", is_history=True)

    # ================= 頁面 3: 財務長簽核 =================
    elif menu == "3. 財務長簽核":
        st.subheader("💰 財務長簽核管理")
        f_db = load_data(); req_db = f_db[f_db["類型"]=="請款單"]
        t1, t2 = st.tabs(["⏳ 待簽核清單", "📜 歷史紀錄 (已核准/已駁回)"])
        with t1:
            pending = req_db[req_db["狀態"] == "待複審"]
            if not is_admin and curr_name != CFO_NAME: pending = pd.DataFrame()
            render_signing_table(pending, "CFO")
        with t2:
            history_cfo = req_db[req_db["狀態"].isin(["已核准", "已駁回"])]
            if not is_admin and curr_name != CFO_NAME: history_cfo = history_cfo[(history_cfo["申請人"] == curr_name) | (history_cfo["代申請人"] == curr_name) | (history_cfo["專案負責人"] == curr_name) | (history_cfo["初審人"] == curr_name)]
            render_signing_table(history_cfo, "CFO", is_history=True)

    # ================= 頁面 4: 總覽 =================
    elif menu == "4. 表單狀態總覽":
        st.subheader("📊 表單狀態總覽")
        f_db = load_data(); my_db = f_db[f_db["類型"]=="請款單"]
        if not is_admin: my_db = my_db[(my_db["申請人"] == curr_name) | (my_db["專案負責人"] == curr_name)]
        st.dataframe(my_db[["單號", "專案名稱", "請款廠商", "總金額", "申請人", "狀態", "付款方式", "匯款狀態", "匯款日期"]], hide_index=True)

    # ================= 頁面 5: 系統設定 =================
    elif menu == "5. 請款狀態/系統設定":
        st.subheader("⚙️ 請款狀態 / 系統設定")
        if is_admin:
            with st.expander("🐙 4. GitHub 自動備份同步設定", expanded=True):
                st.write("設定完成後，每次存檔都會自動覆蓋 GitHub 上的 CSV 檔！(永不遺失)")
                g_token, g_repo = "", ""
                if os.path.exists(G_FILE):
                    try:
                        with open(G_FILE, "r", encoding="utf-8") as f:
                            lines = f.read().splitlines()
                            g_token = "".join(c for c in lines[0] if c.isascii()).strip() if len(lines)>0 else ""
                            g_repo = "".join(c for c in lines[1] if c.isascii()).strip() if len(lines)>1 else ""
                    except: pass
                i_token = st.text_input("GitHub Token (ghp_開頭)", value=g_token, type="password")
                i_repo = st.text_input("GitHub 倉庫名稱 (格式: 帳號/倉庫名，例如 anitalin/timelab-ops)", value=g_repo)
                c_btn1, c_btn2 = st.columns([1, 1])
                if c_btn1.button("💾 測試連線並儲存設定"):
                    clean_token = "".join(c for c in i_token if c.isascii()).strip()
                    clean_repo = "".join(c for c in i_repo if c.isascii()).strip()
                    if not clean_token or not clean_repo: st.error("❌ 請輸入有效的 Token 與倉庫名稱。")
                    else:
                        with open(G_FILE, "w", encoding="utf-8") as f: f.write(f"{clean_token}\n{clean_repo}")
                        try:
                            url = f"https://api.github.com/repos/{clean_repo}"; headers = {"Authorization": f"token {clean_token}"}
                            res = requests.get(url, headers=headers, timeout=5)
                            if res.status_code == 200:
                                st.success("🎉 連線測試成功！自動備份引擎已正式啟動。"); sync_to_github(G_FILE); time.sleep(2); st.rerun()
                            else: st.error(f"❌ 連線被 GitHub 拒絕 (錯誤碼 {res.status_code})。請確認倉庫名稱是否有錯字，或 Token 是否有勾選 'repo' 權限。")
                        except Exception as e: st.error(f"❌ 網路連線異常：{e}")
                st.markdown("---"); st.write("💡 **如果您的舊單據或人員密碼還沒上傳到 GitHub，請點擊下方按鈕強制備份：**")
                if c_btn2.button("🚀 一鍵強制同步所有資料至 GitHub"):
                    with st.spinner("正在將所有資料（包含舊單據與密碼）傳送至 GitHub，請稍候..."):
                        if os.path.exists(D_FILE): sync_to_github(D_FILE)
                        if os.path.exists(S_FILE): sync_to_github(S_FILE)
                        if os.path.exists(P_FILE): sync_to_github(P_FILE)
                        if os.path.exists(V_FILE): sync_to_github(V_FILE)
                        if os.path.exists(L_FILE): sync_to_github(L_FILE) 
                        if os.path.exists(G_FILE): sync_to_github(G_FILE)
                        time.sleep(2) 
                    st.success("✅ 資料庫、人員密碼、專案、廠商與「設定參數」已全部發送至 GitHub 同步！")

            with st.expander("🧰 3. 專案與廠商資料庫 (備份、還原與重建)", expanded=False):
                st.write("💡 **資料不見了怎麼辦？** 如果雲端重啟導致您之前建檔的廠商與專案消失，只要點擊下方按鈕，系統就會自動去「歷史表單 (database.csv)」裡面，把您曾經打過的專案跟廠商全部抓出來重建！")
                if st.button("🪄 一鍵從歷史單據找回/重建專案與廠商"):
                    with st.spinner("正在從歷史單據中打撈資料..."):
                        f_db = load_data()
                        if not f_db.empty:
                            p_data = f_db[["專案負責人", "專案名稱", "專案編號"]].drop_duplicates().dropna()
                            p_data = p_data[(p_data["專案名稱"] != "") & (p_data["專案編號"] != "")].rename(columns={"專案負責人": "負責執行長"})
                            save_projects(pd.concat([load_projects(), p_data]).drop_duplicates(subset=["專案名稱"]).reset_index(drop=True))
                            v_data = f_db[["請款廠商", "匯款帳戶"]].drop_duplicates().dropna()
                            v_data = v_data[(v_data["請款廠商"] != "")]
                            save_vendors(pd.concat([load_vendors(), v_data]).drop_duplicates(subset=["請款廠商"]).reset_index(drop=True))
                            st.success("✅ 太棒了！已成功從歷史單據中找回您的專案與廠商名單，並自動備份到 GitHub！"); time.sleep(2); st.rerun()
                        else: st.warning("⚠️ 目前歷史單據沒有資料，無法打撈。")

            st.error("⚠️ **雲端暫存機制提醒：** 免費雲端主機重啟會清空資料。有設定 GitHub 自動備份則無須擔心！")
            with st.expander("💾 1. 表單資料庫備份與還原", expanded=True):
                col_down, col_up = st.columns(2)
                with col_down:
                    st.write("⬇️ **步驟一：下載最新表單資料庫**")
                    if os.path.exists(D_FILE):
                        with open(D_FILE, "rb") as f: st.download_button("下載表單備份檔", f, file_name=f"時研系統表單備份_{datetime.date.today()}.csv", mime="text/csv")
                with col_up:
                    st.write("⬆️ **步驟二：還原表單資料庫**")
                    up_db = st.file_uploader("上傳表單 CSV 檔", type=["csv"], key="up_db", label_visibility="collapsed")
                    if up_db and st.button("確認還原表單"):
                        with open(D_FILE, "wb") as f: f.write(up_db.getbuffer())
                        st.success("表單資料庫已還原！"); time.sleep(1); st.rerun()
                    
            with st.expander("👥 2. 人員與大頭貼資料備份與還原"):
                col_down2, col_up2 = st.columns(2)
                with col_down2:
                    st.write("⬇️ **步驟一：下載最新人員資料 (含大頭貼與LINE ID)**")
                    if os.path.exists(S_FILE):
                        with open(S_FILE, "rb") as f: st.download_button("下載人員備份檔", f, file_name=f"時研系统人員備份_{datetime.date.today()}.csv", mime="text/csv")
                with col_up2:
                    st.write("⬆️ **步驟二：還原人員資料**")
                    uploaded_staff = st.file_uploader("上傳人員 CSV 檔", type=["csv"], key="up_staff", label_visibility="collapsed")
                    if uploaded_staff and st.button("確認還原人員資料"):
                        with open(S_FILE, "wb") as f: f.write(uploaded_staff.getbuffer())
                        st.session_state.staff_df = load_staff(); st.success("人員資料已還原！"); time.sleep(1); st.rerun()

            with st.expander("🔔 3. LINE 官方帳號推播設定 (全域 Token & 行政副本 ID)", expanded=True):
                st.write("請填寫從 LINE Developers 取得的兩組關鍵代碼：")
                ct, cu = get_line_credentials()
                nt = st.text_input("Channel Access Token (長字串)", value=ct, type="password")
                nu = st.text_input("行政專屬 User ID (U開頭，用來接收所有副本)", value=cu)
                if st.button("💾 儲存 LINE 設定"): save_line_credentials(nt, nu); st.success("LINE 推播設定已成功儲存並啟用！"); time.sleep(1); st.rerun()
            st.divider()

        st.subheader("💰 財務匯款註記")
        f_db = load_data(); df_pay = f_db[f_db["類型"]=="請款單"].copy()
        if not is_admin and curr_name != CFO_NAME: df_pay = df_pay[(df_pay["申請人"] == curr_name) | (df_pay["專案負責人"] == curr_name)]
        
        if not df_pay.empty:
            df_pay["匯款日期"] = pd.to_datetime(df_pay["匯款日期"], errors='coerce').dt.date
            if is_admin:
                ed = st.data_editor(df_pay[["單號", "專案名稱", "請款廠商", "總金額", "匯款狀態", "匯款日期"]], hide_index=True, column_config={"匯款狀態": st.column_config.SelectboxColumn("匯款狀態", options=["尚未匯款", "已匯款"]), "匯款日期": st.column_config.DateColumn("匯款日期", format="YYYY-MM-DD")})
                if st.button("💾 儲存匯款資訊"):
                    for _, row in ed.iterrows(): f_db.loc[f_db["單號"]==row["單號"], ["匯款狀態", "匯款日期"]] = [row["匯款狀態"], str(row["匯款日期"]) if pd.notna(row["匯款日期"]) else ""]
                    save_data(f_db); st.success("已更新"); st.rerun()
            else: st.dataframe(df_pay[["單號", "專案名稱", "請款廠商", "總金額", "匯款狀態", "匯款日期"]], hide_index=True)

    # ================= 全域預覽/列印模組 =================
    if st.session_state.get('req_print_id'):
        r_df = load_data()
        r_df = r_df[r_df["單號"]==st.session_state.req_print_id]
        if not r_df.empty:
            r = r_df.iloc[0]
            html_str = clean_for_js(render_html_with_attachments(r))
            js_code = f"<script>var w=window.open('');w.document.write('{html_str}');w.document.close();setTimeout(function(){{w.print();w.close();}}, 1000);</script>"
            st.components.v1.html(js_code, height=0)
        st.session_state.req_print_id = None

    if st.session_state.req_view_id:
        st.divider()
        r_df = load_data()
        r_df = r_df[r_df["單號"]==st.session_state.req_view_id]
        
        if r_df.empty:
            st.warning("⚠️ 找不到該單號資料，可能已被刪除。")
            if st.button("❌ 關閉預覽"): st.session_state.req_view_id = None; st.rerun()
        else:
            r = r_df.iloc[0]
            if st.button("❌ 關閉預覽"): st.session_state.req_view_id = None; st.rerun()
            
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
                for f_b64 in all_files:
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
