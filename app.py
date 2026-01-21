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
            # 讀取時強制重設索引預防報錯
            return pd.read_csv(S_FILE).fillna("在職").reset_index(drop=True)
        except: pass
    d = {"name": ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita"],
         "status": ["在職", "在職", "在職", "在職", "在職"]}
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
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入識別畫面 ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    st.info("請選取您的身分以進入系統")
    # 僅顯示「在職」員工供選取
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

# --- 3. 側邊欄：身份顯示與權限管理 (修復重複 ID 報錯) ---
st.sidebar.markdown(f"### 👤 目前登入：{curr_name}")
if is_admin:
    st.sidebar.success("系統權限：管理員")
    with st.sidebar.expander("⚙️ 管理員工具"):
        new_p = st.text_input("1. 新增同事姓名")
        if st.button("➕ 確認新增"):
            if not new_p: st.sidebar.warning("請輸入姓名")
            elif new_p in st.session_state.staff_df["name"].tolist():
                st.sidebar.error("該員已重複新增")
            else:
                # 使用 ignore_index 預防編號衝突
                new_row = pd.DataFrame({"name": [new_p], "status": ["在職"]})
                st.session_state.staff_df = pd.concat([st.session_state.staff_df, new_row], ignore_index=True)
                save_staff(st.session_state.staff_df)
                st.sidebar.success("該員新增完成")
                st.rerun()
        st.divider()
        st.write("2. 人員狀態管理")
        # 迴圈時強制重設索引預防 DuplicateElementKey 報錯
        for i, r in st.session_state.staff_df.reset_index(drop=True).iterrows():
            if r["name"] == "Anita": continue
            c1, c2 = st.columns([2, 1])
            c1.write(r["name"])
            if r["status"] == "在職":
                if c2.button("離職", key=f"res_{i}"):
                    st.session_state.staff_df.at[i, "status"] = "離職"
                    save_staff(st.session_state.staff_df); st.rerun()
            else:
                if c2.button("復職", key=f"act_{i}"):
                    st.session_state.staff_df.at[i, "status"] = "在職"
                    save_staff(st.session_state.staff_df); st.rerun()
else:
    st.sidebar.info("系統權限：一般申請")

if st.sidebar.button("🚪 登出系統"):
    st.session_state.user_id = None; st.rerun()

# --- 4. HTML 排版內容 (極短行拼接) ---
def render_html(row):
    amt = float(row['總金額']); fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0; act = amt - fee
    b64 = get_b64_logo(); lg = '<h3>Time Lab</h3>'
    if b64: lg = '<img src="data:image/jpeg;base64,' + b64 + '" style="height:60px;">'
    h = '<div style="font-family:sans-serif;padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += '<div style="display:flex;justify-content:space-between;align-items:center;"><div>' + lg + '</div><div><h3 style="margin:0;">時研國際設計股份有限公司</h3></div></div>'
    h += '<hr style="border:1px solid #000;margin:10px 0;"><h2 style="text-align:center;letter-spacing:10px;">' + str(row["類型"]) + '</h2>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1"><tr><td bgcolor="#f2f2f2" width="18%" height="35">單號</td>'
    h += '<td>&nbsp;' + str(row["單號"]) + '</td>'
    h += '<td bgcolor="#f2f2f2" width="18%">專案負責人</td><td>&nbsp;蔡松霖</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">專案名稱</td><td>&nbsp;' + str(row["專案名稱"]) + '</td>'
    h += '<td bgcolor="#f2f2f2">專案編號</td><td>&nbsp;' + str(row["專案編號"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">承辦人</td><td colspan="3">&nbsp;' + str(row["申請人"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">廠商</td><td>&nbsp;' + str(row["請款廠商"]) + '</td>'
    h += '<td bgcolor="#f2f2f2">付款方式</td><td>&nbsp;' + str(row["付款方式"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">幣別</td><td>&nbsp;' + str(row["幣別"]) + '</td>'
    h += '<td bgcolor="#f2f2f2">匯款帳戶</td><td>&nbsp;' + str(row["匯款帳戶"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="80" valign="top">說明</td>'
    h += '<td colspan="3" valign="top" style="padding:10px;">' + str(row["請款說明"]) + '</td></tr>'
    h += '<tr><td colspan="3" align="right">請款金額&nbsp;</td><td align="right">' + f"{amt:,.0f}" + '&nbsp;</td></tr>'
    h += '<tr><td colspan="3" align="right">提列手續費&nbsp;</td><td align="right">' + str(fee) + '&nbsp;</td></tr>'
    h += '<tr style="font-weight:bold;"><td colspan="3" align="right" height="40" bgcolor="#eee">實際請款&nbsp;</td>'
    h += '<td align="right" bgcolor="#eee">' + f"{act:,.0f}" + '&nbsp;</td></tr></table>'
    if str(row['帳戶影像Base64']) != "":
        h += '<div style="margin-top:10px;border:1px dashed #ccc;padding:10px;"><b>存摺影本：</b><br><img src="data:image/jpeg;base64,' + str(row["帳戶影像Base64"]) + '" style="max-width:100%;max-height:220px;"></div>'
    h += '<div style="display:flex;flex-direction:column;gap:15px;margin-top:40px;font-size:11px;">'
    h += '<div style="display:flex;justify-content:space-between;"><span>承辦人簽核：' + str(row["申請人"]) 
    if str(row["提交時間"]) != "": h += ' (' + str(row["提交時間"]) + ')'
    h += '</span><span>專案合夥人簽核：_________</span></div>'
    h += '<div style="display:flex;justify-content:space-between;"><span>財務執行長簽核：_________</span><span>財務簽核：_________</span></div></div></div>'
    v = ""
    if str(row['影像Base64']) != "":
        imgs = str(row['影像Base64']).split('|')
        for i, img in enumerate(imgs):
            if i % 2 == 0: v += '<div style="width:700px;margin:auto;page-break-before:always;padding:20px;">'
            if i == 0: v += '<b style="font-size:16px;">憑證：</b><br><br>'
            v += '<div style="height:480px;border-bottom:1px solid #ccc;margin-bottom:10px;"><img src="data:image/jpeg;base64,' + img + '" style="max-width:100%;max-height:100%;"></div>'
            if i % 2 == 1 or i == len(imgs)-1: v += '</div>'
    return h + v

# --- 5. 主功能流程 ---
menu = st.sidebar.radio("導覽選單", ["1. 填寫申請單", "2. 簽核中心"])

if menu == "1. 填寫申請單":
    st.header("時研國際設計股份有限公司 請購/請款系統")
    ed_data = None
    if st.session_state.edit_id:
        r_f = st.session_state.db[st.session_state.db["單號"]==st.session_state.edit_id]
        if not r_f.empty:
            ed_data = r_f.iloc[0]; st.warning("📝 修改單號：" + str(st.session_state.edit_id))

    current_staff = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]["name"].tolist()

    with st.form("apply_form"):
        c1, c2 = st.columns(2)
        with c1:
            app = st.text_input("承辦人 *", value=curr_name if ed_data is None else ed_data["申請人"]) 
            pn = st.text_input("專案名稱 *", value=ed_data["專案名稱"] if ed_data is not None else "")
            exe = st.selectbox("專案執行人 *", current_staff, index=current_staff.index(ed_data["專案執行人"]) if (ed_data is not None and ed_data["專案執行人"] in current_staff) else 0)
        with c2:
            pi = st.text_input("專案編號 *", value=ed_data["專案編號"] if ed_data is not None else "")
            amt = st.number_input("總金額 *", min_value=0, value=int(ed_data["總金額"]) if ed_data is not None else 0)
            tp = st.selectbox("類型 *", ["請款單", "採購單"])
        pay = st.radio("付款方式 *", ["零用金", "現金", "匯款(扣30
