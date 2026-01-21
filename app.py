import streamlit as st
import pandas as pd
import datetime
import os
import base64

# --- 1. 系統環境與資料庫設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff.csv") # 同事清單儲存檔

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

# --- 同事清單管理 (新增同事功能) ---
def load_staff():
    default_staff = ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita"]
    if os.path.exists(S_FILE):
        try:
            return pd.read_csv(S_FILE)["name"].tolist()
        except: pass
    return default_staff

def save_staff(staff_list):
    pd.DataFrame({"name": staff_list}).to_csv(S_FILE, index=False)

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

# 初始化身分清單與資料
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff' not in st.session_state: st.session_state.staff = load_staff()
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入身分選取畫面 ---
if 'user_id' not in st.session_state:
    st.header("🏢 時研國際 - 內部管理系統")
    st.markdown("### 🔑 請選擇您的身分進入系統")
    sel_u = st.selectbox("我的身分：", ["--- 請選擇 ---"] + st.session_state.staff)
    if st.button("確認進入"):
        if sel_u != "--- 請選擇 ---":
            st.session_state.user_id = sel_u
            st.rerun()
    st.stop()

curr_name = st.session_state.user_id
is_admin = (curr_name == "Anita") # 定義管理員

# --- 3. 側邊欄：顯示目前身分與管理功能 ---
st.sidebar.markdown(f"### 👤 目前登入：{curr_name}")
if is_admin:
    st.sidebar.success("系統權限：管理員")
    with st.sidebar.expander("⚙️ 管理員工具：新增同事"):
        new_person = st.text_input("輸入新同事姓名")
        if st.button("➕ 確認新增"):
            if new_person and new_person not in st.session_state.staff:
                st.session_state.staff.append(new_person)
                save_staff(st.session_state.staff)
                st.toast(f"✅ 已新增 {new_person}")
                st.rerun()
else:
    st.sidebar.info("系統權限：一般申請")

if st.sidebar.button("🚪 登出系統"):
    del st.session_state.user_id
    st.rerun()

# --- 4. HTML A4 排版函數 ---
def render_html(row):
    amt = float(row['總金額']); fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0; act = amt - fee
    b64 = get_b64_logo(); lg = '<h3>Time Lab</h3>'
    if b64: lg = '<img src="data:image/jpeg;base64,' + b64 + '" style="height:60px;">'
    h = '<div style="font-family:sans-serif;padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += '<div style="display:flex;justify-content:space-between;align-items:center;"><div>' + lg + '</div><div><h3 style="margin:0;">時研國際設計股份有限公司</h3></div></div>'
    h += '<hr style="border:1px solid #000;margin:10px 0;"><h2 style="text-align:center;letter-spacing:10px;">' + str(row["類型"]) + '</h2>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1"><tr><td bgcolor="#f2f2f2" width="18%" height="35">單號</td><td>&nbsp;' + str(row["單號"]) + '</td><td bgcolor="#f2f2f2" width="18%">專案負責人</td><td>&nbsp;蔡松霖</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">專案名稱</td><td>&nbsp;' + str(row["專案名稱"]) + '</td><td bgcolor="#f2f2f2">專案編號</td><td>&nbsp;' + str(row["專案編號"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">承辦人</td><td colspan="3">&nbsp;' + str(row["申請人"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">廠商</td><td>&nbsp;' + str(row["請款廠商"]) + '</td><td bgcolor="#f2f2f2">付款方式</td><td>&nbsp;' + str(row["付款方式"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">幣別</td><td>&nbsp;' + str(row["幣別"]) + '</td><td bgcolor="#f2f2f2">匯款帳戶</td><td>&nbsp;' + str(row["匯款帳戶"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="80" valign="top">說明</td><td colspan="3" valign="top" style="padding:10px;">' + str(row["請款說明"]) + '</td></tr>'
    h += '<tr><td colspan="3" align="right">請款金額&nbsp;</td><td align="right">' + f"{amt:,.0f}" + '&nbsp;</td></tr><tr><td colspan="3" align="right">提列手續費&nbsp;</td><td align="right">' + str(fee) + '&nbsp;</td></tr>'
    h += '<tr style="font-weight:bold;"><td colspan="3" align="right" height="40" bgcolor="#eee">實際請款&nbsp;</td><td align="right" bgcolor="#eee">' + f"{act:,.0f}" + '&nbsp;</td></tr></table>'
    if str(row['帳戶影像Base64']) != "": h += '<div style="margin-top:10px;border:1px dashed #ccc;padding:10px;"><b>存摺影本：</b><br><img src="data:image/jpeg;base64,' + str(row["帳戶影像Base64"]) + '" style="max-width:100%;max-height:220px;"></div>'
    h += '<div style="display:flex;flex-direction:column;gap:15px;margin-top:40px;font-size:11px;"><div style="display:flex;justify-content:space-between;"><span>承辦人簽核：' + str(row["申請人"]) 
    if str(row["提交時間"]) != "": h += ' (' + str(row["提交時間"]) + ')'
    h += '</span><span>專案合夥人簽核：_________</span></div><div style="display:flex;justify-content:space-between;"><span>財務執行長簽核：_________</span><span>財務簽核：_________</span></div></div></div>'
    v = ""
    if str(row['影像Base64']) != "":
        imgs = str(row['影像Base64']).split('|')
        for i, img in enumerate(imgs):
            if i % 2 == 0: v += '<div style="width:700px;margin:auto;page-break-before:always;padding:20px;">'
            if i == 0: v += '<b style="font-size:16px;">憑證：</b>
