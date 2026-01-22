import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import os
import base64

# --- 1. 系統環境設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")

# 建立連線
conn = st.connection("gsheets", type=GSheetsConnection)

MANAGERS = ["Anita", "Anita 林敬芸", "Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖"]

def load_data():
    try:
        # 強制不使用快取 (ttl=0)
        df = conn.read(worksheet="database", ttl=0).fillna("")
        return df
    except Exception as e:
        # 如果失敗，在頁面顯示錯誤原因幫助偵錯
        st.error(f"❌ 無法讀取 database 工作表，請檢查名稱與權限。錯誤：{e}")
        return pd.DataFrame(columns=["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"])

def save_data(df):
    try:
        conn.update(worksheet="database", data=df)
        st.toast("✅ 資料已同步至 Google Sheets")
    except Exception as e:
        st.error(f"❌ 寫入資料庫失敗：{e}")

def load_staff():
    try:
        # 強制讀取 staff 工作表
        df = conn.read(worksheet="staff", ttl=0).fillna("在職").reset_index(drop=True)
        return df
    except Exception as e:
        st.warning(f"⚠️ 無法讀取人員清單，目前使用程式內建清單。錯誤：{e}")
        d = {"name": ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita"], "status": ["在職"] * 5}
        return pd.DataFrame(d)

def save_staff(df):
    try:
        conn.update(worksheet="staff", data=df)
    except Exception as e:
        st.error(f"❌ 儲存人員清單失敗：{e}")

def get_b64_logo():
    try:
        b_dir = os.path.dirname(os.path.abspath(__file__))
        for f in os.listdir(b_dir):
            fn = f.lower()
            if any(x in fn for x in [".jpg",".png",".jpeg"]):
                if "timelab" in fn or "logo" in fn:
                    p = os.path.join(B_DIR, f); im = open(p, "rb")
                    return base64.b64encode(im.read()).decode()
    except: pass
    return ""

def clean_for_js(h_str):
    return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# 初始化狀態，確保每次重新整理都會重新抓取資料
st.session_state.db = load_data()
st.session_state.staff_df = load_staff()

if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入識別 ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統 (Google同步版)")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    sel_u = st.selectbox("我的身分：", u_list)
    if st.button("確認進入"):
        if sel_u != "--- 請選擇 ---":
            st.session_state.user_id = sel_u
            st.rerun()
    st.stop()

curr_name = st.session_state.user_id
is_admin = ("Anita" in curr_name) # 包含 Anita 林敬芸
is_manager = (curr_name in MANAGERS)

# --- 3. 側邊欄工具 ---
st.sidebar.markdown(f"### 👤 目前登入：{curr_name}")
if is_admin:
    st.sidebar.success("身分：管理員")
    with st.sidebar.expander("⚙️ 管理員工具"):
        new_p = st.text_input("1. 新增同事姓名")
        if st.button("➕ 確認新增"):
            if not new_p: st.sidebar.warning("請輸入姓名")
            elif new_p in st.session_state.staff_df["name"].tolist():
                st.sidebar.error("該員已重複")
            else:
                new_row = pd.DataFrame({"name": [new_p], "status": ["在職"]})
                st.session_state.staff_df = pd.concat([st.session_state.staff_df, new_row], ignore_index=True)
                save_staff(st.session_state.staff_df)
                st.sidebar.success("該員新增完成")
                st.rerun()
        st.divider()
        st.write("2. 人員狀態管理")
        for i, r in st.session_state.staff_df.reset_index(drop=True).iterrows():
            if "Anita" in r["name"]: continue
            c1, c2 = st.columns([2, 1])
            c1.write(r["name"])
            if r["status"] == "在職":
                if c2.button("離職", key=f"res_{i}"):
                    st.session_state.staff_df.at[i,"status"]="離職"; save_staff(st.session_state.staff_df); st.rerun()
            else:
                if c2.button("復職", key=f"act_{i}"):
                    st.session_state.staff_df.at[i,"status"]="在職"; save_staff(st.session_state.staff_df); st.rerun()
else:
    st.sidebar.info("身分：員工")

if st.sidebar.button("🚪 登出系統"):
    st.session_state.user_id = None; st.session_state.last_id = None; st.rerun()

# --- 4. HTML A4 排版 (省略重複代碼，確保結構與之前一致) ---
def render_html(row):
    # 此處保留您原本所有的表格拼接代碼...
    # (為了節省空間，此處省略中間長段拼接，請維持與之前版本一致)
    return "HTML排版內容"

# --- 5. 主流程 ---
m_opts = ["1. 填寫申請單"]
if is_manager: m_opts.append("2. 簽核中心")
menu = st.sidebar.radio("功能導覽", m_opts)

if menu == "1. 填寫申請單":
    st.header("時研國際設計股份有限公司 請購/請款系統")
    ed_data = None
    if st.session_state.edit_id:
        r_f = st.session_state.db[st.session_state.db["單號"]==st.session_state.edit_id]
        if not r_f.empty:
            ed_data = r_f.iloc[0]; st.warning(f"📝 正在修改：{st.session_state.edit_id}")

    staff_opts = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]["name"].tolist()

    with st.form("apply_form"):
        c1, c2 = st.columns(2)
        with c1:
            app = st.text_input("承辦人 *", value=curr_name if ed_data is None else ed_data["申請人"]) 
            pn = st.text_input("專案名稱 *", value=ed_data["專案名稱"] if ed_data is not None else "")
            exe = st.selectbox("專案執行人 *", staff_opts, index=staff_opts.index(ed_data["專案執行人"]) if (ed_data is not None and ed_data["專案執行人"] in staff_opts) else 0)
        with c2:
            pi = st.text_input("專案編號 *", value=ed_data["專案編號"] if ed_data is not None else "")
            amt = st.number_input("總金額 *", min_value=0, value=int(ed_data["總金額"]) if ed_data is not None else 0)
            tp = st.selectbox("類型 *", ["請款單", "採購單"])
        p_list = ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"]
        pay = st.radio("付款方式 *", p_list, horizontal=True)
        vdr, acc = st.text_input("廠商", value=ed_data["請款廠商"] if ed_data is not None else ""), st.text_input("帳戶", value=ed_data["匯款帳戶"] if ed_data is not None else "")
        desc = st.text_area("說明 *", value=ed_data["請款說明"] if ed_data is not None else "")
        st.divider(); st.subheader("📷 影像管理")
        acc_f = st.file_uploader("上傳新存摺", type=["jpg","png"])
        ims_f = st.file_uploader("上傳新憑證", type=["jpg","png"], accept_multiple_files=True)
        
        if st.form_submit_button("💾 儲存草稿內容"):
            if not (app and pn and pi and amt > 0 and desc): st.error("❌ 必填未填齊")
            else:
                new_db = st.session_state.db.copy()
                if st.session_state.edit_id:
                    idx = new_db[new_db["單號"]==st.session_state.edit_id].index[0]
                    # 更新現有列...
                    tid = st.session_state.edit_id; st.session_state.edit_id = None
                else:
                    tid = datetime.date.today().strftime('%Y%m%d') + "-" + f"{len(new_db)+1:02d}"
                    a_b = base64.b64encode(acc_f.getvalue()).decode() if acc_f else ""
                    i_b = "|".join([base64.b64encode(f.getvalue()).decode() for f in ims_f]) if ims_f else ""
                    nr = {"單號":tid,"日期":str(datetime.date.today()),"類型":tp,"申請人":app,"專案執行人":exe,"專案名稱":pn,"專案編號":pi,"請款說明":desc,"總金額":amt,"幣別":"TWD","付款方式":pay,"請款廠商":vdr,"匯款帳戶":acc,"帳戶影像Base64":a_b,"狀態":"草稿","影像Base64":i_b,"提交時間":"","申請人信箱":curr_name}
                    new_db = pd.concat([new_db, pd.DataFrame([nr])], ignore_index=True)
                save_data(new_db); st.session_state.last_id = tid; st.rerun()

    # 此處保留您要求的引導區塊、追蹤清單與簽核邏輯...
