import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  
import json 

# --- A. 系統身分強制鎖定 ---
st.session_state['sys_choice'] = "請款單系統"

# --- B. 介面設定 ---
st.set_page_config(page_title="時研-請款單系統", layout="wide", page_icon="🏢")

# [CSS] 隱藏左側導航的 "app" 字樣，並優化手機版
st.markdown("""
<style>
    /* 隱藏左側選單的第一個項目 (app.py) */
    [data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
    .stApp { overflow-x: hidden; }
    @media screen and (max-width: 768px) {
        .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- C. 路徑修正：確保分頁能讀到根目錄的檔案 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) # 取得 pages 的上一層，即根目錄
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- D. 基礎工具函式 ---
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

def get_line_credentials():
    if os.path.exists(L_FILE):
        try:
            with open(L_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                return (lines[0].strip(), lines[1].strip()) if len(lines) >= 2 else ("", "")
        except: pass
    return "", ""

def send_line_message(msg):
    token, _ = get_line_credentials()
    if not token: return  
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try: requests.post(url, headers=headers, json={"messages": [{"type": "text", "text": msg}]}, timeout=5)
    except: pass

# --- E. 資料處理 ---
def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950']:
        try: return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except: continue
    return pd.DataFrame()

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "代申請人", "專案負責人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱",
            "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", 
            "刪除原因", "駁回原因", "匯款狀態", "匯款日期",
            "支付條件", "支付期數", "請款狀態", "已請款金額", "尚未請款金額", "最後採購金額"]
    df = read_csv_robust(D_FILE)
    if df is None or df.empty: return pd.DataFrame(columns=cols)
    if "專案執行人" in df.columns: df = df.rename(columns={"專案執行人": "專案負責人"})
    for c in cols:
        if c not in df.columns: df[c] = ""
    for col in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]:
        df[col] = df[col].apply(clean_amount)
    return df[cols]

def save_data(df):
    df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')

def load_staff():
    df = read_csv_robust(S_FILE)
    if df is None or df.empty:
        return pd.DataFrame({"name": DEFAULT_STAFF, "status": ["在職"]*5, "password": ["0000"]*5, "avatar": [""], "line_uid": [""]})
    df["name"] = df["name"].str.strip()
    return df

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
        st.markdown(f'<div style="display:flex;align-items:center;justify-content:center;gap:15px;margin-bottom:20px;"><img src="data:image/png;base64,{logo_b64}" style="height:60px;"><h2>時研國際設計股份有限公司</h2></div>', unsafe_allow_html=True)
    else: st.title("時研國際設計股份有限公司")
    st.divider()

def is_pdf(b64_str): return str(b64_str).startswith("JVBERi")
def clean_for_js(h_str): return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# --- F. 權限檢查 ---
if 'user_id' not in st.session_state or st.session_state.user_id is None:
    st.warning("⚠️ 請先回首頁登入")
    st.stop()

# Session 初始化
if 'view_id' not in st.session_state: st.session_state.view_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'form_key' not in st.session_state: st.session_state.form_key = 0

curr_name = st.session_state.user_id
staff_df = load_staff()
is_admin = (curr_name in ADMINS)

# --- G. 側邊欄 ---
st.sidebar.markdown(f"### 👤 {curr_name}")
st.sidebar.info(f"📌 目前系統：`請款單系統`")

if st.sidebar.button("登出系統"):
    st.session_state.user_id = None
    st.switch_page("app.py")

menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽"]
if is_admin: menu_options.append("5. 請款狀態/系統設定")
menu = st.sidebar.radio("導覽", menu_options, key="menu_radio")

# --- H. 核心 HTML 渲染 (請款專用) ---
def render_html(row):
    amt = clean_amount(row['總金額'])
    fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0
    
    logo_b64 = get_b64_logo()
    lg_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:50px;">' if logo_b64 else ''
    
    h = f'<div style="padding:20px;border:2px solid #000;max-width:680px;background:#fff;color:#000;margin:auto;">'
    h += f'<div style="text-align:center;border-bottom:2px solid #000;padding-bottom:10px;">{lg_html}<h2>時研國際設計股份有限公司</h2><h3>請款單</h3></div>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;margin-top:10px;" border="1">'
    h += f'<tr><td bgcolor="#eee" width="20%">單號</td><td>{row["單號"]}</td><td bgcolor="#eee" width="20%">廠商</td><td>{row["請款廠商"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">專案</td><td>{row["專案名稱"]}</td><td bgcolor="#eee">執行長</td><td>{clean_name(row["專案負責人"])}</td></tr>'
    h += f'<tr><td bgcolor="#eee">帳戶</td><td colspan="3">{row.get("匯款帳戶", "")}</td></tr>'
    h += f'<tr><td bgcolor="#eee">說明</td><td colspan="3">{row["請款說明"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">應付金額</td><td colspan="3" align="right">{row.get("幣別","TWD")} {amt:,.0f}</td></tr>'
    h += f'<tr><td bgcolor="#eee">實付金額</td><td colspan="3" align="right"><b>{row.get("幣別","TWD")} {amt-fee:,.0f}</b></td></tr></table>'
    h += f'<p style="font-size:12px;">提交時間: {row.get("提交時間","")}</p></div>'
    
    # 附件與存摺
    v = ""
    if row.get('帳戶影像Base64'):
        v += '<div style="page-break-before:always;"><h3>存摺影像：</h3>'
        if is_pdf(row['帳戶影像Base64']): v += f'<embed src="data:application/pdf;base64,{row["帳戶影像Base64"]}" width="100%" height="500px" />'
        else: v += f'<img src="data:image/jpeg;base64,{row["帳戶影像Base64"]}" width="100%">'
        v += '</div>'
    return h + v

# 過濾資料庫
def get_filtered_db():
    db = load_data()
    return db[db["類型"].isin(["請款單", "請購單"])]

# --- I. 各頁面邏輯 ---

if menu == "1. 填寫申請單":
    render_header()
    st.subheader("📝 填寫請款申請單")
    
    db = load_data()
    staffs = staff_df["name"].tolist()
    
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id].iloc[0]
        st.info(f"正在修改單號: {st.session_state.edit_id}")
    
    with st.form("pay_form"):
        c1, c2 = st.columns(2)
        pn = c1.text_input("專案名稱")
        exe = c1.selectbox("專案負責執行長", staffs)
        pi = c2.text_input("專案編號")
        amt = c2.number_input("請款金額", min_value=0)
        vdr = st.text_input("請款廠商")
        acc = st.text_input("匯款帳號 (銀行+分行+帳號)")
        pay_mode = st.radio("付款方式", ["現金", "零用金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], horizontal=True)
        desc = st.text_area("請款說明")
        f_acc = st.file_uploader("上傳存摺照片/PDF")
        f_ims = st.file_uploader("上傳請款憑證 (發票/收據)", accept_multiple_files=True)
        
        if st.form_submit_button("💾 儲存並產生單號"):
            if not (pn and amt > 0 and vdr):
                st.error("請填寫必填欄位 (專案、金額、廠商)！")
            else:
                b_acc = base64.b64encode(f_acc.getvalue()).decode() if f_acc else ""
                b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else ""
                today_str = datetime.date.today().strftime('%Y%m%d')
                tid = f"{today_str}-{len(db[db['單號'].str.startswith(today_str)])+1:02d}"
                
                nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"請款單", "申請人":curr_name, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "總金額":amt, "請款廠商":vdr, "匯款帳戶":acc, "付款方式":pay_mode, "請款說明":desc, "帳戶影像Base64":b_acc, "影像Base64":b_ims, "狀態":"已儲存", "匯款狀態":"尚未匯款"}
                
                db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                save_data(db)
                st.session_state.last_id = tid
                st.success(f"成功！單號：{tid}")
                st.rerun()

    if st.session_state.last_id:
        if st.button("🚀 正式提交申請"):
            fresh_db = load_data()
            idx = fresh_db[fresh_db["單號"]==st.session_state.last_id].index[0]
            fresh_db.at[idx, "狀態"] = "待簽核"
            fresh_db.at[idx, "提交時間"] = get_taiwan_time()
            save_data(fresh_db)
            send_line_message(f"🔔【請款單待簽核】\n單號：{st.session_state.last_id}\n有一筆新的請款申請需要執行長簽核。")
            st.session_state.last_id = None
            st.success("已送出簽核！")
            st.rerun()

elif menu == "2. 專案執行長簽核":
    render_header()
    st.subheader("🔍 專案執行長第一級簽核")
    sys_db = get_filtered_db()
    p_df = sys_db[(sys_db["狀態"] == "待簽核") & (sys_db["專案負責人"] == curr_name)]
    
    if p_df.empty: st.info("目前無待簽核項目。")
    for i, r in p_df.iterrows():
        with st.expander(f"單號: {r['單號']} - {r['請款廠商']} (${r['總金額']:,})"):
            st.write(f"專案: {r['專案名稱']} | 說明: {r['請款說明']}")
            if st.button("✅ 核准並送交財務長", key=f"ok_{i}"):
                fresh_db = load_data()
                idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                fresh_db.at[idx, "狀態"] = "待複審"
                fresh_db.at[idx, "初審人"] = curr_name
                fresh_db.at[idx, "初審時間"] = get_taiwan_time()
                save_data(fresh_db)
                send_line_message(f"🔔【請款複審提醒】\n單號：{r['單號']}\n執行長已核准，請財務長進行複審。")
                st.rerun()

elif menu == "3. 財務長簽核":
    render_header()
    st.subheader("🏁 財務長最終簽核")
    if curr_name != CFO_NAME and not is_admin:
        st.error("您沒有權限進入此頁面。")
    else:
        sys_db = get_filtered_db()
        f_df = sys_db[sys_db["狀態"] == "待複審"]
        if f_df.empty: st.info("目前無待複審項目。")
        for i, r in f_df.iterrows():
            with st.expander(f"複審：{r['單號']} - {r['請款廠商']}"):
                if st.button("👑 最終核准", key=f"fok_{i}"):
                    fresh_db = load_data()
                    idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    fresh_db.at[idx, "狀態"] = "已核准"
                    fresh_db.at[idx, "複審人"] = curr_name
                    fresh_db.at[idx, "複審時間"] = get_taiwan_time()
                    save_data(fresh_db)
                    st.success("已核准！")
                    st.rerun()

elif menu == "5. 請款狀態/系統設定":
    render_header()
    st.subheader("💰 財務匯款註記 (僅管理員)")
    if not is_admin: st.error("僅管理員可使用。")
    else:
        sys_db = get_filtered_db()
        approved_df = sys_db[sys_db["狀態"] == "已核准"].copy()
        if approved_df.empty: st.info("尚無已核准待匯款單據。")
        else:
            edited_df = st.data_editor(approved_df[["單號", "請款廠商", "總金額", "匯款狀態", "匯款日期"]], use_container_width=True)
            if st.button("💾 儲存匯款註記"):
                fresh_db = load_data()
                for i, row in edited_df.iterrows():
                    idx = fresh_db[fresh_db["單號"]==row["單號"]].index[0]
                    fresh_db.at[idx, "匯款狀態"] = row["匯款狀態"]
                    fresh_db.at[idx, "匯款日期"] = row["匯款日期"]
                save_data(fresh_db)
                st.success("匯款資訊更新成功！")

# 全域預覽
if st.session_state.view_id:
    st.markdown("---")
    r = load_data(); r = r[r["單號"]==st.session_state.view_id]
    if not r.empty:
        if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
        st.markdown(render_html(r.iloc[0]), unsafe_allow_html=True)
