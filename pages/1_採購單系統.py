import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re
import time
import requests  
import json 

# --- [新增] 強制鎖定為採購單系統 ---
st.session_state['sys_choice'] = "採購單系統"

# --- 1. 系統設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide", page_icon="🏢")

# [手機版 RWD 響應式優化 CSS & 隱藏左側 app 選單]
st.markdown("""
<style>
/* 隱藏左側選單的第一個項目(app首頁) */
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }

.stApp { overflow-x: hidden; }
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    table { word-wrap: break-word !important; font-size: 13px !important; }
    th, td { padding: 5px !important; }
}
</style>
""", unsafe_allow_html=True)

# --- [修改] 路徑修正：讓系統穿透 pages 資料夾，找到外面的資料庫 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) 

D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# [工具] 取得台灣時間
def get_taiwan_time():
    tw_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    return tw_time.strftime('%Y-%m-%d %H:%M')

# [工具] 金額清洗 (極度安全版)
def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": 
        return 0
    s_val = str(val).replace(",", "").replace("$", "").replace("，", "").replace(" ", "")
    try:
        return int(float(s_val))
    except Exception:
        return 0

# [工具] 名字清洗
def clean_name(val):
    if pd.isna(val) or val is None or str(val).strip() == "": 
        return ""
    return str(val).strip().split(" ")[0]

# [工具] 跳轉至修改頁面
def navigate_to_edit(eid):
    st.session_state.edit_id = eid
    st.session_state.menu_radio = "1. 填寫申請單"

# [工具] 追蹤在線人數
def get_online_users(curr_user):
    try:
        if not curr_user: 
            return 1
        now = time.time()
        df = pd.DataFrame(columns=["user", "time"])
        if os.path.exists(O_FILE):
            try: 
                df = pd.read_csv(O_FILE)
            except Exception: 
                pass
            
        if "user" not in df.columns or "time" not in df.columns:
            df = pd.DataFrame(columns=["user", "time"])
            
        df = df[df["user"] != curr_user]
        df = pd.concat([df, pd.DataFrame([{"user": curr_user, "time": now}])], ignore_index=True)
        df["time"] = pd.to_numeric(df["time"], errors='coerce').fillna(now)
        df = df[now - df["time"] <= 300]
        
        try: 
            df.to_csv(O_FILE, index=False)
        except Exception: 
            pass
        return len(df["user"].unique())
    except Exception:
        return 1

# [更新工具] LINE 精準群發推播功能
def get_line_credentials():
    if os.path.exists(L_FILE):
        try:
            with open(L_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                t = lines[0].strip() if len(lines) > 0 else ""
                u = lines[1].strip() if len(lines) > 1 else ""
                return t, u
        except Exception: 
            pass
    return "", ""

def save_line_credentials(token, user_id):
    try:
        with open(L_FILE, "w", encoding="utf-8") as f:
            f.write(f"{token.strip()}\n{user_id.strip()}")
    except Exception: 
        pass

# 全面改用 LINE 官方群發 (Broadcast) 機制
def send_line_message(msg, target_name=""):
    token, _ = get_line_credentials()
    if not token: 
        return  
    
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    data = {
        "messages": [{"type": "text", "text": msg}]
    }
    
    try:
        requests.post(url, headers=headers, json=data, timeout=5)
    except Exception:
        pass

# --- 2. 自動救援資料 ---
def init_rescue_data():
    if not os.path.exists(D_FILE):
        data = {
            "單號": ["20260205-01"], "日期": ["2026-02-05"], "類型": ["請款單"],
            "申請人": ["Anita"], "代申請人": [""], "專案負責人": ["Andy"], "專案名稱": ["公司費用"],
            "專案編號": ["GENERAL"], "請款說明": ["測試款項"], "總金額": [5500],
            "幣別": ["TWD"], "付款方式": ["現金"], "請款廠商": ["測試廠商"],
            "匯款帳戶": [""], "帳戶影像Base64": [""], "狀態": ["待簽核"],
            "影像Base64": [""], "提交時間": ["2026-02-05 14:00"], "申請人信箱": ["Anita"],
            "初審人": [""], "初審時間": [""], "複審人": [""], "複審時間": [""],
            "刪除人": [""], "刪除時間": [""], "刪除原因": [""], "駁回原因": [""],
            "匯款狀態": ["尚未匯款"], "匯款日期": [""],
            "支付條件": [""], "支付期數": [""], "請款狀態": [""], "已請款金額": [0], "尚未請款金額": [0], "最後採購金額": [0]
        }
        df = pd.DataFrame(data)
        df.to_csv(D_FILE, index=False, encoding='utf-8-sig')

init_rescue_data()

# --- 3. 資料處理 ---
def read_csv_robust(filepath):
    if not os.path.exists(filepath): 
        return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try:
            return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except Exception:
            continue
    return pd.DataFrame()

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "代申請人", "專案負責人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱",
            "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", 
            "刪除原因", "駁回原因", "匯款狀態", "匯款日期",
            "支付條件", "支付期數", "請款狀態", "已請款金額", "尚未請款金額", "最後採購金額"]
    
    df = read_csv_robust(D_FILE)
    if df is None or df.empty: 
        return pd.DataFrame(columns=cols)
        
    if "專案執行人" in df.columns: 
        df = df.rename(columns={"專案執行人": "專案負責人"})
    
    for c in cols:
        if c not in df.columns: 
            df[c] = ""
            
    df["總金額"] = df["總金額"].apply(clean_amount)
    df["已請款金額"] = df["已請款金額"].apply(clean_amount)
    df["尚未請款金額"] = df["尚未請款金額"].apply(clean_amount)
    df["最後採購金額"] = df["最後採購金額"].apply(clean_amount)
    
    df["專案負責人"] = df["專案負責人"].astype(str).apply(clean_name)
    df["申請人"] = df["申請人"].astype(str).apply(clean_name)
    df["代申請人"] = df["代申請人"].astype(str).apply(clean_name)
    df["狀態"] = df["狀態"].astype(str).str.strip()
    return df[cols]

def save_data(df):
    try:
        df["總金額"] = df["總金額"].apply(clean_amount)
        df["已請款金額"] = df["已請款金額"].apply(clean_amount)
        df["尚未請款金額"] = df["尚未請款金額"].apply(clean_amount)
        df["最後採購金額"] = df["最後採購金額"].apply(clean_amount)
        df["專案負責人"] = df["專案負責人"].astype(str).apply(clean_name)
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError:
        st.error("⚠️ 警告：無法寫入檔案！請關閉 Excel。")
        st.stop()

def load_staff():
    default_df = pd.DataFrame({
        "name": DEFAULT_STAFF, 
        "status": ["在職"]*5, 
        "password": ["0000"]*5, 
        "avatar": [""]*5,
        "line_uid": [""]*5 
    })
    df = read_csv_robust(S_FILE)
    if df is None or df.empty:
        df = default_df.copy()
        df.to_csv(S_FILE, index=False, encoding='utf-8-sig')
        return df
    if "status" not in df.columns: df["status"] = "在職"
    if "avatar" not in df.columns: df["avatar"] = ""
    if "line_uid" not in df.columns: df["line_uid"] = ""
    df["name"] = df["name"].str.strip()
    df["avatar"] = df["avatar"].fillna("")
    df["line_uid"] = df["line_uid"].fillna("")
    return df

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            if any(x in f.lower() for x in ["logo", "timelab"]) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                with open(os.path.join(B_DIR, f), "rb") as img:
                    return base64.b64encode(img.read()).decode()
    except Exception: 
        pass
    return ""

def render_header():
    logo_b64 = get_b64_logo()
    if logo_b64:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 20px; flex-wrap: wrap;">
                <img src="data:image/png;base64,{logo_b64}" style="height: 60px; max-width: 100%;">
                <h2 style="margin: 0; color: #333; text-align: center;">時研國際設計股份有限公司</h2>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.title("時研國際設計股份有限公司")
    st.divider()

def clean_for_js(h_str):
    return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

def is_pdf(b64_str):
    return b64_str.startswith("JVBERi")

# Session Init
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'user_status' not in st.session_state: st.session_state.user_status = "在職"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None
if 'form_key' not in st.session_state: st.session_state.form_key = 0 
if 'sys_choice' not in st.session_state: st.session_state.sys_choice = "採購單系統"
if 'menu_radio' not in st.session_state: st.session_state.menu_radio = "1. 填寫申請單"

# --- [修改] 4. 登入檢查：未登入一律跳轉回首頁 app.py ---
if st.session_state.user_id is None:
    st.switch_page("app.py")

curr_name = st.session_state.user_id
is_active = (st.session_state.user_status == "在職")
is_admin = (curr_name in ADMINS)

avatar_b64 = ""
try:
    curr_user_row = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0]
    avatar_b64 = curr_user_row.get("avatar", "")
except Exception: 
    pass

# --- 5. 側邊欄 ---
logo_b64 = get_b64_logo()
if logo_b64:
    st.sidebar.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{logo_b64}" style="height: 80px; max-width: 100%;">
            <h3 style="margin-top: 10px; color: #333;">時研國際設計股份有限公司</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.sidebar.title("時研國際設計股份有限公司")

st.sidebar.divider()
st.sidebar.markdown(f"**📌 目前系統：** `{st.session_state.sys_choice}`")

if avatar_b64:
    st.sidebar.markdown(f'''
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 15px;">
            <img src="data:image/jpeg;base64,{avatar_b64}" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 3px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <span style="font-size: 22px; font-weight: bold; color: #333;">{curr_name}</span>
        </div>
    ''', unsafe_allow_html=True)
else:
    st.sidebar.markdown(f"### 👤 {curr_name}")

online_count = get_online_users(curr_name)
st.sidebar.info(f"🟢 目前在線人數：**{online_count}** 人")

if not is_active: 
    st.sidebar.error("⛔ 已離職")

with st.sidebar.expander("📸 修改大頭貼"):
    new_avatar = st.file_uploader("上傳您的圖片", type=["jpg", "jpeg", "png"])
    if st.button("更新大頭貼", disabled=not is_active):
        if new_avatar is not None:
            b64 = base64.b64encode(new_avatar.getvalue()).decode()
            staff_df = st.session_state.staff_df
            idx = staff_df[staff_df["name"] == curr_name].index[0]
            staff_df.at[idx, "avatar"] = b64
            save_staff(staff_df)
            st.session_state.staff_df = staff_df
            st.success("大頭貼已更新！")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("請選擇圖片檔")

with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password")
    confirm_pw = st.text_input("確認新密碼", type="password")
    if st.button("更新密碼", disabled=not is_active):
        if new_pw != confirm_pw: 
            st.error("兩次輸入不符")
        elif len(str(new_pw)) < 4: 
            st.error("密碼過短")
        else:
            staff_df = st.session_state.staff_df
            idx = staff_df[staff_df["name"] == curr_name].index[0]
            staff_df.at[idx, "password"] = str(new_pw)
            save_staff(staff_df)
            st.session_state.staff_df = staff_df
            st.success("成功")

if is_admin:
    st.sidebar.success("管理員模式")
    
    with st.sidebar.expander("🔑 所有人員密碼清單"):
        staff_df = st.session_state.staff_df
        st.dataframe(staff_df[["name", "password"]], hide_index=True)
        
        st.markdown("---")
        st.write("**恢復預設密碼 (0000)**")
        reset_target = st.selectbox("選擇人員", staff_df["name"].tolist(), key="rst_sel")
        if st.button("確認恢復預設", key="rst_btn"):
            idx = staff_df[staff_df["name"] == reset_target].index[0]
            staff_df.at[idx, "password"] = "0000"
            save_staff(staff_df)
            st.session_state.staff_df = staff_df
            st.success(f"{reset_target} 密碼已重置")

    with st.sidebar.expander("➕ 新增人員"):
        n = st.text_input("姓名")
        if st.button("新增"):
            staff_df = st.session_state.staff_df
            if n not in staff_df["name"].values:
                staff_df = pd.concat([staff_df, pd.DataFrame({"name":[n], "status":["在職"], "password":["0000"], "avatar":[""], "line_uid":[""]})])
                save_staff(staff_df)
                st.session_state.staff_df = staff_df
                st.success("成功")
                st.rerun()
            else: 
                st.error("已存在")
    
    with st.sidebar.expander("⚙️ 人員設定 (狀態 & LINE ID)"):
        st.write("請填寫各員工查到的 U 開頭代碼，以便他們接收專屬通知：")
        staff_df = st.session_state.staff_df
        edited_staff = st.data_editor(
            staff_df[["name", "status", "line_uid"]],
            column_config={
                "name": st.column_config.TextColumn("姓名", disabled=True),
                "status": st.column_config.SelectboxColumn("狀態", options=["在職", "離職"]),
                "line_uid": st.column_config.TextColumn("LINE User ID (U開頭)")
            },
            hide_index=True,
            use_container_width=True,
            key="staff_editor"
        )
        if st.button("💾 儲存人員設定", key="save_staff_btn"):
            for idx, row in edited_staff.iterrows():
                staff_df.at[idx, "status"] = row["status"]
                staff_df.at[idx, "line_uid"] = str(row["line_uid"]).strip() if pd.notna(row["line_uid"]) else ""
            save_staff(staff_df)
            st.session_state.staff_df = staff_df
            st.success("人員設定已更新！")
            time.sleep(1)
            st.rerun()

# --- [修改] 登出按鈕：清除 session 並跳轉回 app.py ---
if st.sidebar.button("登出"):
    st.session_state.user_id = None
    if 'menu_radio' in st.session_state:
        del st.session_state['menu_radio']
    st.switch_page("app.py")

# 導覽選單
menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽"]
if is_admin:
    menu_options.append("5. 請款狀態/系統設定")

if 'menu_radio' in st.session_state and st.session_state.menu_radio not in menu_options:
    st.session_state.menu_radio = "1. 填寫申請單"

menu = st.sidebar.radio("導覽", menu_options, key="menu_radio")

if 'last_menu' not in st.session_state:
    st.session_state.last_menu = st.session_state.menu_radio
if st.session_state.last_menu != st.session_state.menu_radio:
    st.session_state.view_id = None
    st.session_state.last_menu = st.session_state.menu_radio

def get_filtered_db():
    db = load_data()
    db["類型"] = db["類型"].astype(str).str.strip()
    sys_type = "採購單" if st.session_state.get('sys_choice') == "採購單系統" else ("請款單", "請購單")
    if isinstance(sys_type, tuple): 
        return db[db["類型"].isin(sys_type)]
    else: 
        return db[db["類型"] == sys_type]

# --- HTML 渲染 ---
def render_html(row):
    amt = clean_amount(row['總金額'])
    fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0
    
    sub_time_val = row.get("提交時間", "")
    sub_time_str = str(sub_time_val) if pd.notna(sub_time_val) and str(sub_time_val).strip().lower() != "nan" and str(sub_time_val).strip() else get_taiwan_time()
    
    chu_time_val = row.get("初審時間", "")
    chu_time_str = str(chu_time_val) if pd.notna(chu_time_val) and str(chu_time_val).strip().lower() != "nan" else ""
    
    fu_time_val = row.get("複審時間", "")
    fu_time_str = str(fu_time_val) if pd.notna(fu_time_val) and str(fu_time_val).strip().lower() != "nan" else ""

    app_name = clean_name(row.get("申請人", ""))
    proxy_name = clean_name(row.get("代申請人", ""))
    display_app = f"{app_name} ({proxy_name} 代申請)" if proxy_name else app_name
    
    chu_name = clean_name(row.get("初審人", ""))
    fu_name = clean_name(row.get("複審人", ""))
    
    stt = str(row.get("狀態", "")).strip()

    app_info = f"{display_app} {sub_time_str}".strip()
    
    if stt in ["已儲存", "草稿", "待簽核"]:
        chu_info = ""
        fu_info = ""
    elif stt == "待複審":
        chu_info = f"{chu_name} {chu_time_str}".strip()
        fu_info = ""
    else:
        chu_info = f"{chu_name} {chu_time_str}".strip()
        fu_info = f"{fu_name} {fu_time_str}".strip()
    
    t = str(row.get("類型", "請款單")).strip()
    sys_type_title = "採購單" if t == "採購單" else "請款單"
    
    logo_b64 = get_b64_logo()
    lg_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:50px; max-width:100%;">' if logo_b64 else ''
    
    h = f'<div style="padding:20px;border:2px solid #000;max-width:680px;width:100%;box-sizing:border-box;margin:auto;background:#fff;color:#000;">'
    h += f'<div style="text-align:center; border-bottom:2px solid #000; padding-bottom:10px; margin-bottom:10px;">'
    h += f'<div style="display:flex; justify-content:center; align-items:center; gap:15px; flex-wrap:wrap;">'
    if lg_html: 
        h += f'{lg_html}'
    h += f'<h2 style="margin:0;">時研國際設計股份有限公司</h2></div>'
    h += f'<h3 style="margin:10px 0 0 0; letter-spacing:5px;">{sys_type_title}</h3></div>'
    
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;table-layout:fixed;" border="1">'
    h += f'<tr><td bgcolor="#eee" width="25%">單號</td><td width="25%">{row["單號"]}</td><td bgcolor="#eee" width="25%">負責執行長</td><td width="25%">{clean_name(row["專案負責人"])}</td></tr>'
    h += f'<tr><td bgcolor="#eee">專案</td><td>{row["專案名稱"]}</td><td bgcolor="#eee">編號</td><td>{row["專案編號"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">申請人</td><td>{display_app}</td><td bgcolor="#eee">廠商</td><td>{row["請款廠商"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">匯款帳戶</td><td colspan="3">{row.get("匯款帳戶", "")}</td></tr>'
    h += f'<tr><td bgcolor="#eee">說明</td><td colspan="3">{row["請款說明"]}</td></tr>'
    
    c_cur = str(row.get("幣別", "TWD")).replace("nan", "TWD")
    
    if t == "採購單":
        h += f'<tr><td bgcolor="#eee">支付條件</td><td>{row.get("支付條件","")}</td><td bgcolor="#eee">支付期數</td><td>{row.get("支付期數","")}</td></tr>'
        h += f'<tr><td bgcolor="#eee">請款狀態</td><td>{row.get("請款狀態","")}</td><td bgcolor="#eee">最後採購金額</td><td>{c_cur} {clean_amount(row.get("最後採購金額",0)):,.0f}</td></tr>'
        h += f'<tr><td bgcolor="#eee">已請款金額</td><td>{c_cur} {clean_amount(row.get("已請款金額",0)):,.0f}</td><td bgcolor="#eee">尚未請款金額</td><td>{c_cur} {clean_amount(row.get("尚未請款金額",0)):,.0f}</td></tr>'
        h += f'<tr><td colspan="3" align="right">預計採購金額</td><td align="right">{c_cur} {amt:,.0f}</td></tr>'
    else:
        h += f'<tr><td colspan="3" align="right">金額</td><td align="right">{c_cur} {amt:,.0f}</td></tr>'
        
    h += f'<tr><td colspan="3" align="right">實付</td><td align="right">{c_cur} {amt-fee:,.0f}</td></tr></table>'
    
    if row['帳戶影像Base64']:
        h += '<br><b>存摺：</b><br>'
        if is_pdf(row['帳戶影像Base64']): 
            h += f'<embed src="data:application/pdf;base64,{row["帳戶影像Base64"]}" width="100%" height="300px" />'
        else: 
            h += f'<img src="data:image/jpeg;base64,{row["帳戶影像Base64"]}" width="100%">'
        
    if row["狀態"] == "已駁回" and str(row.get("駁回原因", "")) != "":
        h += f'<div style="color:red;border:1px solid red;padding:5px;margin-top:5px;"><b>❌ 駁回原因：</b>{row["駁回原因"]}</div>'
        
    h += f'<p>提交: {app_info} | 初審: {chu_info} | 複審: {fu_info}</p></div>'
    
    v = ""
    if row['影像Base64']:
        imgs = row['影像Base64'].split('|')
        for i, img in enumerate(imgs):
            v += '<div style="page-break-before:always;padding:20px;">'
            if is_pdf(img): 
                v += f'<embed src="data:application/pdf;base64,{img}" width="100%" height="800px" />'
            else: 
                v += f'<img src="data:image/jpeg;base64,{img}" width="100%">'
            v += '</div>'
    return h + v

# [工具] 共用附件補件功能
def render_upload_popover(container, r, prefix):
    with container.popover("📎 附件"):
        st.write("**上傳存摺及憑證 (將覆蓋原檔)**")
        new_f_acc = st.file_uploader("上傳新存摺", key=f"{prefix}_acc")
        new_f_ims = st.file_uploader("上傳新憑證", accept_multiple_files=True, key=f"{prefix}_ims")
        if st.button("💾 儲存附件", key=f"{prefix}_btn"):
            fresh_db = load_data()
            idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
            if new_f_acc:
                fresh_db.at[idx, "帳戶影像Base64"] = base64.b64encode(new_f_acc.getvalue()).decode()
            if new_f_ims:
                fresh_db.at[idx, "影像Base64"] = "|".join([base64.b64encode(f.getvalue()).decode() for f in new_f_ims])
            save_data(fresh_db)
            st.success("附件已成功更新！")
            time.sleep(0.5)
            st.rerun()

# --- 頁面 1: 填寫與追蹤 ---
if menu == "1. 填寫申請單":
    render_header()
    st.subheader("填寫申請單")
    
    try:
        db = load_data()
        staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
        if curr_name not in staffs: staffs.append(curr_name)
        
        sys_save_type = "採購單" if st.session_state.get('sys_choice') == "採購單系統" else "請款單"
        
        curr_options = ["TWD", "USD", "EUR", "JPY", "CNY", "HKD", "GBP", "AUD"]
        dv = {"pn":"", "exe":staffs[0], "pi":"", "amt":0, "curr":"TWD", "pay":"現金", "vdr":"", "acc":"", "desc":"", "ab64":"", "ib64":"", "app": curr_name,
              "pay_cond": "", "pay_inst": "", "final_amt": 0, "billed_amt": 0, "unbilled_amt": 0, "bill_stat": ""}
        
        if st.session_state.edit_id:
            r = db[db["單號"]==st.session_state.edit_id]
            if not r.empty:
                row = r.iloc[0]
                st.info(f"📝 修改中: {st.session_state.edit_id
