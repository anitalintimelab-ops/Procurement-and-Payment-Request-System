import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re
import time
import requests  
import json 

# --- 1. 系統設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide", page_icon="🏢")
B_DIR = os.path.dirname(os.path.abspath(__file__))
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

# [更新工具] LINE 精準推播功能
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

def send_line_message(msg, target_name):
    token, admin_uid = get_line_credentials()
    if not token: 
        return  
    
    staff_df = load_staff()
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    target_uid = ""
    if target_name == "Anita" and admin_uid and admin_uid.startswith("U"):
        target_uid = admin_uid
    else:
        target_row = staff_df[staff_df["name"] == target_name]
        if not target_row.empty:
            target_uid = str(target_row.iloc[0].get("line_uid", "")).strip()
            
    if target_uid and target_uid.startswith("U"):
        data = {
            "to": target_uid,
            "messages": [{"type": "text", "text": msg}]
        }
        try:
            requests.post(url, headers=headers, json=data, timeout=5)
        except Exception:
            pass
            
    if target_name != "Anita":
        anita_uid = admin_uid if admin_uid and admin_uid.startswith("U") else ""
        if not anita_uid:
            anita_row = staff_df[staff_df["name"] == "Anita"]
            if not anita_row.empty:
                anita_uid = str(anita_row.iloc[0].get("line_uid", "")).strip()
                
        if anita_uid and anita_uid.startswith("U"):
            cc_msg = f"👀 [系統同步副本給行政 - 原送給 {target_name}]\n{msg}"
            data_cc = {
                "to": anita_uid,
                "messages": [{"type": "text", "text": cc_msg}]
            }
            try:
                requests.post(url, headers=headers, json=data_cc, timeout=5)
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
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
                <img src="data:image/png;base64,{logo_b64}" style="height: 60px;">
                <h2 style="margin: 0; color: #333;">時研國際設計股份有限公司</h2>
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
if 'sys_choice' not in st.session_state: st.session_state.sys_choice = "請款單系統"
if 'menu_radio' not in st.session_state: st.session_state.menu_radio = "1. 填寫申請單"

# --- 4. 登入 ---
if st.session_state.user_id is None:
    logo_b64 = get_b64_logo()
    if logo_b64:
        st.markdown(
            f"""
            <div style="text-align: center; margin-bottom: 30px;">
                <img src="data:image/png;base64,{logo_b64}" style="height: 100px;">
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("<h1 style='text-align: center;'>🏢 時研國際設計股份有限公司 - 請款&採購申請、審核系統</h1>", unsafe_allow_html=True)
    
    staff_df = load_staff()
    with st.form("login"):
        u = st.selectbox("身分", staff_df["name"].tolist())
        p = st.text_input("密碼", type="password")
        sys_choice = st.selectbox("登入系統", ["請款單系統", "採購單系統"])
        
        if st.form_submit_button("登入"):
            row = staff_df[staff_df["name"] == u].iloc[0]
            stored_p = str(row["password"]).strip().replace(".0", "")
            if str(p).strip() == stored_p or (str(p).strip() == "0000" and stored_p in ["nan", ""]):
                st.session_state.user_id = u
                st.session_state.user_status = row["status"] if pd.notna(row["status"]) else "在職"
                st.session_state.staff_df = staff_df
                st.session_state.sys_choice = sys_choice
                st.session_state.menu_radio = "1. 填寫申請單"
                st.rerun()
            else:
                st.error("密碼錯誤")
    st.stop()

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
            <img src="data:image/png;base64,{logo_b64}" style="height: 80px;">
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

if st.sidebar.button("登出"):
    st.session_state.user_id = None
    if 'menu_radio' in st.session_state:
        del st.session_state['menu_radio']
    st.rerun()

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
    
    # 隱藏未簽核時殘留的舊備份資料
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
    lg_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:50px;">' if logo_b64 else ''
    
    h = f'<div style="padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += f'<div style="text-align:center; border-bottom:2px solid #000; padding-bottom:10px; margin-bottom:10px;">'
    h += f'<div style="display:flex; justify-content:center; align-items:center; gap:15px;">'
    if lg_html: 
        h += f'{lg_html}'
    h += f'<h2 style="margin:0; white-space:nowrap;">時研國際設計股份有限公司</h2></div>'
    h += f'<h3 style="margin:10px 0 0 0; letter-spacing:5px;">{sys_type_title}</h3></div>'
    
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += f'<tr><td bgcolor="#eee" width="15%">單號</td><td width="35%">{row["單號"]}</td><td bgcolor="#eee" width="15%">負責執行長</td><td width="35%">{clean_name(row["專案負責人"])}</td></tr>'
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
                st.info(f"📝 修改中: {st.session_state.edit_id}")
                dv["app"] = clean_name(row.get("申請人", curr_name)) if clean_name(row.get("申請人", curr_name)) in staffs else curr_name
                dv["pn"] = str(row.get("專案名稱", ""))
                dv["exe"] = clean_name(row.get("專案負責人", staffs[0])) if clean_name(row.get("專案負責人", staffs[0])) in staffs else staffs[0]
                dv["pi"] = str(row.get("專案編號", ""))
                dv["amt"] = clean_amount(row.get("總金額", 0))
                dv["curr"] = str(row.get("幣別", "TWD")) if str(row.get("幣別", "TWD")) in curr_options else "TWD"
                dv["pay"] = str(row.get("付款方式", "現金"))
                dv["vdr"] = str(row.get("請款廠商", ""))
                dv["acc"] = str(row.get("匯款帳戶", ""))
                dv["desc"] = str(row.get("請款說明", ""))
                dv["ab64"] = str(row.get("帳戶影像Base64", ""))
                dv["ib64"] = str(row.get("影像Base64", ""))
                
                dv["pay_cond"] = str(row.get("支付條件", ""))
                dv["pay_inst"] = str(row.get("支付期數", ""))
                dv["final_amt"] = clean_amount(row.get("最後採購金額", 0))
                dv["billed_amt"] = clean_amount(row.get("已請款金額", 0))
                dv["unbilled_amt"] = clean_amount(row.get("尚未請款金額", 0))
                dv["bill_stat"] = str(row.get("請款狀態", ""))

        with st.form("form"):
            mode_suffix = f"{st.session_state.edit_id}_{st.session_state.form_key}" if st.session_state.edit_id else f"new_{st.session_state.form_key}"
            c1, c2 = st.columns(2)
            
            if curr_name == "Anita":
                app_val = c1.selectbox("申請人 (可代申請)", staffs, index=staffs.index(dv["app"]) if dv["app"] in staffs else staffs.index(curr_name), key=f"app_{mode_suffix}")
            else:
                app_val = curr_name
                c1.text_input("申請人", value=app_val, disabled=True, key=f"app_{mode_suffix}")
                
            pn = c1.text_input("專案名稱", value=dv["pn"], key=f"pn_{mode_suffix}")
            exe = c1.selectbox("負責執行長", staffs, index=staffs.index(dv["exe"]), key=f"exe_{mode_suffix}")
            
            pi = c2.text_input("專案編號", value=dv["pi"], key=f"pi_{mode_suffix}")
            
            amt_label = "預計採購金額" if sys_save_type == "採購單" else "總金額"
            amt = c2.number_input(amt_label, value=int(max(0, dv["amt"])), min_value=0, key=f"amt_{mode_suffix}")
            
            currency = c2.selectbox("幣別", curr_options, index=curr_options.index(dv["curr"]), key=f"curr_{mode_suffix}")
            
            pay_cond, pay_inst, final_amt, billed_amt, unbilled_amt, bill_stat = "", "", 0, 0, 0, ""
            if sys_save_type == "採購單":
                st.markdown("---")
                st.markdown("**(採購單專屬欄位 - 皆為非必填)**")
                cp1, cp2, cp3 = st.columns(3)
                pay_cond = cp1.text_input("支付條件", value=dv["pay_cond"], key=f"pc_{mode_suffix}")
                pay_inst = cp2.text_input("支付期數", value=dv["pay_inst"], key=f"pi_{mode_suffix}")
                final_amt = cp3.number_input("最後採購金額", value=int(max(0, dv["final_amt"])), min_value=0, key=f"fa_{mode_suffix}")
                
                cp4, cp5, cp6 = st.columns(3)
                bill_stat = cp4.text_input("請款狀態", value=dv["bill_stat"], key=f"bs_{mode_suffix}")
                billed_amt = cp5.number_input("已請款金額", value=int(max(0, dv["billed_amt"])), min_value=0, key=f"ba_{mode_suffix}")
                unbilled_amt = cp6.number_input("尚未請款金額", value=int(max(0, dv["unbilled_amt"])), min_value=0, key=f"ua_{mode_suffix}")
                st.markdown("---")
            
            pay_idx = ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"].index(dv["pay"]) if dv["pay"] in ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"] else 1
            pay = st.radio("付款方式", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], index=pay_idx, horizontal=True, key=f"pay_{mode_suffix}")
            vdr = st.text_input("廠商", value=dv["vdr"], key=f"vdr_{mode_suffix}")
            acc = st.text_input("帳戶", value=dv["acc"], key=f"acc_{mode_suffix}")
            desc = st.text_area("說明", value=dv["desc"], key=f"desc_{mode_suffix}")
            
            del_acc = False
            if dv["ab64"]:
                st.write("✅ 已有存摺")
                if is_pdf(dv["ab64"]): 
                    st.markdown(f'<embed src="data:application/pdf;base64,{dv["ab64"]}" width="100%" height="200px" />', unsafe_allow_html=True)
                else: 
                    st.image(base64.b64decode(dv["ab64"]), width=200)
                del_acc = st.checkbox("❌ 刪除此存摺", key=f"da_{mode_suffix}")
            f_acc = st.file_uploader("上傳存摺", key=f"fa_{mode_suffix}")
            
            del_ims = False
            if dv["ib64"]:
                st.write("✅ 已有憑證")
                del_ims = st.checkbox("❌ 刪除所有憑證", key=f"di_{mode_suffix}")
            f_ims = st.file_uploader("上傳憑證", accept_multiple_files=True, key=f"fi_{mode_suffix}")
            
            if st.form_submit_button("💾 儲存", disabled=not is_active):
                db = load_data()
                if not (pn and pi and amt>0 and desc):
                    st.error("請確認必填欄位 (專案名稱、編號、金額、說明) 已填寫")
                else:
                    b_acc = base64.b64encode(f_acc.getvalue()).decode() if f_acc else ("" if del_acc else dv["ab64"])
                    b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else ("" if del_ims else dv["ib64"])
                    
                    sys_save_type = "採購單" if st.session_state.get('sys_choice') == "採購單系統" else "請款單"
                    proxy_val = curr_name if app_val != curr_name else ""
                    
                    if st.session_state.edit_id:
                        idx = db[db["單號"]==st.session_state.edit_id].index[0]
                        db.at[idx, "申請人"] = app_val
                        db.at[idx, "代申請人"] = proxy_val
                        db.at[idx, "專案名稱"] = pn
                        db.at[idx, "專案負責人"] = exe
                        db.at[idx, "專案編號"] = pi
                        db.at[idx, "總金額"] = amt
                        db.at[idx, "請款說明"] = desc
                        db.at[idx, "幣別"] = currency 
                        db.at[idx, "付款方式"] = pay
                        db.at[idx, "請款廠商"] = vdr
                        db.at[idx, "匯款帳戶"] = acc
                        db.at[idx, "帳戶影像Base64"] = b_acc
                        db.at[idx, "影像Base64"] = b_ims
                        if sys_save_type == "採購單":
                            db.at[idx, "支付條件"] = pay_cond
                            db.at[idx, "支付期數"] = pay_inst
                            db.at[idx, "最後採購金額"] = final_amt
                            db.at[idx, "請款狀態"] = bill_stat
                            db.at[idx, "已請款金額"] = billed_amt
                            db.at[idx, "尚未請款金額"] = unbilled_amt
                        st.session_state.edit_id = None
                    else:
                        today_str = datetime.date.today().strftime('%Y%m%d')
                        if not db.empty:
                            today_count = len(db[db["單號"].astype(str).str.startswith(today_str)])
                            next_num = today_count + 1
                        else:
                            next_num = 1
                        tid = f"{today_str}-{next_num:02d}"
                        
                        nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":sys_save_type, 
                              "申請人":app_val, "代申請人":proxy_val,
                              "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":desc, "總金額":amt, 
                              "幣別":currency, "付款方式":pay, "請款廠商":vdr, "匯款帳戶":acc, 
                              "帳戶影像Base64":b_acc, "狀態":"已儲存", "影像Base64":b_ims, "提交時間":"",
                              "申請人信箱":curr_name, "初審人":"", "初審時間":"", "複審人":"", "複審時間":"", "刪除人":"", "刪除時間":"", "刪除原因":"", "駁回原因":"",
                              "支付條件": pay_cond, "支付期數": pay_inst, "請款狀態": bill_stat, "已請款金額": billed_amt, "尚未請款金額": unbilled_amt, "最後採購金額": final_amt}
                        db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                        st.session_state.last_id = tid
                        st.session_state.form_key += 1
                    save_data(db)
                    st.success("成功")
                    st.rerun()

        if st.session_state.last_id:
            c1, c2, c3, c4, c5 = st.columns(5)
            
            temp_db = load_data()
            curr_row = temp_db[temp_db["單號"]==st.session_state.last_id]
            
            can_edit_or_submit = False
            if not curr_row.empty:
                curr_st = curr_row.iloc[0]["狀態"]
                if curr_st in ["已儲存", "草稿", "已駁回"] and is_active:
                    can_edit_or_submit = True

            if c1.button("🚀 提交", disabled=not can_edit_or_submit):
                idx = temp_db[temp_db["單號"]==st.session_state.last_id].index[0]
                temp_db.at[idx, "狀態"] = "待簽核"
                temp_db.at[idx, "提交時間"] = get_taiwan_time()
                
                temp_db.at[idx, "初審人"] = ""
                temp_db.at[idx, "初審時間"] = ""
                temp_db.at[idx, "複審人"] = ""
                temp_db.at[idx, "複審時間"] = ""
                temp_db.at[idx, "駁回原因"] = ""
                
                save_data(temp_db)
                
                exe_name = clean_name(temp_db.at[idx, "專案負責人"])
                send_line_message(f"🔔 【待簽核提醒】\n單號：{st.session_state.last_id}\n您有一筆新的表單需要進行簽核！", target_name=exe_name)
                
                st.success("已成功提交，等待主管簽核！")
                st.rerun()
                
            if c2.button("🔍 線上預覽"): 
                st.session_state.view_id = st.session_state.last_id
                st.rerun()
                
            if c3.button("🖨️ 線上列印"):
                target = temp_db[temp_db["單號"]==st.session_state.last_id].iloc[0]
                js = "var w=window.open();w.document.write('" + clean_for_js(render_html(target)) + "');w.print();w.close();"
                st.components.v1.html(f"<script>{js}</script>", height=0)
            
            if c4.button("✏️ 修改", disabled=not can_edit_or_submit):
                st.session_state.edit_id = st.session_state.last_id
                st.session_state.last_id = None
                st.rerun()
                
            if c5.button("🆕 下一筆"): 
                st.session_state.last_id = None
                st.rerun()

        st.divider()
        st.subheader("📋 申請追蹤清單")
        
        sys_type_display = "預計採購金額" if st.session_state.get('sys_choice') == "採購單系統" else "總金額"
        h1, h2, hx, h3, h4, h5, h6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        h1.write("**申請單號**")
        h2.write("**專案名稱**")
        hx.write("**負責執行長**")
        h3.write("**申請人**")
        h4.write(f"**{sys_type_display}**")
        h5.write("**狀態**")
        h6.write("**操作**") 
        
        sys_db = get_filtered_db()
        my_db = sys_db if is_admin else sys_db[sys_db["申請人"] == curr_name]
        
        for i, r in my_db.iterrows():
            c1, c2, cx, c3, c4, c5, c6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
            c1.write(r["單號"])
            c2.write(r["專案名稱"])
            cx.write(clean_name(r["專案負責人"]))
            c3.write(r["申請人"])
            c_cur = str(r.get('幣別','TWD')).replace("nan", "TWD")
            c4.write(f"{c_cur} ${clean_amount(r['總金額']):,.0f}")
            
            stt = r["狀態"]
            color = "blue" if stt in ["已儲存", "草稿"] else "orange" if stt in ["待簽核", "待初審", "待複審"] else "green" if stt == "已核准" else "red" if stt == "已駁回" else "gray"
            c5.markdown(f":{color}[**{stt}**]")
            
            with c6:
                b1, b2, b3, b4, b5, b6 = st.columns(6)
                
                is_own = (str(r["申請人"]).strip() == curr_name) or (str(r.get("代申請人", "")).strip() == curr_name)
                can_edit = (stt in ["已儲存", "草稿", "已駁回"]) and is_own and is_active
                
                is_po = (str(r["類型"]).strip() == "採購單")
                can_po_post_edit = (is_po and stt == "已核准" and is_active)
                
                if b1.button("提交", key=f"s{i}", disabled=not can_edit):
                    fresh_db = load_data()
                    idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    fresh_db.at[idx, "狀態"] = "待簽核" 
                    fresh_db.at[idx, "提交時間"] = get_taiwan_time()
                    
                    fresh_db.at[idx, "初審人"] = ""
                    fresh_db.at[idx, "初審時間"] = ""
                    fresh_db.at[idx, "複審人"] = ""
                    fresh_db.at[idx, "複審時間"] = ""
                    fresh_db.at[idx, "駁回原因"] = ""
                    
                    save_data(fresh_db)
                    
                    exe_name = clean_name(r['專案負責人'])
                    send_line_message(f"🔔 【待簽核提醒】\n單號：{r['單號']}\n您有一筆新的表單需要進行簽核！", target_name=exe_name)
                    
                    st.rerun()
                if b2.button("預覽", key=f"v{i}"): 
                    st.session_state.view_id = r["單號"]
                    st.rerun()
                if b3.button("列印", key=f"p{i}"):
                    js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                    st.components.v1.html('<script>' + js_p + '</script>', height=0)
                if b4.button("修改", key=f"e{i}", disabled=not can_edit): 
                    st.session_state.edit_id = r["單號"]
                    st.rerun()
                
                if can_po_post_edit:
                    with b5.popover("📝 更新"):
                        st.write("**採購單後續更新**")
                        new_bill_stat = st.text_input("請款狀態", value=str(r.get("請款狀態", "")), key=f"m1_bs_{i}")
                        new_billed = st.number_input("已請款金額", value=int(clean_amount(r.get("已請款金額", 0))), min_value=0, key=f"m1_ba_{i}")
                        new_unbilled = st.number_input("尚未請款金額", value=int(clean_amount(r.get("尚未請款金額", 0))), min_value=0, key=f"m1_ua_{i}")
                        new_desc = st.text_area("修改說明內容", value=str(r.get("請款說明", "")), key=f"m1_desc_{i}")
                        
                        if st.button("💾 儲存修改", key=f"m1_save_pur_{i}"):
                            fresh_db = load_data()
                            idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                            fresh_db.at[idx, "請款狀態"] = new_bill_stat
                            fresh_db.at[idx, "已請款金額"] = new_billed
                            fresh_db.at[idx, "尚未請款金額"] = new_unbilled
                            fresh_db.at[idx, "請款說明"] = new_desc
                            save_data(fresh_db)
                            st.success("採購單資訊已更新！")
                            time.sleep(0.5)
                            st.rerun()
                else:
                    if can_edit:
                        with b5.popover("刪除"):
                            reason = st.text_input("刪除原因", key=f"d_res_{i}")
                            if st.button("確認", key=f"d{i}"):
                                if not reason: 
                                    st.error("請輸入原因")
                                else:
                                    fresh_db = load_data()
                                    idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                                    fresh_db.at[idx, "狀態"] = "已刪除"
                                    fresh_db.at[idx, "刪除人"] = curr_name
                                    fresh_db.at[idx, "刪除時間"] = get_taiwan_time()
                                    fresh_db.at[idx, "刪除原因"] = reason
                                    save_data(fresh_db)
                                    st.rerun()
                    else:
                        b5.button("刪除", disabled=True, key=f"fake_d_{i}")

                render_upload_popover(b6, r, f"m1_up_{i}")

    except Exception as e:
        st.error(f"系統發生預期外的錯誤，請截圖此畫面給開發者：{str(e)}")

# --- 頁面 2: 執行長簽核 ---
elif menu == "2. 專案執行長簽核":
    render_header()
    st.subheader("🔍 專案執行長簽核")
    
    try:
        sys_db = get_filtered_db()
        
        if is_admin:
            p_df = sys_db[sys_db["狀態"].isin(["待簽核", "待初審"])]
        else:
            p_df = sys_db[(sys_db["狀態"].isin(["待簽核", "待初審"])) & (sys_db["專案負責人"] == curr_name)]
        
        st.subheader("⏳ 待簽核清單")
        if p_df.empty: 
            st.info("目前無待簽核單據")
        else: 
            sys_type_display = "預計採購金額" if st.session_state.get('sys_choice') == "採購單系統" else "總金額"
            h1, h2, hx, h3, h4, h5, h6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
            h1.write("**單號**"); h2.write("**專案名稱**"); hx.write("**負責執行長**"); h3.write("**申請人**")
            h4.write(f"**{sys_type_display}**"); h5.write("**提交時間**"); h6.write("**操作**")
            
            for i, r in p_df.iterrows():
                c1, c2, cx, c3, c4, c5, c6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
                c1.write(r["單號"]); c2.write(r["專案名稱"]); cx.write(clean_name(r["專案負責人"]))
                c3.write(r["申請人"])
                c_cur = str(r.get('幣別','TWD')).replace("nan", "TWD")
                c4.write(f"{c_cur} ${clean_amount(r['總金額']):,.0f}")
                c5.write(r["提交時間"])
                
                with c6:
                    b1, b2, b3 = st.columns(3)
                    can_sign = (r["專案負責人"] == curr_name) and is_active
                    
                    if b1.button("預覽", key=f"ceo_v_{i}"): 
                        st.session_state.view_id = r["單號"]
                        st.rerun()
                    if b2.button("✅ 核准", key=f"ceo_ok_{i}", disabled=not can_sign):
                        fresh_db = load_data()
                        idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                        if str(fresh_db.at[idx, "類型"]).strip() == "採購單":
                            fresh_db.at[idx, "狀態"] = "已核准"
                            fresh_db.at[idx, "初審人"] = curr_name
                            fresh_db.at[idx, "初審時間"] = get_taiwan_time()
                            send_line_message(f"🔔 【採購單核准】\n單號：{r['單號']}\n執行長已核准此採購單！", target_name=clean_name(r["申請人"]))
                        else:
                            fresh_db.at[idx, "狀態"] = "待複審"
                            fresh_db.at[idx, "初審人"] = curr_name
                            fresh_db.at[idx, "初審時間"] = get_taiwan_time()
                            send_line_message(f"🔔 【待複審提醒】\n單號：{r['單號']}\n執行長已核准，需要財務長進行最終複審！", target_name=CFO_NAME)
                        
                        save_data(fresh_db)
                        st.rerun()
                        
                    if can_sign:
                        with b3.popover("❌ 駁回"):
                            reason = st.text_input("駁回原因", key=f"ceo_r_{i}")
                            if st.button("確認", key=f"ceo_no_{i}"):
                                fresh_db = load_data()
                                idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                                fresh_db.at[idx, "狀態"] = "已駁回"
                                fresh_db.at[idx, "駁回原因"] = reason
                                fresh_db.at[idx, "初審人"] = curr_name
                                fresh_db.at[idx, "初審時間"] = get_taiwan_time()
                                save_data(fresh_db); st.rerun()
                    else:
                        b3.button("❌ 駁回", disabled=True, key=f"fake_ceo_no_{i}")
        
        st.divider()
        st.subheader("📜 歷史紀錄 (已核准/已駁回)")
        
        # [精準修正] 歷史紀錄改用「狀態」來判斷，徹底解決備份還原後「初審人」空白導致紀錄消失的問題
        if is_admin: 
            h_df = sys_db[sys_db["狀態"].isin(["待複審", "已核准", "已駁回"])]
        else: 
            h_df = sys_db[(sys_db["專案負責人"] == curr_name) & (sys_db["狀態"].isin(["待複審", "已核准", "已駁回"]))]
            
        if h_df.empty: 
            st.info("尚無紀錄")
        else: 
            lh1, lh2, lnx, lh3, lh4, lh5, lh6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1, 3.5])
            lh1.write("**單號**"); lh2.write("**專案名稱**"); lnx.write("**負責執行長**"); lh3.write("**申請人**")
            lh4.write("**總金額**"); lh5.write("**狀態**"); lh6.write("**操作**")
            
            for i, r in h_df.iterrows():
                lc1, lc2, lcx, lc3, lc4, lc5, lc6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1, 3.5])
                lc1.write(r["單號"]); lc2.write(r["專案名稱"]); lcx.write(clean_name(r["專案負責人"]))
                lc3.write(r["申請人"])
                c_cur = str(r.get('幣別','TWD')).replace("nan", "TWD")
                lc4.write(f"{c_cur} ${clean_amount(r['總金額']):,.0f}")
                lc5.write(r["狀態"])
                
                with lc6:
                    lb1, lb2, lb3, lb4 = st.columns(4)
                    if lb1.button("🔍 預覽", key=f"h_ceo_v_{i}"): 
                        st.session_state.view_id = r["單號"]
                        st.rerun()
                    if lb2.button("🖨️ 列印", key=f"h_ceo_p_{i}"):
                        js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                        st.components.v1.html('<script>' + js_p + '</script>', height=0)
                    
                    is_po = (str(r["類型"]).strip() == "採購單")
                    can_ceo_edit = (r["專案負責人"] == curr_name) and is_active and ((is_po and r["狀態"] == "已核准") or (not is_po and r["狀態"] == "待複審"))
                    
                    if can_ceo_edit:
                        if is_po and r["狀態"] == "已核准":
                            with lb3.popover("📝 更新"):
                                st.write("**📝 採購單後續修改**")
                                new_bill_stat = st.text_input("請款狀態", value=str(r.get("請款狀態", "")), key=f"c_bs_{i}")
                                new_billed = st.number_input("已請款金額", value=int(clean_amount(r.get("已請款金額", 0))), min_value=0, key=f"c_ba_{i}")
                                new_unbilled = st.number_input("尚未請款金額", value=int(clean_amount(r.get("尚未請款金額", 0))), min_value=0, key=f"c_ua_{i}")
                                new_desc = st.text_area("修改說明內容", value=str(r.get("請款說明", "")), key=f"c_desc_{i}")
                                
                                if st.button("💾 儲存修改", key=f"ceo_save_pur_{i}"):
                                    fresh_db = load_data()
                                    idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                                    fresh_db.at[idx, "請款狀態"] = new_bill_stat
                                    fresh_db.at[idx, "已請款金額"] = new_billed
                                    fresh_db.at[idx, "尚未請款金額"] = new_unbilled
                                    fresh_db.at[idx, "請款說明"] = new_desc
                                    save_data(fresh_db)
                                    st.success("採購單資訊已更新！")
                                    time.sleep(0.5)
                                    st.rerun()
                        else:
                            with lb3.popover("✏️ 修改"):
                                st.write("**📝 僅限修改說明或直接駁回**")
                                new_desc = st.text_area("修改說明內容", value=str(r.get("請款說明", "")), key=f"ceo_desc_{i}")
                                if st.button("💾 儲存說明", key=f"ceo_save_desc_{i}"):
                                    fresh_db = load_data()
                                    idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                                    fresh_db.at[idx, "請款說明"] = new_desc
                                    save_data(fresh_db)
                                    st.success("說明已成功更新！")
                                    time.sleep(0.5)
                                    st.rerun()
                                
                                st.divider()
                                rej_reason = st.text_input("撤回並駁回之原因", key=f"ceo_rej_r_{i}")
                                if st.button("❌ 撤回並駁回", key=f"ceo_rej_btn_{i}"):
                                    if not rej_reason:
                                        st.error("請填寫駁回原因")
                                    else:
                                        fresh_db = load_data()
                                        idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                                        fresh_db.at[idx, "狀態"] = "已駁回"
                                        fresh_db.at[idx, "駁回原因"] = rej_reason
                                        fresh_db.at[idx, "初審人"] = curr_name
                                        fresh_db.at[idx, "初審時間"] = get_taiwan_time()
                                        save_data(fresh_db)
                                        st.success("已改為駁回！")
                                        time.sleep(0.5)
                                        st.rerun()
                    else:
                        lb3.button("✏️ 修改", disabled=True, key=f"fake_ceo_edit_{i}")

                    render_upload_popover(lb4, r, f"ceo_h_up_{i}")

    except Exception as e:
        st.error(f"載入頁面時發生異常，請聯絡管理員確認資料庫是否正確。錯誤訊息：{str(e)}")

# --- 頁面 3: 財務長簽核 ---
elif menu == "3. 財務長簽核":
    render_header()
    st.subheader("🏁 財務長簽核")
    
    try:
        sys_db = get_filtered_db()
        
        st.subheader("⏳ 待財務長簽核")
        if is_admin or curr_name == CFO_NAME:
            p_df = sys_db[sys_db["狀態"] == "待複審"]
        else:
            p_df = sys_db[(sys_db["狀態"] == "待複審") & (sys_db["專案負責人"] == curr_name)]
            
        if p_df.empty: 
            st.info("無待審單據")
        else: 
            h1, h2, hx, h3, h4, h5 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 2.5])
            h1.write("**單號**"); h2.write("**專案名稱**"); hx.write("**負責執行長**")
            h3.write("**申請人**"); h4.write("**總金額**"); h5.write("**操作**")

            for i, r in p_df.iterrows():
                c1, c2, cx, c3, c4, c5 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 2.5])
                c1.write(r["單號"]); c2.write(r["專案名稱"]); cx.write(clean_name(r["專案負責人"]))
                c3.write(r["申請人"])
                c_cur = str(r.get('幣別','TWD')).replace("nan", "TWD")
                c4.write(f"{c_cur} ${clean_amount(r['總金額']):,.0f}")
                
                with c5:
                    b1, b2, b3 = st.columns(3)
                    is_cfo_action = (curr_name == CFO_NAME) and is_active
                    
                    if b1.button("預覽", key=f"cfo_v_{i}"): 
                        st.session_state.view_id = r["單號"]
                        st.rerun()
                    if b2.button("👑 核准", key=f"cok_{i}", disabled=not is_cfo_action):
                        fresh_db = load_data()
                        idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                        fresh_db.at[idx, "狀態"] = "已核准"
                        fresh_db.at[idx, "複審人"] = curr_name
                        fresh_db.at[idx, "複審時間"] = get_taiwan_time()
                        save_data(fresh_db); st.rerun()
                    
                    if is_cfo_action:
                        with b3.popover("❌ 駁回"):
                            reason = st.text_input("原因", key=f"cr_{i}")
                            if st.button("確認", key=f"cno_{i}"):
                                fresh_db = load_data()
                                idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                                fresh_db.at[idx, "狀態"] = "已駁回"
                                fresh_db.at[idx, "駁回原因"] = reason
                                fresh_db.at[idx, "複審人"] = curr_name 
                                fresh_db.at[idx, "複審時間"] = get_taiwan_time()
                                save_data(fresh_db); st.rerun()
                    else:
                        b3.button("❌ 駁回", disabled=True, key=f"fake_cfo_no_{i}")

        st.divider()
        st.subheader("📜 歷史紀錄 (已核准/已駁回)")
        
        # [精準修正] 歷史紀錄改用「狀態」來判斷，徹底解決備份還原後「複審人」空白導致紀錄消失的問題
        if is_admin or curr_name == CFO_NAME:
            f_df = sys_db[sys_db["狀態"].isin(["已核准", "已駁回"])]
        else:
            f_df = sys_db[(sys_db["專案負責人"] == curr_name) & (sys_db["狀態"].isin(["已核准", "已駁回"]))]
            
        if f_df.empty: 
            st.info("尚無紀錄")
        else: 
            lh1, lh2, lnx, lh3, lh4, lh5, lh6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1, 3.5])
            lh1.write("**單號**"); lh2.write("**專案名稱**"); lnx.write("**負責執行長**"); lh3.write("**申請人**")
            lh4.write("**總金額**"); lh5.write("**狀態**"); lh6.write("**操作**")
            
            for i, r in f_df.iterrows():
                lc1, lc2, lcx, lc3, lc4, lc5, lc6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1, 3.5])
                lc1.write(r["單號"]); lc2.write(r["專案名稱"]); lcx.write(clean_name(r["專案負責人"]))
                lc3.write(r["申請人"])
                c_cur = str(r.get('幣別','TWD')).replace("nan", "TWD")
                lc4.write(f"{c_cur} ${clean_amount(r['總金額']):,.0f}")
                lc5.write(r["狀態"])
                
                with lc6:
                    lb1, lb2, lb3 = st.columns(3)
                    if lb1.button("🔍 預覽", key=f"h_cfo_v_{i}"): 
                        st.session_state.view_id = r["單號"]
                        st.rerun()
                    if lb2.button("🖨️ 列印", key=f"h_cfo_p_{i}"):
                        js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                        st.components.v1.html('<script>' + js_p + '</script>', height=0)
                    
                    render_upload_popover(lb3, r, f"cfo_h_up_{i}")

    except Exception as e:
        st.error(f"載入頁面時發生異常，請聯絡管理員確認資料庫是否正確。錯誤訊息：{str(e)}")

# --- 頁面 4: 表單狀態總覽 ---
elif menu == "4. 表單狀態總覽":
    render_header()
    st.subheader("📊 表單狀態總覽")
    try:
        sys_db = get_filtered_db()
        
        if not is_admin:
            sys_db = sys_db[(sys_db["申請人"] == curr_name) | (sys_db["代申請人"] == curr_name) | (sys_db["專案負責人"] == curr_name)]
            
        display_df = sys_db.copy()
        if not display_df.empty:
            
            is_po_sys = (st.session_state.get('sys_choice') == "採購單系統")
            if is_po_sys:
                st.info("💡 勾選採購單並輸入「本次請款金額」，即可一鍵為 Anita 建立新的請款單草稿！")
                display_df.insert(0, "轉成請款單", False)
                display_df.insert(1, "本次請款金額", 0)
                
            display_df["負責執行長"] = display_df["專案負責人"]
            display_df["預計採購/總金額"] = display_df.apply(lambda x: f"{str(x.get('幣別','TWD')).replace('nan','TWD')} ${clean_amount(x.get('總金額',0)):,.0f}", axis=1)
            
            display_df["請款狀態"] = display_df["請款狀態"].fillna("").astype(str)
            display_df["已請款金額"] = display_df["已請款金額"].apply(clean_amount)
            display_df["尚未請款金額"] = display_df["尚未請款金額"].apply(clean_amount)
            
            display_df = display_df.rename(columns={"單號": "申請單號"})
            
            if is_po_sys:
                target_cols = ["轉成請款單", "本次請款金額", "申請單號", "專案名稱", "負責執行長", "申請人", "預計採購/總金額", "狀態", "請款狀態", "已請款金額", "尚未請款金額"]
                edited_df = st.data_editor(
                    display_df[target_cols],
                    disabled=["申請單號", "專案名稱", "負責執行長", "申請人", "預計採購/總金額", "狀態", "請款狀態", "已請款金額", "尚未請款金額"],
                    use_container_width=True,
                    column_config={
                        "轉成請款單": st.column_config.CheckboxColumn("勾選轉換"),
                        "本次請款金額": st.column_config.NumberColumn("本次請款金額", min_value=0, step=1),
                    }
                )
                
                if st.button("🚀 確認將勾選項目轉成請款單"):
                    fresh_db = load_data()
                    converted_count = 0
                    for i, row in edited_df.iterrows():
                        conv_amt = row.get("本次請款金額")
                        if bool(row.get("轉成請款單")) and pd.notna(conv_amt) and int(float(conv_amt)) > 0:
                            orig_id = row["申請單號"]
                            orig_idx = fresh_db[fresh_db["單號"]==orig_id].index[0]
                            orig_row = fresh_db.iloc[orig_idx]
                            
                            real_conv_amt = int(float(conv_amt))
                            
                            current_billed = clean_amount(orig_row.get("已請款金額", 0))
                            new_billed = current_billed + real_conv_amt
                            
                            final_amt = clean_amount(orig_row.get("最後採購金額", 0))
                            if final_amt == 0: 
                                final_amt = clean_amount(orig_row.get("總金額", 0))
                            
                            new_unbilled = final_amt - new_billed
                            if new_unbilled < 0: 
                                new_unbilled = 0
                            
                            fresh_db.at[orig_idx, "已請款金額"] = new_billed
                            fresh_db.at[orig_idx, "尚未請款金額"] = new_unbilled
                            fresh_db.at[orig_idx, "請款狀態"] = "已轉請款單"
                            
                            today_str = datetime.date.today().strftime('%Y%m%d')
                            today_count = len(fresh_db[fresh_db["單號"].astype(str).str.startswith(today_str)])
                            new_tid = f"{today_str}-{today_count+1:02d}"
                            
                            nr = {
                                "單號": new_tid, "日期": str(datetime.date.today()), "類型": "請款單", 
                                "申請人": "Anita", "代申請人": "", 
                                "專案負責人": orig_row.get("專案負責人",""), "專案名稱": orig_row.get("專案名稱",""), 
                                "專案編號": orig_row.get("專案編號",""), 
                                "請款說明": f"自採購單 {orig_id} 轉換", "總金額": real_conv_amt, 
                                "幣別": orig_row.get("幣別","TWD"), "付款方式": orig_row.get("付款方式",""), 
                                "請款廠商": orig_row.get("請款廠商",""), "匯款帳戶": orig_row.get("匯款帳戶",""), 
                                "帳戶影像Base64": orig_row.get("帳戶影像Base64",""), "狀態": "已儲存", "影像Base64": orig_row.get("影像Base64",""), "提交時間": "",
                                "申請人信箱": "Anita", "初審人": "", "初審時間": "", "複審人": "", "複審時間": "", "刪除人": "", "刪除時間": "", "刪除原因": "", "駁回原因": "",
                                "支付條件": "", "支付期數": "", "請款狀態": "", "已請款金額": 0, "尚未請款金額": 0, "最後採購金額": 0
                            }
                            fresh_db = pd.concat([fresh_db, pd.DataFrame([nr])], ignore_index=True)
                            converted_count += 1
                    
                    if converted_count > 0:
                        save_data(fresh_db)
                        st.success(f"✅ 成功轉換 {converted_count} 筆！請切換至「請款單系統」由 Anita 進行後續提交。")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.warning("請確保有勾選項目，且輸入金額大於 0！")
                        
            else:
                target_cols = ["申請單號", "專案名稱", "負責執行長", "申請人", "預計採購/總金額", "狀態", "匯款狀態", "匯款日期"]
                st.dataframe(display_df[target_cols], use_container_width=True)
        else:
            st.info("尚無您的表單狀態紀錄。")
    except Exception as e:
        st.error(f"系統發生預期外的錯誤，請截圖此畫面給開發者：{str(e)}")

# --- 頁面 5: 請款狀態/系統設定 ---
elif menu == "5. 請款狀態/系統設定":
    render_header()
    
    st.error("⚠️ **雲端暫存機制提醒：** 免費雲端主機重啟會清空資料。請管理員務必在下班前下載備份！")
    
    with st.expander("💾 1. 表單資料庫備份與還原", expanded=True):
        col_down, col_up = st.columns(2)
        with col_down:
            st.write("⬇️ **步驟一：下載最新表單資料庫**")
            if os.path.exists(D_FILE):
                with open(D_FILE, "rb") as f:
                    st.download_button("下載表單備份檔", f, file_name=f"時研系統表單備份_{datetime.date.today()}.csv", mime="text/csv")
        with col_up:
            st.write("⬆️ **步驟二：還原表單資料庫**")
            uploaded_db = st.file_uploader("上傳表單 CSV 檔", type=["csv"], key="up_db", label_visibility="collapsed")
            if uploaded_db and st.button("確認還原表單"):
                with open(D_FILE, "wb") as f:
                    f.write(uploaded_db.getbuffer())
                st.success("表單資料庫已還原！")
                time.sleep(1)
                st.rerun()

    with st.expander("👥 2. 人員與大頭貼資料備份與還原"):
        col_down2, col_up2 = st.columns(2)
        with col_down2:
            st.write("⬇️ **步驟一：下載最新人員資料 (含大頭貼與LINE ID)**")
            if os.path.exists(S_FILE):
                with open(S_FILE, "rb") as f:
                    st.download_button("下載人員備份檔", f, file_name=f"時研系統人員備份_{datetime.date.today()}.csv", mime="text/csv")
        with col_up2:
            st.write("⬆️ **步驟二：還原人員資料**")
            uploaded_staff = st.file_uploader("上傳人員 CSV 檔", type=["csv"], key="up_staff", label_visibility="collapsed")
            if uploaded_staff and st.button("確認還原人員資料"):
                with open(S_FILE, "wb") as f:
                    f.write(uploaded_staff.getbuffer())
                st.session_state.staff_df = load_staff()
                st.success("人員資料已還原！")
                time.sleep(1)
                st.rerun()

    with st.expander("🔔 3. LINE 官方帳號推播設定 (全域 Token & 行政副本 ID)"):
        st.write("請填寫從 LINE Developers 取得的兩組關鍵代碼：")
        curr_token, curr_uid = get_line_credentials()
        new_token = st.text_input("Channel Access Token (長字串)", value=curr_token, type="password")
        new_uid = st.text_input("行政專屬 User ID (U開頭，用來接收所有副本)", value=curr_uid)
        if st.button("💾 儲存 LINE 設定"):
            save_line_credentials(new_token, new_uid) 
            st.success("LINE 推播設定已成功儲存並啟用！")
            time.sleep(1)
            st.rerun()

    st.divider()
    st.subheader("💰 請款狀態 (Admin)")
    st.info("💡 溫馨提醒：此處編輯的「匯款狀態」與「匯款日期」都已包含在上方的「表單資料庫備份」中，還原時會一併恢復，無須重新手動輸入！")
    
    try:
        sys_db = get_filtered_db()
        display_df = sys_db.copy()
        if not display_df.empty:
            display_df["負責執行長"] = display_df["專案負責人"]
            display_df["總金額"] = display_df.apply(lambda x: f"{str(x.get('幣別','TWD')).replace('nan','TWD')} ${clean_amount(x.get('總金額',0)):,.0f}", axis=1)
            display_df = display_df.rename(columns={"單號": "申請單號"})
            
            def parse_date(d_str):
                if pd.isna(d_str) or str(d_str).strip() == "": return None
                try: return datetime.datetime.strptime(str(d_str).strip(), "%Y-%m-%d").date()
                except Exception: return None
                
            display_df["匯款日期"] = display_df["匯款日期"].apply(parse_date)
            
            target_cols = ["申請單號", "專案名稱", "負責執行長", "申請人", "總金額", "狀態", "匯款狀態", "匯款日期"]
            
            edited_df = st.data_editor(
                display_df[target_cols],
                disabled=["申請單號", "專案名稱", "負責執行長", "申請人", "總金額", "狀態"],
                use_container_width=True,
                column_config={
                    "匯款狀態": st.column_config.SelectboxColumn(
                        "匯款狀態",
                        options=["尚未匯款", "已匯款"],
                        required=True,
                        width="medium"
                    ),
                    "匯款日期": st.column_config.DateColumn(
                        "匯款日期",
                        format="YYYY-MM-DD",
                        width="medium",
                        min_value=datetime.date(2020, 1, 1),
                        max_value=datetime.date(2030, 12, 31)
                    )
                }
            )
            
            if st.button("💾 儲存匯款資訊"):
                valid = True
                for i, row in edited_df.iterrows():
                    if row["匯款狀態"] == "已匯款" and (pd.isna(row["匯款日期"]) or str(row["匯款日期"]) == "NaT"):
                        st.error(f"❌ 申請單號 {row['申請單號']}：選擇「已匯款」時，必須填寫匯款日期！")
                        valid = False
                
                if valid:
                    fresh_db = load_data()
                    for i, row in edited_df.iterrows():
                        orig_idx = fresh_db[fresh_db["單號"]==row["申請單號"]].index[0]
                        fresh_db.at[orig_idx, "匯款狀態"] = str(row["匯款狀態"]) if row["匯款狀態"] else "尚未匯款"
                        
                        date_val = row["匯款日期"]
                        if pd.notna(date_val) and str(date_val) != "NaT":
                            fresh_db.at[orig_idx, "匯款日期"] = str(date_val)
                        else:
                            fresh_db.at[orig_idx, "匯款日期"] = ""
                    
                    save_data(fresh_db)
                    st.success("✅ 匯款資訊已成功更新！")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("尚無請款單/採購單資料。")
    except Exception as e:
        st.error(f"載入頁面時發生異常，請聯絡管理員確認資料庫是否正確。錯誤訊息：{str(e)}")

# [全域預覽] 放在最底下確保渲染
if st.session_state.view_id:
    st.markdown("---")
    try:
        r = load_data(); r = r[r["單號"]==st.session_state.view_id]
        if not r.empty:
            c1, c2 = st.columns([8, 2])
            c1.markdown("### 🔍 表單預覽")
            if c2.button("❌ 關閉預覽", key="close_view"): 
                st.session_state.view_id = None
                st.rerun()
            st.markdown(render_html(r.iloc[0]), unsafe_allow_html=True)
    except Exception as e:
        st.error(f"預覽發生錯誤：{str(e)}")
