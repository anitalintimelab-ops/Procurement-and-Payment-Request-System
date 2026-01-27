import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re

# --- 1. 系統環境與權限定義 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")

MANAGERS = ["Anita", "Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖"]

# --- 密碼驗證邏輯 ---
def validate_password(pw):
    # 規則：至少一個英文，且數字需為 4-6 位
    has_letter = bool(re.search(r'[a-zA-Z]', pw))
    digit_count = len(re.findall(r'\d', pw))
    return has_letter and 4 <= digit_count <= 6

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"]
    if os.path.exists(D_FILE):
        try:
            df = pd.read_csv(D_FILE).fillna("")
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: pass
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.reset_index(drop=True).to_csv(D_FILE, index=False)

def load_staff():
    if os.path.exists(S_FILE):
        try:
            df = pd.read_csv(S_FILE).fillna("在職")
            # 如果舊資料沒有密碼欄位，自動補上預設值 0000
            if "password" not in df.columns:
                df["password"] = "0000"
            return df.reset_index(drop=True)
        except: pass
    d = {"name": ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita"],
         "status": ["在職", "在職", "在職", "在職", "在職"],
         "password": ["0000", "0000", "0000", "0000", "0000"]}
    return pd.DataFrame(d)

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False)

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            fn = f.lower()
            if any(x in fn for x in [".jpg",".png",".jpeg"]):
                if "timelab" in fn or "logo" in fn:
                    p = os.path.join(B_DIR, f); im = open(p, "rb")
                    return base64.b64encode(im.read()).decode()
    except: pass
    return ""

def clean_for_js(h_str):
    return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入識別畫面 ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    st.info("請選取您的身分並輸入密碼")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    sel_u = st.selectbox("我的身分：", u_list)
    input_pw = st.text_input("輸入密碼：", type="password")
    
    if st.button("確認進入"):
        if sel_u != "--- 請選擇 ---":
            # 驗證密碼
            target_pw = st.session_state.staff_df[st.session_state.staff_df["name"] == sel_u]["password"].values[0]
            if input_pw == str(target_pw):
                st.session_state.user_id = sel_u
                st.rerun()
            else:
                st.error("❌ 密碼錯誤，請重新輸入。")
    st.stop()

curr_name = st.session_state.user_id
is_admin = (curr_name == "Anita")
is_manager = (curr_name in MANAGERS)

# --- 3. 側邊欄工具與選單過濾 ---
st.sidebar.markdown(f"### 👤 目前登入：{curr_name}")

# --- 個人設定：修改密碼 ---
with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password", help="需包含至少一個英文字母且數字為 4-6 位")
    confirm_pw = st.text_input("確認新密碼", type="password")
    if st.button("更新密碼"):
        if new_pw != confirm_pw:
            st.error("兩次輸入不符")
        elif not validate_password(new_pw):
            st.error("不符合規則：至少一英文+數字4-6位")
        else:
            idx = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].index[0]
            st.session_state.staff_df.at[idx, "password"] = new_pw
            save_staff(st.session_state.staff_df)
            st.success("密碼修改成功！")

if is_admin:
    st.sidebar.success("身分：管理員")
    with st.sidebar.expander("⚙️ 管理員工具"):
        new_p = st.text_input("1. 新增同事姓名")
        if st.button("➕ 確認新增"):
            if not new_p: st.sidebar.warning("請輸入姓名")
            elif new_p in st.session_state.staff_df["name"].tolist():
                st.sidebar.error("該員已重複新增")
            else:
                new_row = pd.DataFrame({"name": [new_p], "status": ["在職"], "password": ["0000"]})
                st.session_state.staff_df = pd.concat([st.session_state.staff_df, new_row], ignore_index=True)
                save_staff(st.session_state.staff_df)
                st.sidebar.success("該員新增完成 (預設密碼 0000)")
                st.rerun()
        st.divider()
        st.write("2. 人員與密碼管理")
        for i, r in st.session_state.staff_df.iterrows():
            if r["name"] == "Anita" and not is_admin: continue 
            with st.container():
                c1, c2, c3 = st.columns([1.5, 1.5, 1])
                c1.write(f"**{r['name']}**")
                # 管理員可見密碼
                c2.code(r["password"])
                if c3.button("重設", key=f"reset_pw_{i}", help="恢復
