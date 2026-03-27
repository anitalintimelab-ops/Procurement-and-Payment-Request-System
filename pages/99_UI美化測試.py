import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  
import json
import io

# --- 1. 系統鎖定與介面設定 ---
st.session_state['sys_choice'] = "請款單系統"
st.set_page_config(page_title="時研-請款單系統", layout="wide", page_icon="🏢")

# ==========================================
# 🎨 核心 CSS 魔法：深度復刻暗色高級選單
# ==========================================
st.markdown("""
<style>
/* 隱藏預設導覽列與防止 x 軸溢出 */
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
.stApp { overflow-x: hidden; }

/* 🎨 1. 主畫面背景漸變 */
.stApp {
    background: linear-gradient(180deg, #D9EAFB 0%, #EBDCF1 100%);
}

/* 🎨 2. 深度復刻：側邊欄深色背景與文字 */
[data-testid="stSidebar"] {
    background-color: #1A1A1A !important; 
    color: white !important;
}

/* 側邊欄一般文字顏色修正 */
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
    color: #CCCCCC !important; 
}

/* 側邊欄「目前系統」code 標籤美化 */
[data-testid="stSidebar"] code {
    background-color: rgba(255, 255, 255, 0.1) !important;
    color: #007BFF !important; 
    padding: 4px 8px !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
}

/* 側邊欄用戶資訊排版 */
.sb-profile-pic { width: 100px; height: 100px; border-radius: 50%; object-fit: cover; margin: auto; display: block; border: 3px solid #333;}
.sb-name { color: white !important; text-align: center; font-size: 20px; font-weight: bold !important; margin-top: 10px; margin-bottom: 2px;}
.sb-title { color: #888 !important; text-align: center; font-size: 14px; margin-bottom: 15px;}

/* 側邊欄實體按鈕 */
[data-testid="stSidebar"] .stButton > button {
    background-color: #333333 !important; 
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 15px !important;
    width: 100%;
    margin-bottom: 8px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] .stButton > button * {
    color: white !important; 
    font-weight: 600 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #444444 !important;
}

/* 側邊欄選單 (Radio) 深度復刻 (全透明 + 亮藍高亮) */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
    background-color: transparent !important; 
    border-radius: 8px !important;
    padding: 10px 15px !important;
    margin-bottom: 6px !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label * {
    color: #CCCCCC !important; 
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
    background-color: rgba(255, 255, 255, 0.05) !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(div[data-checked="true"]) {
    background-color: #007BFF !important; 
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(div[data-checked="true"]) * {
    color: white !important; 
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stRadio div[data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* 側邊欄分隔線與 Header */
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #666666 !important; 
    font-size: 14px !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    margin-top: 20px;
    margin-bottom: 10px;
}

/* 模擬搜尋列 */
.sb-search-sim {
    background-color: #262626;
    color: #666;
    border-radius: 8px;
    padding: 10px 15px;
    margin-top: 15px;
    margin-bottom: 25px;
    font-size: 14px;
    border: 1px solid #333;
    pointer-events: none; 
}

/* 🎨 3. 主畫面卡片區塊 */
[data-testid="stForm"], div.stExpander > div[role="button"], [data-testid="stDataFrame"] {
    background-color: rgba(240, 244, 248, 0.8) !important;
    backdrop-filter: blur(10px);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.4);
}
[data-testid="stForm"] *, div.stExpander * { color: #1E293B; }

/* 🎨 4. 主畫面輸入框與按鈕 */
.stTextInput input, .stSelectbox div[data-baseweb="select BAS_Web BAS_Select BAS_Select-Input"], .stTextArea textarea, .stNumberInput input {
    border-radius: 10px !important;
    border: 1px solid #CBD5E1 !important;
    background-color: rgba(224, 231, 255, 0.5) !important;
    color: #1E293B !important;
}
.stTextInput input:focus, .stSelectbox div[data-baseweb="select BAS_Web BAS_Select BAS_Select-Input"]:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
    background-color: #ffffff !important;
}
.stButton>button, .stFormSubmitButton>button, .stPopover>button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    border: 1px solid #3b82f6 !important;
    background-color: #ffffff !important;
    color: #00BFFF !important; 
}

/* ★ 手機版防呆 */
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    table { word-wrap: break-word !important; font-size: 13px !important; }
    div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; overflow-x: auto !important; padding-bottom: 5px; }
    div[data-testid="column"] { width: auto !important; flex: 1 1 auto !important; min-width: max-content !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 2. 路徑定位 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) 
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

P_FILE = os.path.join(B_DIR, "projects.csv")
V_FILE = os.path.join(B_DIR, "vendors.csv")

ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

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
        df = df[now - pd.to_numeric(df["time"], errors='coerce').fillna(0) <= 300]
        df.to_csv(O_FILE, index=False)
        return len(df["user"].unique())
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
    try: df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except: st.error("⚠️ 檔案鎖定中！請關閉電腦上的 database.csv。"); st.stop()

def load_staff():
    df = read_csv_robust(S_FILE)
    if df is None or df.empty: return pd.DataFrame({"name": DEFAULT_STAFF, "status":["在職"]*5, "password":["0000"]*5})
    return df

def save_staff(df): df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def load_projects():
    if not os.path.exists(P_FILE):
        pd.DataFrame(columns=["負責執行長", "專案名稱", "專案編號"]).to_csv(P_FILE, index=False, encoding='utf-8-sig')
    return read_csv_robust(P_FILE)

def save_projects(df):
    df.to_csv(P_FILE, index=False, encoding='utf-8-sig')

def load_vendors():
    if not os.path.exists(V_FILE):
        pd.DataFrame(columns=["請款廠商", "匯款帳戶"]).to_csv(V_FILE, index=False, encoding='utf-8-sig')
    return read_csv_robust(V_FILE)

def save_vendors(df):
    df.to_csv(V_FILE, index=False, encoding='utf-8-sig')

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
    h += f'<div style="text-align:center;"><h1 style="margin-bottom:10px;font-size:32px;letter-spacing:2px;color:#000 !important;">Time Lab 時研國際設計股份有限公司</h1></div>'
    h += f'<div style="text-align:center;"><h2 style="margin-top:0px;margin-bottom:15px;font-size:24px;letter-spacing:5px;color:#000 !important;">請款單</h2></div>'
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
    
    h += f'<p style="font-size:15px;margin-top:20px;line-height:1.6;color:#000 !important;">提交: {s_submit} | 初審: {s_first} | 複審: {s_second}</p></div>'
    return h

def clean_for_js(h_str): return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# --- 6. Session 初始化 ---
if st.session_state.get('user_id') is None: st.switch_page("app.py")
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()

for k in ['req_edit_id', 'req_last_id', 'req_view_id', 'req_print_id', 'req_last_msg']: 
    if k not in st.session_state: st.session_state[k] = None

if 'req_uploader_key' not in st.session_state: st.session_state.req_uploader_key = 0

curr_name, is_admin = st.session_state.user_id, (st.session_state.user_id in ADMINS)
is_active = (st.session_state.user_status == "在職")

# --- 7. 深色復刻側邊欄 ---
with st.sidebar:
    avatar_b64 = ""
    try: 
        avatar_b64 = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0].get("avatar", "")
    except: 
        pass
    
    if avatar_b64:
        st.markdown(f'<img src="data:image/jpeg;base64,{avatar_b64}" class="sb-profile-pic">', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="sb-profile-pic" style="background:#555; display:flex; align-items:center; justify-content:center; color:#aaa; font-size:40px;">{curr_name[0]}</div>', unsafe_allow_html=True)
        
    st.markdown(f'<p class="sb-name">{curr_name}</p>', unsafe_allow_html=True)
    
    title = "管理員 / 設計總監" if is_admin else "在職人員 / 設計師"
    st.markdown(f'<p class="sb-title">{title}</p>', unsafe_allow_html=True)
    
    with st.expander("👤 用戶與系統設定"):
        st.info(f"🟢 在線：**{get_online_users(curr_name)}** 人")
        st.markdown(f"目前系統：`{st.session_state.sys_choice}`")
        st.divider()

        f_av = st.file_uploader("📸 修改頭貼", type=["jpg", "png"], key="av_up")
        if f_av and st.button("更新頭貼", key="av_btn"):
            s_df = load_staff()
            idx = s_df[s_df["name"] == curr_name].index[0]
            s_df.at[idx, "avatar"] = base64.b64encode(f_av.getvalue()).decode()
            save_staff(s_df)
            st.rerun()

        f_pw = st.text_input("🔐 修改密碼", type="password", key="pw_in")
        if f_pw and st.button("更新密碼", key="pw_btn") and len(f_pw) >= 4:
            s_df = load_staff()
            idx = s_df[s_df["name"] == curr_name].index[0]
            s_df.at[idx, "password"] = str(f_pw)
            save_staff(s_df)
            st.success("已更新")
            
        if is_admin:
            st.divider()
            st.write("🔑 **管理員專區**")
            rt = st.selectbox("重置密碼 (0000)", s_df["name"].tolist(), key="rt_sel")
            if st.button("確認重置", key="rt_btn"):
                s_df = load_staff()
                idx = s_df[s_df["name"] == rt].index[0]
                s_df.at[idx, "password"] = "0000"
                save_staff(s_df)
                st.success("已重置")
            
            nt = st.text_input("➕ 新增人員姓名", key="nt_in")
            if st.button("確認新增", key="nt_btn") and nt and nt not in s_df["name"].values:
                new_s = pd.DataFrame([{"name": nt, "status": "在職", "password": "0000"}])
                pd.concat([load_staff(), new_s], ignore_index=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')
                st.rerun()
            
            es = st.data_editor(s_df[["name", "status"]], hide_index=True, column_config={"status": st.column_config.SelectboxColumn(options=["在職", "離職"])}, key="es_dt")
            if st.button("💾 儲存人員狀態", key="es_btn"):
                pd.merge(load_staff().drop(columns="status"), es, on="name").to_csv(S_FILE, index=False, encoding='utf-8-sig')
                st.rerun()

    if st.button("登出系統", key="req_logout"): 
        st.session_state.user_id = None
        st.switch_page("app.py")

    st.markdown('<div class="sb-search-sim">🔍 搜尋請款單號/專案名稱...</div>', unsafe_allow_html=True)
    
    st.markdown("### 管理")
    menu_options = ["填寫請款申請單", "專案執行長簽核", "財務長簽核", "表單狀態總覽", "請款狀態/系統設定"]
    menu_map = {"填寫請款申請單":"1. 填寫申請單", "專案執行長簽核":"2. 專案執行長簽核", "財務長簽核":"3. 財務長簽核", "表單狀態總覽":"4. 表單狀態總覽", "請款狀態/系統設定":"5. 請款狀態/系統設定"}
    
    menu_sel_raw = st.radio("導覽", menu_options, key="radio_menu", label_visibility="collapsed")
    menu = menu_map[menu_sel_raw]

# --- 7.1 處理頁面切換 ---
if "req_prev_state_menu" not in st.session_state: 
    st.session_state.req_prev_state_menu = menu
if menu != st.session_state.req_prev_state_menu: 
    st.session_state.req_view_id = None
    st.session_state.req_print_id = None
    st.session_state.req_edit_id = None
    st.session_state.req_prev_state_menu = menu
    st.rerun()

# ================= 簽核列表渲染模組 =================
def render_signing_table(df_list, sign_type, is_history=False):
    if df_list.empty: 
        st.info("目前無相關紀錄")
        return
    show_exe = not (sign_type == "EXE" and not is_admin)
    cols_header = st.columns([1.2, 2.0, 1.2, 1.2, 1.2, 3.0]) if show_exe else st.columns([1.2, 2.0, 1.2, 1.2, 3.0])
    headers = ["單號", "專案名稱", "執行長", "申請人", "金額", "操作"] if show_exe else ["單號", "專案名稱", "申請人", "金額", "操作"]
    for c, h in zip(cols_header, headers): c.write(f"**{h}**")
    
    for i, r in df_list.iterrows():
        cols = st.columns([1.2, 2.0, 1.2, 1.2, 1.2, 3.0]) if show_exe else st.columns([1.2, 2.0, 1.2, 1.2, 3.0])
        cols[0].write(r["單號"]); cols[1].write(r["專案名稱"])
        if show_exe: 
            cols[2].write(clean_name(r["專案負責人"]))
            cols[3].write(r["申請人"])
            cols[4].write(f"${clean_amount(r['總金額']):,}")
            btn_c = cols[5]
        else: 
            cols[2].write(r["申請人"])
            cols[3].write(f"${clean_amount(r['總金額']):,}")
            btn_c = cols[4]
            
        with btn_c:
            b1, b2, b3 = st.columns(3)
            if b1.button("預覽", key=f"v_{sign_type}_{i}"): 
                st.session_state.req_view_id = r["單號"]
                st.rerun()
            if not is_history:
                can_sign = (r["專案負責人"] == curr_name if sign_type == "EXE" else curr_name == CFO_NAME) and is_active
                if b2.button("✅ 核准", key=f"ok_{sign_type}_{i}", disabled=not can_sign):
                    fresh_db = load_data()
                    idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    if sign_type == "EXE": 
                        fresh_db.loc[idx, ["狀態", "初審人", "初審時間"]] = ["待複審", curr_name, get_taiwan_time()]
                    else: 
                        fresh_db.loc[idx, ["狀態", "複審人", "複審時間"]] = ["已核准", curr_name, get_taiwan_time()]
                    save_data(fresh_db)
                    st.rerun()
                if can_sign:
                    with b3.popover("❌ 駁回"):
                        reason = st.text_input("原因", key=f"rj_{sign_type}_{i}")
                        if st.button("確認驳回", key=f"rjb_{sign_type}_{i}"):
                            fresh_db = load_data()
                            idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                            fresh_db.loc[idx, ["狀態", "駁回原因", "初審人" if sign_type=="EXE" else "複審人", "初審時間" if sign_type=="EXE" else "複審時間"]] = ["已駁回", reason, curr_name, get_taiwan_time()]
                            save_data(fresh_db)
                            st.rerun()
                else: 
                    b3.button("❌ 駁回", disabled=True, key=f"fjr_{sign_type}_{i}")
            else: 
                b2.write(f"[{r['狀態']}]")

# ================= 頁面邏輯 =================
# ★ 全域主畫面正中間置頂 Logo (完美復刻圖片 Time Lab排版)
st.markdown("""
    <div style='text-align: center; margin-bottom: 40px; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 15px; flex-wrap: wrap;'>
        <span style='font-size: 38px; font-weight: 500; font-family: "Times New Roman", Times, serif; color: #3E3024;'>T<span style='color: #C19A6B;'>i</span>me Lab</span>
        <span style='font-size: 32px; font-weight: 900; color: #2C3E50; letter-spacing: 1px; font-family: "Microsoft JhengHei", "PingFang TC", sans-serif;'>時研國際設計股份有限公司</span>
    </div>
""", unsafe_allow_html=True)

if menu == "1. 填寫申請單":
    st.subheader("📝 填寫請款申請單")
    if st.session_state.get('req_last_msg'): 
        st.success(st.session_state.req_last_msg)
        st.session_state.req_last_msg = None
        
    p_db = load_projects()
    v_db = load_vendors()
    
    with st.expander("➕ 新增專案 / 廠商"):
        t1, t2 = st.tabs(["📂 新增專案", "🏢 新增廠商"])
        with t1:
            pc = st.columns([1, 2, 2, 1])
            np_exe = pc[0].selectbox("負責執行長", st.session_state.staff_df["name"].apply(clean_name).tolist())
            np_name = pc[1].text_input("專案名稱")
            np_id = pc[2].text_input("專案編號")
            if pc[3].button("➕ 儲存專案") and np_name and np_id: 
                pd.concat([load_projects(), pd.DataFrame([{"負責執行長": np_exe, "專案名稱": np_name, "專案編號": np_id}])], ignore_index=True).to_csv(P_FILE, index=False, encoding='utf-8-sig')
                st.rerun()
        with t2:
            vc = st.columns([2, 2, 1])
            nv_name = vc[0].text_input("廠商名稱")
            nv_acc = vc[1].text_input("匯款帳戶")
            if vc[2].button("➕ 儲存廠商") and nv_name and nv_acc: 
                pd.concat([load_vendors(), pd.DataFrame([{"請款廠商": nv_name, "匯款帳戶": nv_acc}])], ignore_index=True).to_csv(V_FILE, index=False, encoding='utf-8-sig')
                st.rerun()

    db = load_data()
    staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
    dv = {"app": curr_name, "pn": "", "pi": "", "exe": staffs[0], "net": 0, "tax": 0, "desc": "", "ib64": "", "cur": "TWD", "ab64":"", "vdr":"", "acc":"", "pay":"匯款(扣30手續費)", "inv":"", "ac_n":"", "ims_n":[]}
    
    if st.session_state.req_edit_id:
        r_ = db[db["單號"]==st.session_state.req_edit_id].iloc[0]
        jd_ = parse_req_json(r_["請款說明"])
        dv.update({
            "app": r_["申請人"], "pn": r_["專案名稱"], "pi": r_["專案編號"], "exe": r_["專案負責人"], 
            "net": jd_["net_amt"], "tax": jd_["tax_amt"], "desc": jd_["desc"], 
            "ib64": r_["影像Base64"], "cur": r_.get("幣別","TWD"), "ab64": r_["帳戶影像Base64"], 
            "vdr": r_.get("請款廠商",""), "acc": r_.get("匯款帳戶",""), "pay": r_.get("付款方式","匯款(扣30手續費)"), 
            "inv": jd_["inv_no"], "ac_n": jd_["acc_name"], "ims_n": jd_["ims_names"]
        })

    c = st.columns(4)
    app = c[0].selectbox("申請人", staffs, index=staffs.index(dv["app"]) if dv["app"] in staffs else 0) if is_admin else curr_name
    if not is_admin: c[0].text_input("申請人", value=app, disabled=True)
    exe = c[1].selectbox("執行長", staffs, index=staffs.index(dv["exe"]) if dv["exe"] in staffs else 0)
    
    p_names = p_db[p_db["負責執行長"] == exe]["專案名稱"].unique().tolist()
    p_opts = [""] + p_names + ["➕ 手動輸入"]
    pn_idx = p_opts.index(dv["pn"]) if dv["pn"] in p_names else p_opts.index("➕ 手動輸入") if dv["pn"] else 0
    pn_s = c[2].selectbox("專案", p_opts, index=pn_idx)
    pn = c[2].text_input("✍️ 專案名稱", dv["pn"] if dv["pn"] not in p_names else "") if pn_s == "➕ 手動輸入" else pn_s
    pi = c[3].text_input("專案編號", p_db[p_db["專案名稱"] == pn]["專案編號"].iloc[0] if pn in p_names else dv["pi"])
    
    cx = st.columns(4)
    cur = cx[0].selectbox("幣別", ["TWD", "USD", "EUR"], index=["TWD", "USD", "EUR"].index(dv["cur"]) if dv["cur"] in ["TWD", "USD", "EUR"] else 0)
    net = cx[1].number_input("未稅", value=int(dv["net"]), min_value=0)
    tax = cx[2].number_input("稅額", value=int(dv["tax"]), min_value=0)
    cx[3].text_input("總額", f"{int(net+tax):,}", disabled=True)
    
    v_names = v_db["請款廠商"].unique().tolist()
    v_opts = [""] + v_names + ["➕ 手動輸入"]
    vdr_idx = v_opts.index(dv["vdr"]) if dv["vdr"] in v_names else v_opts.index("➕ 手動輸入") if dv["vdr"] else 0
    vd_s = st.columns(3)[0].selectbox("廠商", v_opts, index=vdr_idx)
    
    cv1, cv2, cv3 = st.columns(3)
    vdr = cv1.text_input("✍️ 廠商名稱", dv["vdr"] if dv["vdr"] not in v_names else "") if vd_s == "➕ 手動輸入" else vd_s
    acc = cv2.text_input("匯款帳戶", v_db[v_db["請款廠商"] == vdr]["匯款帳戶"].iloc[0] if vdr in v_names else dv["acc"])
    inv = cv3.text_input("發票/憑證號", dv["inv"])
    
    pay_opt = ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"]
    pay = st.radio("付款", pay_opt, index=pay_opt.index(dv["pay"]) if dv["pay"] in pay_opt else 2, horizontal=True)
    desc = st.text_area("說明", dv["desc"])
    st.info("💡 總額 = 未稅 + 稅額。選擇扣30手續費會自動於存檔時減 30。")
    
    up_k = st.session_state.req_uploader_key
    f_a = st.file_uploader("存摺", type=["png", "jpg", "xlsx", "xls"], key=f"f_a_{up_k}")
    f_i = st.file_uploader("憑證", type=["png", "jpg", "xlsx", "xls"], accept_multiple_files=True, key=f"f_i_{up_k}")
    
    d_a, d_i = False, []
    if st.session_state.req_edit_id:
        with st.expander("🗑️ 管理現有附件"):
            if dv["ab64"]:
                d_a = st.checkbox(f"刪除 {dv['ac_n'] if dv['ac_n'] else '存摺'}")
            if dv["ib64"]:
                ims = dv["ib64"].split('|')
                ims_n = dv["ims_n"]
                for idx_i, _ in enumerate(ims):
                    name = ims_n[idx_i] if idx_i < len(ims_n) else f"舊檔{idx_i+1}"
                    if st.checkbox(f"刪除 {name}", key=f"d_i_{idx_i}"): 
                        d_i.append(idx_i)

    if st.session_state.req_edit_id:
        cb = st.columns(6)
        b_sv = cb[0].button("💾 存檔", use_container_width=True)
        b_sb = cb[1].button("🚀 提交", use_container_width=True)
        b_pv = cb[2].button("🔍 預覽", use_container_width=True)
        b_pt = cb[3].button("🖨️ 列印", use_container_width=True)
        b_nx = cb[4].button("🆕 下一筆", use_container_width=True)
        b_cn = cb[5].button("❌ 不存檔", use_container_width=True)
    else:
        cb = st.columns(5)
        b_sv = cb[0].button("💾 存檔", use_container_width=True)
        b_sb = cb[1].button("🚀 提交", use_container_width=True)
        b_pv = cb[2].button("🔍 預覽", use_container_width=True)
        b_pt = cb[3].button("🖨️ 列印", use_container_width=True)
        b_nx = cb[4].button("🆕 下一筆", use_container_width=True)
        b_cn = False

    if b_cn: 
        st.session_state.req_edit_id = None
        st.session_state.req_uploader_key += 1
        st.rerun()
        
    if b_nx: 
        st.session_state.req_edit_id = None
        st.session_state.req_uploader_key += 1
        st.rerun()
        
    if (b_sv or b_sb or b_pv or b_pt):
        if not pn or net+tax <= 0:
            st.error("⚠️ 請填寫專案名稱且金額需大於0")
        else:
            fee = 30 if "扣30" in pay else 0
            total = net + tax - fee
            
            b_a = base64.b64encode(f_a.getvalue()).decode() if f_a else "" if d_a else dv["ab64"]
            a_n = f_a.name if f_a else "" if d_a else dv["ac_n"]
            
            o_ims = dv["ib64"].split('|') if dv["ib64"] else []
            o_ims_n = dv["ims_n"]
            
            r_ims = [img for idx, img in enumerate(o_ims) if idx not in d_i]
            r_ims_n = [name for idx, name in enumerate(o_ims_n) if idx not in d_i]
            
            n_ims = [base64.b64encode(f.getvalue()).decode() for f in f_i] if f_i else []
            n_ims_n = [f.name for f in f_i] if f_i else []
            
            f_ims = "|".join(r_ims + n_ims)
            f_ims_n = r_ims_n + n_ims_n
            
            pk_desc = "[請款單資料]\n" + json.dumps({"net_amt":net,"tax_amt":tax,"fee":fee,"inv_no":inv,"desc":desc,"acc_name":a_n,"ims_names":f_ims_n}, ensure_ascii=False)
            f_db = load_data()
            prox = curr_name if app!=curr_name else ""
            
            if st.session_state.req_edit_id:
                tid = st.session_state.req_edit_id
                idx = f_db[f_db["單號"]==tid].index[0]
                f_db.loc[idx, ["申請人", "代申請人", "專案名稱", "專案編號", "專案負責人", "總金額", "請款說明", "請款廠商", "匯款帳戶", "付款方式", "影像Base64", "帳戶影像Base64", "幣別", "狀態"]] = [app, prox, pn, pi, exe, total, pk_desc, vdr, acc, pay, f_ims, b_a, cur, "已存檔未提交"]
            else:
                tid = f"{datetime.date.today().strftime('%Y%m%d')}-{len(f_db[f_db['單號'].str.startswith(datetime.date.today().strftime('%Y%m%d'))])+1:02d}"
                f_db = pd.concat([f_db, pd.DataFrame([{"單號":tid,"日期":str(datetime.date.today()),"類型":"請款單","申請人":app,"代申請人":prox,"專案負責人":exe,"專案名稱":pn,"專案編號":pi,"請款說明":pk_desc,"總金額":total,"幣別":cur,"請款廠商":vdr,"匯款帳戶":acc,"付款方式":pay,"狀態":"已存檔未提交","影像Base64":f_ims,"帳戶影像Base64":b_a}])], ignore_index=True)
            
            save_data(f_db)
            
            if b_sb: 
                f_db = load_data()
                idx = f_db[f_db["單號"]==tid].index[0]
                f_db.loc[idx, ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]
                save_data(f_db)
                st.session_state.req_edit_id = None
                st.success(f"🚀 {tid} 已提交")
            else: 
                st.session_state.req_edit_id = tid
                st.session_state.req_last_msg = f"📄 {tid} 已存檔"
                
            if b_pv: st.session_state.req_view_id = tid
            if b_pt: st.session_state.req_print_id = tid
            
            st.session_state.req_uploader_key += 1
            st.rerun()

    st.divider()
    st.subheader("📋 申請追蹤")
    my_db = load_data()[load_data()["類型"]=="請款單"]
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    
    cols_h = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
    for c,h in zip(cols_h, ["單號", "專案", "執行長", "申請人", "金額", "狀態", "操作"]): c.write(f"**{h}**")
    
    for i, r in my_db.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        c[0].write(r["單號"])
        c[1].write(r["專案名稱"])
        c[2].write(clean_name(r["專案負責人"]))
        c[3].write(r["申請人"])
        c[4].write(f"${clean_amount(r['總金額']):,}")
        s_r = safe_str(r.get("狀態"))
        color = "blue" if s_r in ["已存檔未提交","已儲存"] else "orange" if "待" in s_r else "green" if s_r=="已核准" else "red"
        c[5].markdown(f":{color}[**{s_r}**]")
        
        with c[6]:
            b1, b2, b3, b4, b5, b6 = st.columns(6)
            can_e = s_r in ["已儲存", "已存檔未提交", "已駁回"] and is_active
            
            if b1.button("🚀", key=f"s{i}", disabled=not can_e): 
                fresh_db = load_data()
                fresh_db.loc[fresh_db["單號"]==r["單號"], ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]
                save_data(fresh_db)
                st.rerun()
                
            if b2.button("🔍", key=f"v{i}"): 
                st.session_state.req_view_id = r["單號"]
                st.rerun()
                
            if b3.button("🖨️", key=f"p{i}"): 
                st.components.v1.html(f"<script>window.open().document.write('{clean_for_js(render_html(r))}');window.close();</script>", height=0)
                
            if b4.button("✍️", key=f"e{i}", disabled=not can_e): 
                st.session_state.req_edit_id = r["單號"]
                st.rerun()
                
            if b5.button("🗑️", key=f"d{i}", disabled=not can_e): 
                fresh_db = load_data()
                fresh_db.loc[fresh_db["單號"]==r["單號"], ["狀態"]] = ["已刪除"]
                save_data(fresh_db)
                st.rerun()

elif menu == "2. 專案執行長簽核":
    st.subheader("👨‍💼 專案執行長簽核")
    db_ = load_data()[load_data()["類型"]=="請款單"]
    render_signing_table(db_[db_["狀態"].isin(["待簽核","待初審"])], "EXE")
    render_signing_table(db_[db_["狀態"].isin(["已核准","已駁回","待複審"])], "EXE", is_history=True)

elif menu == "3. 財務長簽核":
    st.subheader("💰 財務長簽核")
    db_ = load_data()[load_data()["類型"]=="請款單"]
    render_signing_table(db_[db_["狀態"]=="待複審"], "CFO")
    render_signing_table(db_[db_["狀態"].isin(["已核准","已駁回"])], "CFO", is_history=True)

elif menu == "4. 表單狀態總覽":
    st.subheader("📊 表單狀態總覽")
    st.dataframe(load_data(), hide_index=True)

elif menu == "5. 請款狀態/系統設定":
    st.subheader("⚙️ 系統設定")
    if is_admin:
        col1, col2 = st.columns(2)
        with col1:
            st.write("💾 **備份資料庫**")
            if os.path.exists(D_FILE): 
                with open(D_FILE, "rb") as f: 
                    st.download_button("下載 database.csv", f, "database_bak.csv")
        with col2:
            st.write("⬆️ **還原資料庫**")
            u_d = st.file_uploader("上傳 CSV")
            if u_d and st.button("確認還原"): 
                with open(D_FILE, "wb") as f: 
                    f.write(u_d.getvalue())
                st.rerun()

# --- 8. 全域預覽/列印 ---
if st.session_state.get('req_print_id'):
    r_df = load_data()
    r_df = r_df[r_df["單號"]==st.session_state.req_print_id]
    if not r_df.empty: 
        st.components.v1.html(f"<script>window.open().document.write('{clean_for_js(render_html(r_df.iloc[0]))}');window.close();</script>", height=0)
    st.session_state.req_print_id = None

if st.session_state.req_view_id:
    st.divider()
    r_df = load_data()
    r_df = r_df[r_df["單號"]==st.session_state.req_view_id]
    if r_df.empty: 
        st.warning("找不到資料")
    else:
        r_ = r_df.iloc[0]
        st.markdown(render_html(r_), unsafe_allow_html=True)
        all_f = []
        if safe_str(r_.get("帳戶影像Base64")): 
            all_f.append(safe_str(r_.get("帳戶影像Base64")))
        if safe_str(r_.get("影像Base64")): 
            all_f.extend(safe_str(r_.get("影像Base64")).split('|'))
            
        if all_f: 
            st.write("#### 📎 附件預覽")
            for f_ in all_f:
                try: 
                    raw_ = base64.b64decode(f_)
                    if raw_.startswith(b'PK') or raw_.startswith(b'\xd0\xcf\x11\xe0'): 
                        st.info("Excel 檔案")
                        st.dataframe(pd.read_excel(io.BytesIO(raw_)))
                    else: 
                        st.image(raw_)
                except: 
                    pass
                    
        if st.button("❌ 關閉預覽"): 
            st.session_state.req_view_id = None
            st.rerun()
