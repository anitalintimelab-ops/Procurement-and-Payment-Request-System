import streamlit as st
import pandas as pd
import datetime
import os
import base64

# --- 1. 系統環境設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")

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
            return pd.read_csv(S_FILE).fillna("在職").reset_index(drop=True)
        except: pass
    d = {"name": ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita"],
         "status": ["在職", "在職", "在職", "在職", "在職"]}
    return pd.DataFrame(d)

def save_staff(df):
    df.to_csv(S_FILE, index=False)

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

# --- 2. 登入識別 ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    st.info("請選取您的身分以進入系統")
    # 僅顯示「在職」員工
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    sel_u = st.selectbox("我的身分：", u_list)
    if st.button("確認進入"):
        if sel_u != "--- 請選擇 ---":
            st.session_state.user_id = sel_u
            st.rerun()
    st.stop()

curr_name = st.session_state.user_id
is_admin = (curr_name == "Anita")

# --- 3. 側邊欄：身份與權限管理 ---
st.sidebar.markdown("### 👤 目前登入")
st.sidebar.markdown(curr_name)

if is_admin:
    st.sidebar.success("身分等級：管理員")
    with st.sidebar.expander("⚙️ 管理員工具"):
        new_p = st.text_input("1. 新增同事姓名")
        if st.button("➕ 確認新增"):
            if not new_p: st.sidebar.warning("請輸入姓名")
            elif new_p in st.session_state.staff_df["name"].tolist():
                st.sidebar.error("該員已重複新增")
            else:
                new_row = pd.DataFrame({"name": [new_p], "status": ["在職"]})
                st.session_state.staff_df = pd.concat([st.session_state.staff_df, new_row], ignore_index=True)
                save_staff(st.session_state.staff_df)
                st.sidebar.success("該員新增完成")
                st.rerun()
        st.divider()
        st.write("2. 人員狀態管理")
        for i, r in st.session_state.staff_df.reset_index(drop=True).iterrows():
            if r["name"] == "Anita": continue
            c1, c2 = st.columns([2, 1])
            c1.write(r["name"])
            if r["status"] == "在職":
                if c2.button("離職", key="res_"+str(i)):
                    st.session_state.staff_df.at[i,"status"]="離職"; save_staff(st.session_state.staff_df); st.rerun()
            else:
                if c2.button("復職", key="act_"+str(i)):
                    st.session_state.staff_df.at[i,"status"]="在職"; save_staff(st.session_state.staff_df); st.rerun()
else:
    st.sidebar.info("身分等級：申請人")

if st.sidebar.button("🚪 登出系統"):
    st.session_state.user_id = None; st.session_state.last_id = None; st.rerun()

# --- 4. HTML 排版 (碎片化拼接) ---
def render_html(row):
    amt = float(row['總金額']); fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0; act = amt - fee
    b64 = get_b64_logo(); lg = '<h3>Time Lab</h3>'
    if b64: lg = '<img src="data:image/jpeg;base64,' + b64 + '" style="height:60px;">'
    h = '<div style="font-family:sans-serif;padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += '<div style="display:flex;justify-content:space-between;align-items:center;">'
    h += '<div>' + lg + '</div><div><h3 style="margin:0;">時研國際設計股份有限公司</h3></div></div>'
    h += '<hr style="border:1px solid #000;margin:10px 0;"><h2 style="text-align:center;letter-spacing:10px;">' + str(row["類型"]) + '</h2>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += '<tr><td bgcolor="#f2f2f2" width="18%" height="35">單號</td><td>&nbsp;' + str(row["單號"]) + '</td>'
    h += '<td bgcolor="#f2f2f2" width="18%">專案負責人</td><td>&nbsp;蔡松霖</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">專案名稱</td><td>&nbsp;' + str(row["專案名稱"]) + '</td>'
    h += '<td bgcolor="#f2f
