import streamlit as st
import pandas as pd
import datetime
import os
import base64

# --- 1. 系統環境設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v7.csv") 

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
            return df.reset_index(drop=True)
        except: pass
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
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入識別 (密碼預設 0000) ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    sel_u = st.selectbox("我的身分：", u_list)
    if sel_u != "--- 請選擇 ---":
        input_pwd = st.text_input("輸入密碼 (預設 0000)：", type="password")
        if st.button("確認進入"):
            correct_pwd = st.session_state.staff_df[st.session_state.staff_df["name"] == sel_u]["password"].values[0]
            if input_pwd == str(correct_pwd):
                st.session_state.user_id = sel_u
                st.rerun()
            else: st.error("❌ 密碼錯誤")
    st.stop()

curr_name = st.session_state.user_id
is_admin = ("Anita" in curr_name)

# --- 3. HTML 簽核渲染 ---
def render_html(row):
    amt = float(row['總金額']); fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0; act = amt - fee
    h = '<div style="font-family:sans-serif;padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += '<div style="display:flex;justify-content:space-between;align-items:center;"><div><h3>Time Lab</h3></div><div><h4 style="margin:0;">時研國際設計股份有限公司</h4></div></div>'
    h += '<hr style="border:1px solid #000;margin:10px 0;"><h2 style="text-align:center;letter-spacing:10px;">' + str(row["類型"]) + '</h2>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += '<tr><td bgcolor="#f2f2f2" width="18%" height="35">單號</td><td>&nbsp;' + str(row["單號"]) + '</td><td bgcolor="#f2f2f2" width="18%">專案負責人</td><td>&nbsp;蔡松霖</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">專案名稱</td><td>&nbsp;' + str(row["專案名稱"]) + '</td><td bgcolor="#f2f2f2">專案編號</td><td>&nbsp;' + str(row["專案編號"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">承辦人</td><td colspan="3">&nbsp;' + str(row["申請人"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">付款方式</td><td>&nbsp;' + str(row["付款方式"]) + '</td><td bgcolor="#f2f2f2">總金額</td><td align="right">' + f"{amt:,.0f}" + '&nbsp;</td></tr>'
    h += '<tr style="font-weight:bold;background:#eee;"><td colspan="3" align="right" height="35">實際請款 (扣除手續費)&nbsp;</td><td align="right">' + f"{act:,.0f}" + '&nbsp;</td></tr></table>'
    h += '<div style="margin-top:40px;display:grid;grid-template-columns:1fr 1fr;gap:20px;font-size:12px;">'
    h += '<div><b>承辦人簽核：</b>' + str(row["申請人"]) + '</div><div><b>專案合夥人簽核：</b>____________________</div>'
    h += '<div><b>財務執行長簽核：</b>____________________</div><div><b>財務簽核：</b>____________________</div></div>'
    return h + '</div>'

# --- 4. 主流程 ---
menu = st.sidebar.radio("導覽", ["1. 填寫申請單", "2. 簽核中心"])

if menu == "1. 填寫申請單":
    st.header("時研國際設計 - 請購/請款系統")
    s_list = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]["name"].tolist()
    
    # 填寫區
    with st.form("my_form"):
        c1, c2 = st.columns(2)
        with c1:
            pn = st.text_input("專案名稱 *")
            exe = st.selectbox("專案執行人 *", s_list, index=s_list.index(curr_name) if curr_name in s_list else 0)
        with c2:
            pi = st.text_input("專案編號 *")
            amt = st.number_input("總金額 *", min_value=0)
        tp = st.selectbox("類型 *", ["請款單", "採購單"])
        pay = st.radio("付款方式 *", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], horizontal=True)
        desc = st.text_area("內容說明 *")
        
        # 使用者要求的按鈕：儲存草稿
        if st.form_submit_button("💾 儲存草稿"):
            if not (pn and pi and amt > 0 and desc): st.error("❌ 必填欄位未填寫")
            else:
                tid = datetime.date.today().strftime('%Y%m%d') + "-" + f"{len(st.session_state.db)+1:02d}"
                nr = {"單號":tid,"日期":str(datetime.date.today()),"類型":tp,"申請人":curr_name,"專案執行人":exe,"專案名稱":pn,"專案編號":pi,"請款說明":desc,"總金額":amt,"幣別":"TWD","付款方式":pay,"請款廠商":"","匯款帳戶":"","帳戶影像Base64":"","狀態":"草稿","影像Base64":"","提交時間":"","申請人信箱":curr_name}
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nr])], ignore_index=True)
                save_data(st.session_state.db); st.session_state.last_id = tid; st.rerun()

    # 儲存後的動作區域
    if st.session_state.last_id:
        st.success(f"✅ 草稿已存檔！單號：{st.session_state.last_id}")
        r_now = st.session_state.db[st.session_state.db["單號"]==st.session_state.last_id].iloc[0]
        ax, ay, az = st.columns(3)
        if ax.button("🚀 提交送審"):
            idx = st.session_state.db[st.session_state.db["單號"]==st.session_state.last_id].index[0]
            st.session_state.db.at[idx, "狀態"] = "待簽核"
            save_data(st.session_state.db); st.success("已成功提交！"); st.session_state.last_id = None; st.rerun()
        if ay.button("🔍 線上預覽"): st.session_state.view_id = st.session_state.last_id
        if az.button("🖨️ 線上列印"):
            js = "var w=window.open();w.document.write('" + clean_for_js(render_html(r_now)) + "');w.print();w.close();"
            st.components.v1.html(f'<script>{js}</script>', height=0)

    # 預覽視窗
    if st.session_state.view_id:
        st.markdown(render_html(st.session_state.db[st.session_state.db["單號"]==st.session_state.view_id].iloc[0]), unsafe_allow_html=True)
        if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()

    # 清單區
    st.divider()
    st.subheader("📋 我的申請進度")
    disp = st.session_state.db if is_admin else st.session_state.db[st.session_state.db["申請人"]==curr_name]
    for i, r in disp.iloc[::-1].iterrows():
        rid = r['單號']; s_txt = "未送審" if r['狀態']=="草稿" else r['狀態']
        c = st.columns([3, 1, 1, 1, 1])
        c[0].write(f"{rid} - {r['專案名稱']} (${r['總金額']:,.0f})")
        c[1].write(f"狀態：{s_txt}")
        # 清單按鈕：修改、線上預覽、線上列印
        if c[2].button("修改", key=f"e_{rid}", disabled=(r['狀態']!="草稿")): pass
        if c[3].button("線上預覽", key=f"v_{rid}"): st.session_state.view_id = rid; st.rerun()
        if c[4].button("線上列印", key=f"p_{rid}"):
            js = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
            st.components.v1.html(f'<script>{js}</script>', height=0)

elif menu == "2. 簽核中心":
    st.header("⚖️ 簽核中心")
    # ... (主管簽核邏輯維持不變) ...
