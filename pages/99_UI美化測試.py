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
# 🎨 核心 CSS 魔法：仿照範例色彩主題 + 立體按鈕 + 手機防呆
# ==========================================
st.markdown("""
<style>
/* 隱藏預設導覽列與防止 x 軸溢出 */
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
.stApp { overflow-x: hidden; }

/* 🎨 1. 整體背景漸變 */
.stApp {
    background: linear-gradient(180deg, #D9EAFB 0%, #EBDCF1 100%);
}

/* 🎨 2. 側邊欄背景漸變 (深紫到深藍) */
[data-testid="stSidebar"] {
    background: linear-gradient(135deg, #4A00E0 0%, #8E2DE2 100%), radial-gradient(circle at 70% 30%, rgba(255, 255, 255, 0.1) 0%, transparent 40%);
    background-blend-mode: overlay;
}

/* ★ 修正：確保側邊欄文字是白色，但不影響特殊按鈕 */
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: white !important;
}

/* ★ 修正：「目前系統」標籤 (code) 獨立美化，避免隱形 */
[data-testid="stSidebar"] code {
    background-color: rgba(255, 255, 255, 0.95) !important;
    color: #4A00E0 !important;
    padding: 6px 12px !important;
    border-radius: 8px !important;
    font-weight: 800 !important;
    font-size: 15px !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15) !important;
}

/* ★ 修正：側邊欄導覽選單 (Radio) 化身 3D 立體按鈕 */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
    background-color: rgba(255, 255, 255, 0.1) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    border-radius: 12px !important;
    padding: 12px 15px !important;
    margin-bottom: 10px !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
/* 滑鼠移過去：微亮、上浮 */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
    background-color: rgba(255, 255, 255, 0.25) !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
}
/* 點選中(Active)：變成實體白底＋深紫文字＋內陰影按下感 */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(div[data-checked="true"]) {
    background-color: white !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.1) !important;
    transform: translateY(2px) !important;
    border: 1px solid white !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(div[data-checked="true"]) * {
    color: #4A00E0 !important;
    font-weight: 800 !important;
}
/* 隱藏原生 Radio 的醜圓圈圈 */
[data-testid="stSidebar"] .stRadio div[data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* ★ 修正：「登出系統」等側邊欄實體按鈕顏色 */
[data-testid="stSidebar"] .stButton > button {
    background-color: rgba(255, 255, 255, 0.2) !important;
    border: 1px solid rgba(255, 255, 255, 0.5) !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    transition: all 0.2s ease !important;
}
/* 預設字體為白色，不用碰觸就看得見 */
[data-testid="stSidebar"] .stButton > button * {
    color: white !important; 
    font-weight: 700 !important;
}
/* 滑鼠碰觸：變白底、字變深紫 */
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: white !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.2) !important;
}
[data-testid="stSidebar"] .stButton > button:hover * {
    color: #4A00E0 !important; 
}

/* 🎨 3. 主畫面卡片區塊 (半透明淡藍色，backdrop-filter) */
[data-testid="stForm"], div.stExpander > div[role="button"], [data-testid="stDataFrame"] {
    background-color: rgba(240, 244, 248, 0.8) !important;
    backdrop-filter: blur(10px);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.4);
}
/* 確保卡片內文字顏色為深色 */
[data-testid="stForm"] *, div.stExpander * {
    color: #1E293B;
}

/* 🎨 4. 輸入框與按鈕質感 */
.stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stNumberInput input {
    border-radius: 10px !important;
    border: 1px solid #CBD5E1 !important;
    background-color: rgba(224, 231, 255, 0.5) !important;
    color: #1E293B !important;
    transition: all 0.3s ease;
}
.stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
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
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
}
.stButton>button:hover, .stFormSubmitButton>button:hover, .stPopover>button:hover {
    background-color: rgba(0, 191, 255, 0.1) !important;
    border-color: #3b82f6 !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
    color: #00BFFF !important;
}

/* ★ 手機版防呆保留原樣 */
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    table { word-wrap: break-word !important; font-size: 13px !important; }
    th, td { padding: 5px !important; }
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

# --- 6. Session 初始化 ---
if st.session_state.get('user_id') is None: st.switch_page("app.py")
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()

for k in ['req_edit_id', 'req_last_id', 'req_view_id', 'req_print_id', 'req_last_msg']: 
    if k not in st.session_state: st.session_state[k] = None

if 'req_uploader_key' not in st.session_state: st.session_state.req_uploader_key = 0

curr_name, is_admin = st.session_state.user_id, (st.session_state.user_id in ADMINS)
is_active = (st.session_state.user_status == "在職")

# --- 7. 左側側邊欄 ---
st.sidebar.markdown(f"**📌 目前系統：** `{st.session_state.sys_choice}`")
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
    st.sidebar.success("管理員專屬區塊 (已解鎖)")
    
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
        if st.button("新增", key="req_add_staff"):
            s_df = load_staff()
            if n and n not in s_df["name"].values:
                new_row = pd.DataFrame([{"name": n, "status": "在職", "password": "0000", "avatar": "", "line_uid": ""}])
                s_df = pd.concat([s_df, new_row], ignore_index=True)
                save_staff(s_df)
                st.session_state.staff_df = s_df
                st.success("人員新增成功")
                st.rerun()
            elif n in s_df["name"].values:
                st.error("人員已存在")

    with st.sidebar.expander("⚙️ 人員設定 (狀態 & LINE ID)"):
        edited_staff = st.data_editor(
            st.session_state.staff_df[["name", "status", "line_uid"]], 
            column_config={
                "name": st.column_config.TextColumn("姓名", disabled=True),
                "status": st.column_config.SelectboxColumn("狀態", options=["在職", "離職"])
            }, 
            hide_index=True, 
            key="req_staff_editor_admin"
        )
        if st.button("💾 儲存人員設定", key="req_save_staff_admin"):
            s_df = load_staff()
            for idx, row in edited_staff.iterrows():
                s_df.at[idx, "status"] = row["status"]
                s_df.at[idx, "line_uid"] = str(row["line_uid"]).strip() if pd.notna(row["line_uid"]) else ""
            save_staff(s_df)
            st.session_state.staff_df = s_df
            st.rerun()

if st.sidebar.button("登出系統", key="req_logout"): st.session_state.user_id = None; st.switch_page("app.py")

menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽", "5. 請款狀態/系統設定"]
menu = st.sidebar.radio("導覽", menu_options, key="req_menu_radio")

if "req_prev_state_menu" not in st.session_state:
    st.session_state.req_prev_state_menu = menu
if "req_prev_state_user" not in st.session_state:
    st.session_state.req_prev_state_user = st.session_state.user_id

if menu != st.session_state.req_prev_state_menu or st.session_state.user_id != st.session_state.req_prev_state_user:
    st.session_state.req_view_id = None
    st.session_state.req_print_id = None
    st.session_state.req_edit_id = None
    st.session_state.req_prev_state_menu = menu
    st.session_state.req_prev_state_user = st.session_state.user_id
    st.rerun()


# --- 8. 簽核列表渲染模組 ---
def render_signing_table(df_list, sign_type, is_history=False):
    if df_list.empty:
        st.info("目前無相關紀錄")
        return
    
    show_exe = True
    if sign_type == "EXE" and not is_admin:
        show_exe = False
        
    if show_exe:
        cols_header = st.columns([1.2, 2.0, 1.2, 1.2, 1.2, 3.0])
        headers = ["單號", "專案名稱", "負責執行長", "申請人", "請款金額", "操作"]
    else:
        cols_header = st.columns([1.2, 2.0, 1.2, 1.2, 3.0])
        headers = ["單號", "專案名稱", "申請人", "請款金額", "操作"]
        
    for c, h in zip(cols_header, headers): c.write(f"**{h}**")
    
    for i, r in df_list.iterrows():
        if show_exe:
            c = st.columns([1.2, 2.0, 1.2, 1.2, 1.2, 3.0])
            c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"])
            c[4].write(f"${clean_amount(r['總金額']):,}")
            btn_c = c[5]
        else:
            c = st.columns([1.2, 2.0, 1.2, 1.2, 3.0])
            c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(r["申請人"])
            c[3].write(f"${clean_amount(r['總金額']):,}")
            btn_c = c[4]
            
        with btn_c:
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            if btn_col1.button("預覽", key=f"sv_{sign_type}_{i}_{is_history}"):
                st.session_state.req_view_id = r["單號"]; st.rerun()
            
            if not is_history:
                can_sign = (r["專案負責人"] == curr_name if sign_type == "EXE" else curr_name == CFO_NAME) and is_active
                if btn_col2.button("✅ 核准", key=f"sok_{sign_type}_{i}", disabled=not can_sign):
                    fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    if sign_type == "EXE":
                        fresh_db.loc[idx, ["狀態", "初審人", "初審時間"]] = ["待複審", curr_name, get_taiwan_time()]
                        sys_name = st.session_state.get('sys_choice', '請款單系統')
                        send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{r['單號']}\n專案名稱：{r['專案名稱']}\n執行長已核准，有一筆表單需要財務長 ({CFO_NAME}) 進行簽核！")
                    else:
                        fresh_db.loc[idx, ["狀態", "複審人", "複審時間"]] = ["已核准", curr_name, get_taiwan_time()]
                    save_data(fresh_db); st.success("已核准！"); time.sleep(0.5); st.rerun()
                
                if can_sign:
                    with btn_col3.popover("❌ 駁回"):
                        reason = st.text_input("駁回原因", key=f"sr_{sign_type}_{i}")
                        if st.button("確認", key=f"sno_{sign_type}_{i}"):
                            fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                            field_prefix = "初審" if sign_type == "EXE" else "複審"
                            fresh_db.loc[idx, ["狀態", "駁回原因", f"{field_prefix}人", f"{field_prefix}時間"]] = ["已駁回", reason, curr_name, get_taiwan_time()]
                            save_data(fresh_db); st.rerun()
                else:
                    btn_col3.button("❌ 駁回", disabled=True, key=f"fk_sno_{sign_type}_{i}")
            else:
                btn_col2.write(f"[{r['狀態']}]")

# ================= 頁面邏輯 =================
# ★ 新增：全域主畫面正中間置頂 Logo
st.markdown("<h1 style='text-align: center; color: #1e293b; font-weight: 800; letter-spacing: 2px; margin-bottom: 30px;'>🏢 時研國際設計股份有限公司</h1>", unsafe_allow_html=True)

if menu == "1. 填寫申請單":
    st.subheader("📝 填寫請款申請單")
    
    if st.session_state.get('req_last_msg'):
        st.success(st.session_state.req_last_msg)
        st.session_state.req_last_msg = None

    p_db = load_projects()
    v_db = load_vendors()

    with st.expander("➕ 新增專案 / 廠商至資料庫"):
        tb1, tb2 = st.tabs(["📂 新增專案", "🏢 新增廠商"])
        with tb1:
            pc1, pc2, pc3, pc4 = st.columns([1, 2, 2, 1])
            new_p_exe = pc1.selectbox("所屬執行長", st.session_state.staff_df["name"].apply(clean_name).tolist(), key="new_p_exe")
            new_p_name = pc2.text_input("新專案名稱", key="new_p_name")
            new_p_id = pc3.text_input("新專案編號", key="new_p_id")
            if pc4.button("➕ 儲存專案"):
                if new_p_name and new_p_id:
                    p_db = load_projects()
                    p_db = pd.concat([p_db, pd.DataFrame([{"負責執行長": new_p_exe, "專案名稱": new_p_name, "專案編號": new_p_id}])], ignore_index=True)
                    save_projects(p_db)
                    st.success(f"已存入 {new_p_name} 資料庫！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("請填寫完整資訊")
        with tb2:
            vc1, vc2, vc3 = st.columns([2, 2, 1])
            new_v_name = vc1.text_input("新廠商名稱", key="new_v_name")
            new_v_acc = vc2.text_input("新匯款帳戶", key="new_v_acc")
            if vc3.button("➕ 儲存廠商"):
                if new_v_name and new_v_acc:
                    v_db = load_vendors()
                    v_db = pd.concat([v_db, pd.DataFrame([{"請款廠商": new_v_name, "匯款帳戶": new_v_acc}])], ignore_index=True)
                    save_vendors(v_db)
                    st.success(f"已存入 {new_v_name} 資料庫！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("請填寫完整資訊")

    db = load_data(); staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
    
    dv = {"app": curr_name, "pn": "", "pi": "", "exe": staffs[0], "net_amt": 0, "tax_amt": 0, "desc": "", "ib64": "", "cur": "TWD", "ab64":"", "vdr":"", "acc":"", "pay":"匯款(扣30手續費)", "inv_no":"", "acc_name": "", "ims_names": []}
    
    if st.session_state.req_edit_id:
        match_r = db[db["單號"]==st.session_state.req_edit_id]
        if not match_r.empty:
            r = match_r.iloc[0]
            jd = parse_req_json(r["請款說明"])
            legacy_net = clean_amount(r["總金額"]) if jd.get("net_amt", 0) == 0 and jd.get("tax_amt", 0) == 0 else jd.get("net_amt", 0)
            dv.update({
                "app": r["申請人"], "pn": r["專案名稱"], "pi": r["專案編號"], "exe": r["專案負責人"], 
                "net_amt": legacy_net, "tax_amt": jd.get("tax_amt", 0), "desc": jd.get("desc", ""), 
                "ib64": r["影像Base64"], "cur": r.get("幣別","TWD"), "ab64": r["帳戶影像Base64"], 
                "vdr": r.get("請款廠商",""), "acc": r.get("匯款帳戶",""), "pay": r.get("付款方式","匯款(扣30手續費)"), 
                "inv_no": jd.get("inv_no", ""), "acc_name": jd.get("acc_name", ""), "ims_names": jd.get("ims_names", [])
            })

    with st.container():
        c1, c2, c3, c4 = st.columns(4)
        app_val = c1.selectbox("申請人", staffs, index=staffs.index(dv["app"]) if dv["app"] in staffs else 0) if curr_name == "Anita" else curr_name
        if curr_name != "Anita": c1.text_input("申請人", value=app_val, disabled=True)
        exe = c2.selectbox("負責執行長", staffs, index=staffs.index(dv["exe"]) if dv["exe"] in staffs else 0)
        
        filtered_p = p_db[p_db["負責執行長"] == exe]
        p_names = filtered_p["專案名稱"].unique().tolist()
        p_options = [""] + p_names + ["➕ 手動輸入"]
        
        if dv["pn"] and dv["pn"] not in p_names:
            pn_idx = p_options.index("➕ 手動輸入")
        else:
            pn_idx = p_options.index(dv["pn"]) if dv["pn"] in p_options else 0
            
        pn_sel = c3.selectbox("專案名稱", p_options, index=pn_idx)
        if pn_sel == "➕ 手動輸入":
            pn = c3.text_input("✍️ 手動輸入專案名稱", value=dv["pn"] if dv["pn"] not in p_names else "")
        else:
            pn = pn_sel
            
        if pn_sel != "➕ 手動輸入" and pn in filtered_p["專案名稱"].values:
            auto_id = filtered_p[filtered_p["專案名稱"] == pn]["專案編號"].iloc[0]
        else:
            auto_id = dv["pi"]
            
        pi = c4.text_input("專案編號 (可手寫修改)", value=auto_id)
        
        cx1, cx2, cx3, cx4 = st.columns(4)
        curr = cx1.selectbox("幣別", ["TWD", "USD", "EUR"], index=["TWD", "USD", "EUR"].index(dv["cur"]) if dv["cur"] in ["TWD", "USD", "EUR"] else 0)
        net_amt = cx2.number_input("金額 (未稅)", value=int(dv["net_amt"]), min_value=0)
        tax_amt = cx3.number_input("稅額", value=int(dv["tax_amt"]), min_value=0)
        cx4.text_input("總計金額 (未稅+稅額)", value=f"{int(net_amt) + int(tax_amt):,}", disabled=True)
        
        v_names = v_db["請款廠商"].unique().tolist()
        v_options = [""] + v_names + ["➕ 手動輸入"]
        
        if dv["vdr"] and dv["vdr"] not in v_names:
            vdr_idx = v_options.index("➕ 手動輸入")
        else:
            vdr_idx = v_options.index(dv["vdr"]) if dv["vdr"] in v_options else 0
            
        cv1, cv2, cv3 = st.columns(3)
        vdr_sel = cv1.selectbox("請款廠商", v_options, index=vdr_idx)
        if vdr_sel == "➕ 手動輸入":
            vdr = cv1.text_input("✍️ 手動輸入廠商名稱", value=dv["vdr"] if dv["vdr"] not in v_names else "")
        else:
            vdr = vdr_sel
            
        if vdr_sel != "➕ 手動輸入" and vdr in v_db["請款廠商"].values:
            auto_acc = v_db[v_db["請款廠商"] == vdr]["匯款帳戶"].iloc[0]
        else:
            auto_acc = dv["acc"]
            
        acc = cv2.text_input("匯款帳戶 (可手寫修改)", value=auto_acc)
        inv_no = cv3.text_input("發票號碼或憑證 (非必填)", value=dv["inv_no"])
        
        pay_idx = ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"].index(dv["pay"]) if dv["pay"] in ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"] else 2
        pay = st.radio("付款方式", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], index=pay_idx, horizontal=True)
        
        desc = st.text_area("請款說明", value=dv["desc"])
        st.info("💡 **提示：系統會自動加總「金額(未稅) + 稅額」，若選擇「扣30手續費」，最終存檔總金額會自動扣除 30 元。**")
        
        up_key = st.session_state.req_uploader_key
        f_acc = st.file_uploader("上傳存摺/匯款資料 (圖/Excel)", type=["png", "jpg", "xlsx", "xls"], key=f"req_f_acc_{up_key}")
        f_ims = st.file_uploader("上傳請款憑證 (圖/Excel)", type=["png", "jpg", "xlsx", "xls"], accept_multiple_files=True, key=f"req_f_ims_{up_key}")
        
        del_acc = False
        del_ims = []
        existing_ims = []
        existing_ims_names = dv["ims_names"]
        
        if st.session_state.req_edit_id:
            st.markdown("---")
            st.markdown("### 📎 現有附件管理 (勾選以刪除)")
            
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
                    if c and len(c) > 50:
                        existing_ims.append(c)
                
                if existing_ims:
                    st.write("**已上傳之請款憑證：**")
                    for idx, _ in enumerate(existing_ims):
                        disp_name = existing_ims_names[idx] if idx < len(existing_ims_names) else f"舊版憑證 {idx+1}"
                        if st.checkbox(f"🗑️ 刪除 {disp_name}", key=f"del_im_{idx}"):
                            del_ims.append(idx)
                            
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
            st.session_state.req_edit_id = None
            st.session_state.req_last_msg = "🚫 已取消修改，未儲存任何變更。"
            st.session_state.req_uploader_key += 1
            st.rerun()
            
        elif btn_save or btn_submit or btn_preview or btn_print:
            fee = 30 if pay == "匯款(扣30手續費)" else 0
            total_amt = net_amt + tax_amt - fee
            if not pn or (net_amt + tax_amt) <= 0:
                st.error("⚠️ 請填寫「專案名稱」且金額須大於 0")
            else:
                if f_acc:
                    b_acc = base64.b64encode(f_acc.getvalue()).decode()
                    acc_name_save = f_acc.name
                else:
                    b_acc = "" if del_acc else safe_str(dv["ab64"])
                    acc_name_save = "" if del_acc else dv["acc_name"]

                retained_ims = [img for i, img in enumerate(existing_ims) if i not in del_ims]
                safe_existing_names = dv["ims_names"] + [f"舊版憑證 {i+1}" for i in range(len(existing_ims) - len(dv["ims_names"]))]
                retained_names = [name for i, name in enumerate(safe_existing_names[:len(existing_ims)]) if i not in del_ims]

                new_ims_b64 = [base64.b64encode(f.getvalue()).decode() for f in f_ims] if f_ims else []
                new_ims_names = [f.name for f in f_ims] if f_ims else []

                final_ims_list = retained_ims + new_ims_b64
                final_names_list = retained_names + new_ims_names
                b_ims = "|".join(final_ims_list)

                packed_desc = "[請款單資料]\n" + json.dumps({
                    "net_amt": net_amt, "tax_amt": tax_amt, "fee": fee, 
                    "inv_no": inv_no, "desc": desc, 
                    "acc_name": acc_name_save, "ims_names": final_names_list
                }, ensure_ascii=False)
                
                f_db = load_data()
                proxy_app = curr_name if (curr_name == "Anita" and app_val != curr_name) else ""
                
                if st.session_state.req_edit_id:
                    idx = f_db[f_db["單號"]==st.session_state.req_edit_id].index[0]
                    f_db.loc[idx, ["申請人", "代申請人", "專案名稱", "專案編號", "專案負責人", "總金額", "請款說明", "請款廠商", "匯款帳戶", "付款方式", "影像Base64", "帳戶影像Base64", "幣別", "狀態"]] = [app_val, proxy_app, pn, pi, exe, total_amt, packed_desc, vdr, acc, pay, b_ims, b_acc, curr, "已存檔未提交"]
                    tid = st.session_state.req_edit_id
                    msg_prefix = "修改完畢並存檔"
                else:
                    tid = f"{datetime.date.today().strftime('%Y%m%d')}-{len(f_db[f_db['單號'].str.startswith(datetime.date.today().strftime('%Y%m%d'))])+1:02d}"
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"請款單", "申請人":app_val, "代申請人":proxy_app, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":packed_desc, "總金額":total_amt, "幣別":curr, "請款廠商":vdr, "匯款帳戶":acc, "付款方式":pay, "狀態":"已存檔未提交", "影像Base64":b_ims, "帳戶影像Base64":b_acc}
                    f_db = pd.concat([f_db, pd.DataFrame([nr])], ignore_index=True)
                    msg_prefix = "存檔成功"
                
                save_data(f_db)

                if btn_submit:
                    f_db = load_data()
                    idx = f_db[f_db["單號"]==tid].index[0]
                    f_db.loc[idx, ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]
                    save_data(f_db)
                    sys_name = st.session_state.get('sys_choice', '請款單系統')
                    send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{tid}\n專案名稱：{pn}\n有一筆新的表單需要執行長 ({exe}) 進行簽核！")
                    
                    st.session_state.req_edit_id = None
                    st.session_state.req_last_msg = f"🚀 單據 {tid} 已成功提交簽核！"
                else:
                    st.session_state.req_edit_id = tid  
                    if btn_preview:
                        st.session_state.req_view_id = tid
                        st.session_state.req_last_msg = f"📄 單據 {tid} 已{msg_prefix}，正在產生預覽..."
                    elif btn_print:
                        st.session_state.req_print_id = tid
                        st.session_state.req_last_msg = f"🖨️ 單據 {tid} 已{msg_prefix}，正在準備列印..."
                    else:
                        st.session_state.req_last_msg = f"📄 單據 {tid} 已{msg_prefix}！您可以繼續修改或點擊提交。"
                
                st.session_state.req_uploader_key += 1
                st.rerun()

        if btn_next:
            st.session_state.req_edit_id = None
            st.session_state.req_last_id = None
            st.session_state.req_last_msg = None
            st.session_state.req_uploader_key += 1
            st.rerun()

    st.divider(); st.subheader("📋 申請追蹤清單")
    f_db = load_data(); my_db = f_db[f_db["類型"]=="請款單"]
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
    for c, h in zip(cols, ["申請單號", "專案名稱", "負責執行長", "申請人", "請款總金額", "狀態", "操作"]): c.write(f"**{h}**")
    for i, r in my_db.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"]); c[4].write(f"{r.get('幣別','TWD')} ${clean_amount(r['總金額']):,}")
        
        stt_raw = safe_str(r.get("狀態")).strip()
        stt_display = "已存檔未提交" if stt_raw in ["已儲存", "草稿"] else stt_raw
        
        color = "blue" if stt_display == "已存檔未提交" else "orange" if "待" in stt_display else "green" if stt_display == "已核准" else "red" if stt_display == "已駁回" else "gray"
        c[5].markdown(f":{color}[**{stt_display}**]")
        
        with c[6]:
            b1, b2, b3, b4, b5, b6 = st.columns(6)
            
            app_name = safe_str(r.get("申請人"))
            proxy_name = safe_str(r.get("代申請人"))
            is_own = (curr_name in app_name) or (curr_name in proxy_name) or (curr_name == "Anita")
            can_edit = (stt_raw in ["已儲存", "草稿", "已駁回", "已存檔未提交"]) and is_own and is_active
            
            if b1.button("提交", key=f"s{i}", disabled=not can_edit):
                fdb = load_data(); fdb.loc[fdb["單號"]==r["單號"], ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]; save_data(fdb)
                sys_name = st.session_state.get('sys_choice', '請款單系統')
                send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{r['單號']}\n專案名稱：{r['專案名稱']}\n有一筆新的表單需要執行長 ({r['專案負責人']}) 進行簽核！"); st.rerun()
            if b2.button("預覽", key=f"v{i}"): st.session_state.req_view_id = r["單號"]; st.rerun()
            if b3.button("列印", key=f"p{i}"): st.components.v1.html(f"<script>var w=window.open();w.document.write('{clean_for_js(render_html(r))}');w.print();w.close();</script>", height=0)
            if b4.button("修改", key=f"e{i}", disabled=not can_edit): st.session_state.req_edit_id = r["單號"]; st.rerun()
            
            if can_edit:
                with b5.popover("刪除"):
                    reason = st.text_input("刪除原因", key=f"d_res_{i}")
                    if st.button("確認", key=f"d{i}"):
                        if reason:
                            fresh_db = load_data(); fresh_db.loc[fresh_db["單號"]==r["單號"], ["狀態", "刪除人", "刪除時間", "刪除原因"]] = ["已刪除", curr_name, get_taiwan_time(), reason]; save_data(fresh_db); st.rerun()
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
        if not is_admin:
            history_exe = history_exe[(history_exe["初審人"] == curr_name) | (history_exe["專案負責人"] == curr_name) | (history_exe["申請人"] == curr_name) | (history_exe["代申請人"] == curr_name)]
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
        if not is_admin and curr_name != CFO_NAME:
            history_cfo = history_cfo[(history_cfo["申請人"] == curr_name) | (history_cfo["代申請人"] == curr_name) | (history_cfo["專案負責人"] == curr_name) | (history_cfo["初審人"] == curr_name)]
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
        st.error("⚠️ **雲端暫存機制提醒：** 免費雲端主機重啟會清空資料。請管理員務必在下班前下載備份！")

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
                    with open(S_FILE, "rb") as f: st.download_button("下載人員備份檔", f, file_name=f"時研系統人員備份_{datetime.date.today()}.csv", mime="text/csv")
            with col_up2:
                st.write("⬆️ **步驟二：還原人員資料**")
                uploaded_staff = st.file_uploader("上傳人員 CSV 檔", type=["csv"], key="up_staff", label_visibility="collapsed")
                if uploaded_staff and st.button("確認還原人員資料"):
                    with open(S_FILE, "wb") as f: f.write(uploaded_staff.getbuffer())
                    st.session_state.staff_df = load_staff()
                    st.success("人員資料已還原！"); time.sleep(1); st.rerun()

        with st.expander("🔔 3. LINE 官方帳號推播設定 (全域 Token & 行政副本 ID)", expanded=True):
            st.write("請填寫從 LINE Developers 取得的兩組關鍵代碼：")
            ct, cu = get_line_credentials()
            nt = st.text_input("Channel Access Token (長字串)", value=ct, type="password")
            nu = st.text_input("行政專屬 User ID (U開頭，用來接收所有副本)", value=cu)
            if st.button("💾 儲存 LINE 設定"): 
                save_line_credentials(nt, nu)
                st.success("LINE 推播設定已成功儲存並啟用！")
                time.sleep(1)
                st.rerun()
        st.divider()

    st.subheader("💰 財務匯款註記")
    f_db = load_data(); df_pay = f_db[f_db["類型"]=="請款單"].copy()
    
    if not is_admin and curr_name != CFO_NAME:
        df_pay = df_pay[(df_pay["申請人"] == curr_name) | (df_pay["專案負責人"] == curr_name)]
    
    if not df_pay.empty:
        df_pay["匯款日期"] = pd.to_datetime(df_pay["匯款日期"], errors='coerce').dt.date
        
        if is_admin:
            ed = st.data_editor(df_pay[["單號", "專案名稱", "請款廠商", "總金額", "匯款狀態", "匯款日期"]], hide_index=True, column_config={"匯款狀態": st.column_config.SelectboxColumn("匯款狀態", options=["尚未匯款", "已匯款"]), "匯款日期": st.column_config.DateColumn("匯款日期", format="YYYY-MM-DD")})
            if st.button("💾 儲存匯款資訊"):
                for _, row in ed.iterrows():
                    f_db.loc[f_db["單號"]==row["單號"], ["匯款狀態", "匯款日期"]] = [row["匯款狀態"], str(row["匯款日期"]) if pd.notna(row["匯款日期"]) else ""]
                save_data(f_db); st.success("已更新"); st.rerun()
        else:
            st.dataframe(df_pay[["單號", "專案名稱", "請款廠商", "總金額", "匯款狀態", "匯款日期"]], hide_index=True)

# ================= 全域預覽/列印模組 =================
if st.session_state.get('req_print_id'):
    r_df = load_data()
    r_df = r_df[r_df["單號"]==st.session_state.req_print_id]
    if not r_df.empty:
        r = r_df.iloc[0]
        st.components.v1.html(f"<script>var w=window.open();w.document.write('{clean_for_js(render_html(r))}');w.print();w.close();</script>", height=0)
    st.session_state.req_print_id = None

if st.session_state.req_view_id:
    st.divider()
    r_df = load_data()
    r_df = r_df[r_df["單號"]==st.session_state.req_view_id]
    
    if r_df.empty:
        st.warning("⚠️ 找不到該單號資料，可能已被刪除。")
        if st.button("❌ 關閉預覽"):
            st.session_state.req_view_id = None
            st.rerun()
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
            st.write("#### 📎 附件內容預覽")
            for f_b64 in all_files:
                try:
                    pad = f_b64 + "=" * ((4 - len(f_b64) % 4) % 4)
                    raw = base64.b64decode(pad)
                    if raw.startswith(b'PK\x03\x04') or raw.startswith(b'\xd0\xcf\x11\xe0'):
                        st.info("📊 偵測到 Excel 檔案：")
                        st.dataframe(pd.read_excel(io.BytesIO(raw)), use_container_width=True)
                    else:
                        st.image(raw, use_container_width=True)
                except Exception:
                    pass
