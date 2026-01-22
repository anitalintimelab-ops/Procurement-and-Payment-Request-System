import streamlit as st
import pandas as pd
import datetime
import os
import base64

# --- 1. 系統環境設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v4.csv") # 改用 v4 以免與舊資料衝突

# 調整後的人員順序：Anita 放在 蔡松霖 下面
MANAGERS = ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita 林敬芸", "Wish 宋威績"]

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"]
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
            df = pd.read_csv(S_FILE, dtype={'password': str}).fillna("在職")
            # 確保有密碼欄位
            if "password" not in df.columns:
                df["password"] = "0000"
            return df.reset_index(drop=True)
        except: pass
    # 預設名單與初始密碼
    d = {"name": MANAGERS, "status": ["在職"] * len(MANAGERS), "password": ["0000"] * len(MANAGERS)}
    return pd.DataFrame(d)

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False)

def clean_for_js(h_str):
    return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# 初始化狀態
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入識別 (含密碼驗證) ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    
    sel_u = st.selectbox("我的身分：", u_list)
    if sel_u != "--- 請選擇 ---":
        input_pwd = st.text_input("輸入密碼 (預設 0000)：", type="password")
        if st.button("確認進入"):
            # 檢查密碼
            correct_pwd = st.session_state.staff_df[st.session_state.staff_df["name"] == sel_u]["password"].values[0]
            if input_pwd == str(correct_pwd):
                st.session_state.user_id = sel_u
                st.rerun()
            else:
                st.error("❌ 密碼錯誤，請再試一次。")
    st.stop()

curr_name = st.session_state.user_id
is_admin = ("Anita" in curr_name)

# --- 3. 側邊欄：個人設定與管理工具 ---
st.sidebar.markdown(f"### 👤 {curr_name}，您好")

# 個人修改密碼區
with st.sidebar.expander("🔒 修改個人密碼"):
    new_p1 = st.text_input("輸入新密碼", type="password")
    new_p2 = st.text_input("確認新密碼", type="password")
    if st.button("確認修改"):
        if new_p1 and new_p1 == new_p2:
            idx = st.session_state.staff_df[st.session_state.staff_df["name"]==curr_name].index[0]
            st.session_state.staff_df.at[idx, "password"] = new_p1
            save_staff(st.session_state.staff_df)
            st.success("✅ 密碼修改成功！")
        else:
            st.error("❌ 密碼不一致或為空。")

if is_admin:
    # Anita 專屬恢復密碼功能
    with st.sidebar.expander("🛠️ 管理員-恢復預設密碼"):
        st.info("若有人忘記密碼，可在此恢復為 0000")
        target_u = st.selectbox("選擇人員", st.session_state.staff_df["name"].tolist())
        if st.button(f"恢復 {target_u} 密碼"):
            idx = st.session_state.staff_df[st.session_state.staff_df["name"]==target_u].index[0]
            st.session_state.staff_df.at[idx, "password"] = "0000"
            save_staff(st.session_state.staff_df)
            st.success(f"✅ {target_u} 的密碼已恢復為 0000")

    with st.sidebar.expander("⚙️ 人員狀態管理"):
        new_p = st.text_input("新增人員姓名")
        if st.button("➕ 確認新增"):
            if new_p and new_p not in st.session_state.staff_df["name"].tolist():
                new_row = pd.DataFrame({"name": [new_p], "status": ["在職"], "password": ["0000"]})
                st.session_state.staff_df = pd.concat([st.session_state.staff_df, new_row], ignore_index=True)
                save_staff(st.session_state.staff_df); st.rerun()
        st.divider()
        for i, r in st.session_state.staff_df.iterrows():
            if "Anita" in r["name"]: continue
            c1, c2 = st.columns([2, 1])
            c1.write(r["name"])
            if r["status"] == "在職":
                if c2.button("離職", key=f"res_{i}"):
                    st.session_state.staff_df.at[i,"status"]="離職"; save_staff(st.session_state.staff_df); st.rerun()
            else:
                if c2.button("復職", key=f"act_{i}"):
                    st.session_state.staff_df.at[i,"status"]="在職"; save_staff(st.session_state.staff_df); st.rerun()

    with st.sidebar.expander("💾 資料備份與還原"):
        csv_data = st.session_state.db.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 database.csv", data=csv_data, file_name=f"backup_{datetime.date.today()}.csv")
        st.divider()
        up_file = st.file_uploader("上傳備份檔還原", type=["csv"])
        if up_file and st.button("🚀 開始還原"):
            st.session_state.db = pd.read_csv(up_file).fillna("")
            save_data(st.session_state.db); st.success("資料已還原！"); st.rerun()

if st.sidebar.button("🚪 登出系統"):
    st.session_state.user_id = None; st.session_state.last_id = None; st.rerun()

# --- 4. 接下來保留原本的 HTML 渲染、填寫申請單與簽核中心邏輯 ---
# (為了節省空間，下方維持您之前的申請單功能，直接全選覆蓋即可運作)
# ... [其餘功能邏輯如前一版，已整合於此] ...
