import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re
import time

# --- 1. 系統設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide", page_icon="🏢")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# [工具] 取得台灣時間
def get_taiwan_time():
    tw_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    return tw_time.strftime('%Y-%m-%d %H:%M')

# [工具] 金額清洗
def clean_amount(val):
    if pd.isna(val) or str(val).strip() == "": return 0
    s_val = str(val).replace(",", "").replace("$", "").replace("，", "").replace(" ", "")
    try:
        return int(float(s_val))
    except:
        return 0

# [工具] 名字清洗 (只留英文)
def clean_name(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).strip().split(" ")[0]

# [工具] 跳轉至修改頁面 (Callback - 解決 StreamlitAPIException)
def navigate_to_edit(eid):
    st.session_state.edit_id = eid
    st.session_state.menu_radio = "1. 填寫申請單"

# [工具] 追蹤在線人數
def get_online_users(curr_user):
    try:
        if not curr_user: return 1
        now = time.time()
        if os.path.exists(O_FILE):
            try:
                df = pd.read_csv(O_FILE)
            except:
                df = pd.DataFrame(columns=["user", "time"])
        else:
            df = pd.DataFrame(columns=["user", "time"])
        
        df = df[df["user"] != curr_user]
        df = pd.concat([df, pd.DataFrame([{"user": curr_user, "time": now}])], ignore_index=True)
        df = df[now - df["time"] <= 300]
        df.to_csv(O_FILE, index=False)
        return len(df["user"].unique())
    except:
        return 1

# --- 2. 自動救援資料 ---
def init_rescue_data():
    if not os.path.exists(D_FILE):
        data = {
            "單號": ["20260205-01"], "日期": ["2026-02-05"], "類型": ["請款單"],
            "申請人": ["Anita"], "專案負責人": ["Andy"], "專案名稱": ["公司費用"],
            "專案編號": ["GENERAL"], "請款說明": ["測試款項"], "總金額": [5500],
            "幣別": ["TWD"], "付款方式": ["現金"], "請款廠商": ["測試廠商"],
            "匯款帳戶": [""], "帳戶影像Base64": [""], "狀態": ["待簽核"],
            "影像Base64": [""], "提交時間": ["2026-02-05 14:00"], "申請人信箱": ["Anita"],
            "初審人": [""], "初審時間": [""], "複審人": [""], "複審時間": [""],
            "刪除人": [""], "刪除時間": [""], "刪除原因": [""], "駁回原因": [""],
            "匯款狀態": ["尚未匯款"], "匯款日期": [""]
        }
        df = pd.DataFrame(data)
        df.to_csv(D_FILE, index=False, encoding='utf-8-sig')

init_rescue_data()

# --- 3. 資料處理 ---
def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try:
            return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except:
            continue
    return pd.DataFrame()

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "專案負責人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱",
            "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", 
            "刪除原因", "駁回原因", "匯款狀態", "匯款日期"]
    
    df = read_csv_robust(D_FILE)
    if df is None or df.empty: return pd.DataFrame(columns=cols)
    if "專案執行人" in df.columns: df = df.rename(columns={"專案執行人": "專案負責人"})
    
    for c in cols:
        if c not in df.columns: df[c] = ""
            
    df["總金額"] = df["總金額"].apply(clean_amount)
    df["專案負責人"] = df["專案負責人"].astype(str).apply(clean_name)
    df["申請人"] = df["申請人"].astype(str).apply(clean_name)
    df["狀態"] = df["狀態"].astype(str).str.strip()
    return df[cols]

def save_data(df):
    try:
        df["總金額"] = df["總金額"].apply(clean_amount)
        df["專案負責人"] = df["專案負責人"].astype(str).apply(clean_name)
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError:
        st.error("⚠️ 警告：無法寫入檔案！請關閉 Excel。")
        st.stop()

def load_staff():
    default_df = pd.DataFrame({"name": DEFAULT_STAFF, "status": ["在職"]*5, "password": ["0000"]*5, "avatar": [""]*5})
    df = read_csv_robust(S_FILE)
    if df is None or df.empty:
        df = default_df.copy()
        df.to_csv(S_FILE, index=False, encoding='utf-8-sig')
        return df
    if "status" not in df.columns: df["status"] = "在職"
    if "avatar" not in df.columns: df["avatar"] = ""
    df["name"] = df["name"].str.strip()
    df["avatar"] = df["avatar"].fillna("")
    return df

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            if any(x in f.lower() for x in ["logo", "timelab"]) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                with open(os.path.join(B_DIR, f), "rb") as img:
                    return base64.b64encode(img.read()).decode()
    except: pass
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
if 'sys_choice' not in st.session_state: st.session_state.sys_choice = "請購單系統"
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
        sys_choice = st.selectbox("登入系統", ["請購單系統", "採購單系統"])
        
        if st.form_submit_button("登入"):
            row = staff_df[staff_df["name"] == u].iloc[0]
            stored_p = str(row["password"]).strip().replace(".0", "")
            if str(p).strip() == stored_p or (str(p).strip() == "0000" and stored_p in ["nan", ""]):
                st.session_state.user_id = u
                st.session_state.user_status = row["status"] if pd.notna(row["status"]) else "在職"
                st.session_state.staff_df = staff_df
                st.session_state.sys_choice = sys_choice
                st.rerun()
            else:
                st.error("密碼錯誤")
    st.stop()

curr_name = st.session_state.user_id
is_active = (st.session_state.user_status == "在職")
is_admin = (curr_name in ADMINS)

curr_user_row = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0]
avatar_b64 = curr_user_row.get("avatar", "")

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

if not is_active: st.sidebar.error("⛔ 已離職")

with st.sidebar.expander("📸 修改大頭貼"):
    new_avatar = st.file_uploader("上傳您的圖片", type=["jpg", "jpeg", "png"])
    if st.button("更新大頭貼", disabled=not is_active):
        if new_avatar is not None:
            b64 = base64.b64encode(new_avatar.getvalue()).decode()
            staff_df = st.session_state.staff_df
            idx = staff_df[staff_df["name"] == curr_name].index[0]
            staff_df.at[idx, "avatar"] = b64
            save_staff(staff_df)
            st.session_state
