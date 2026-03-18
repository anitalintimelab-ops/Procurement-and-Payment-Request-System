import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  
import json

# --- 系統鎖定與介面設定 ---
st.session_state['sys_choice'] = "採購單系統"
st.set_page_config(page_title="時研-採購單系統", layout="wide", page_icon="🏢")

st.markdown("""
<style>
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
.stApp { overflow-x: hidden; }
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    table { word-wrap: break-word !important; font-size: 13px !important; }
    th, td { padding: 5px !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 路徑定位 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) 
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- 基礎工具 ---
def get_taiwan_time(): 
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return 0
    try: return int(float(str(val).replace(",", "").replace("$", "").replace(" ", "")))
    except: return 0

def clean_name(val): 
    return str(val).strip().split(" ")[0] if pd.notna(val) and str(val).strip() != "" else ""

def get_online_users(curr_user):
    try:
        now = time.time()
        df = pd.read_csv(O_FILE) if os.path.exists(O_FILE) else pd.DataFrame(columns=["user", "time"])
        df = df[df["user"] != curr_user]
        df = pd.concat([df, pd.DataFrame([{"user": curr_user, "time": now}])], ignore_index=True)
        df = df[now - pd.to_numeric(df["time"], errors='coerce').fillna(0) <= 300]
        df.to_csv(O_FILE, index=False); return len(df["user"].unique())
    except: return 1

def get_line_credentials():
    if os.path.exists(L_FILE):
        try:
            with open(L_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                return lines[0].strip() if len(lines) > 0 else "", lines[1].strip() if len(lines) > 1 else ""
        except: pass
    return "", ""

def save_line_credentials(token, user_id):
    try:
        with open(L_FILE, "w", encoding="utf-8") as f: f.write(f"{token.strip()}\n{user_id.strip()}")
    except: pass

def send_line_message(msg):
    token, _ = get_line_credentials()
    if token:
        try: requests.post("https://api.line.me/v2/bot/message/broadcast", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, json={"messages": [{"type": "text", "text": msg}]}, timeout=5)
        except: pass

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "代申請人", "專案負責人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱", "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", "刪除原因", "駁回原因", "匯款狀態", "匯款日期", "支付條件", "支付期數", "請款狀態", "已請款金額", "尚未請款金額", "最後採購金額"]
    if not os.path.exists(D_FILE): return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(D_FILE, encoding='utf-8-sig', dtype=str).fillna("")
        for c in ["總金額", "已請款金額", "尚未請款金額"]:
            if c in df.columns: df[c] = df[c].apply(clean_amount)
        return df
    except: return pd.DataFrame(columns=cols)

def save_data(df):
    try: df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except: st.error("⚠️ 檔案鎖定中！請關閉電腦上的 database.csv 後重試。"); st.stop()

def load_staff():
    if not os.path.exists(S_FILE): return pd.DataFrame({"name": DEFAULT_STAFF, "status":["在職"]*5, "password":["0000"]*5})
    return pd.read_csv(S_FILE, encoding='utf-8-sig', dtype=str).fillna("")

def save_staff(df): df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def render_html(row):
    amt = clean_amount(row['總金額'])
    sub_time = str(row.get("提交時間", "")) or get_taiwan_time()
    display_app = f"{row['申請人']} ({row.get('代申請人', '')} 代)" if row.get("代申請人") else row['申請人']
    logo_b64 = "" # 簡化
    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;font-family:sans-serif;">'
    h += f'<div style="text-align:center;"><h2>時研國際設計 - 採購申請單</h2></div>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += f'<tr><td bgcolor="#eee" width="25%">單號</td><td>{row["單號"]}</td><td bgcolor="#eee">執行長</td><td>{row["專案負責人"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">專案</td><td>{row["專案名稱"]}</td><td bgcolor="#eee">編號</td><td>{row["專案編號"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">申請人</td><td colspan="3">{display_app}</td></tr>'
    h += f'<tr><td bgcolor="#eee">說明</td><td colspan="3">{row["請款說明"]}</td></tr>'
    h += f'<tr><td colspan="3" align="right"><b>金額</b></td><td align="right"><b>{row.get("幣別","TWD")} {amt:,}</b></td></tr></table>'
    h += f'<p style="font-size:11px;margin-top:10px;">提交：{sub_time} | 初審：{row.get("初審人","")} | 複審：{row.get("複審人","")}</p></div>'
    return h

def clean_for_js(h_str): return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# --- Session ---
if st.session_state.get('user_id') is None: st.switch_page("app.py")
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
for k in ['edit_id', 'last_id', 'view_id']: 
    if k not in st.session_state: st.session_state[k] = None

curr_name, is_admin = st.session_state.user_id, (st.session_state.user_id in ADMINS)

# --- 側邊欄 (與各系統一致) ---
st.sidebar.markdown(f"**📌 目前系統：** `採購單系統`")
st.sidebar.divider()
avatar_b64 = ""
try: avatar_b64 = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0].get("avatar", "")
except: pass

if avatar_b64: st.sidebar.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:15px;"><img src="data:image/jpeg;base64,{avatar_b64}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;border:3px solid #eee;"><span style="font-size:22px;font-weight:bold;color:#333;">{curr_name}</span></div>', unsafe_allow_html=True)
else: st.sidebar.markdown(f"### 👤 {curr_name}")

st.sidebar.info(f"🟢 目前在線人數：**{get_online_users(curr_name)}** 人")

with st.sidebar.expander("📸 修改大頭貼"):
    new_avatar = st.file_uploader("上傳圖片", type=["jpg", "png"])
    if st.button("更新大頭貼") and new_avatar:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "avatar"] = base64.b64encode(new_avatar.getvalue()).decode()
        save_staff(s_df); st.session_state.staff_df = s_df; st.rerun()

with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password")
    if st.button("更新密碼") and len(new_pw) >= 4:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "password"] = str(new_pw); save_staff(s_df); st.success("成功")

if is_admin:
    st.sidebar.success("管理員模式")
    with st.sidebar.expander("🔑 所有人員密碼清單"):
        st.dataframe(st.session_state.staff_df[["name", "password"]], hide_index=True)
    with st.sidebar.expander("⚙️ 人員設定"):
        edited_staff = st.data_editor(st.session_state.staff_df[["name", "status", "line_uid"]], column_config={"status": st.column_config.SelectboxColumn("狀態", options=["在職", "離職"])}, hide_index=True)
        if st.button("💾 儲存人員設定"): save_staff(edited_staff); st.rerun()

if st.sidebar.button("登出系統"): st.session_state.user_id = None; st.switch_page("app.py")

menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽", "5. 請款狀態/系統設定"]
menu = st.sidebar.radio("導覽", menu_options, key="menu_radio")

# ================= 頁面 1: 填寫申請單 =================
if menu == "1. 填寫申請單":
    st.title("時研國際設計股份有限公司")
    st.subheader("📝 填寫採購申請單")
    db = load_data(); staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
    
    dv = {"app": curr_name, "pn": "", "pi": "", "exe": staffs[0], "amt": 0, "desc": "", "ib64": "", "cur": "TWD"}
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id].iloc[0]
        dv.update({"app": r["申請人"], "pn": r["專案名稱"], "pi": r["專案編號"], "exe": r["專案負責人"], "amt": r["總金額"], "desc": r["請款說明"], "ib64": r["影像Base64"], "cur": r.get("幣別","TWD")})

    with st.form("po_form"):
        c1, c2, c3 = st.columns(3)
        app_val = c1.selectbox("申請人", staffs, index=staffs.index(dv["app"]) if dv["app"] in staffs else 0) if curr_name == "Anita" else curr_name
        if curr_name != "Anita": c1.text_input("申請人", value=app_val, disabled=True)
        pn = c2.text_input("專案名稱", value=dv["pn"])
        pi = c3.text_input("專案編號", value=dv["pi"])
        cx1, cx2, cx3 = st.columns(3)
        exe = cx1.selectbox("負責執行長", staffs, index=staffs.index(dv["exe"]) if dv["exe"] in staffs else 0)
        amt = cx2.number_input("預計採購金額", value=int(dv["amt"]), min_value=0)
        curr = cx3.selectbox("幣別", ["TWD", "USD", "EUR"], index=0)
        desc = st.text_area("說明", value=dv["desc"])
        f_ims = st.file_uploader("上傳憑證/圖片 (僅限圖檔)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        
        if st.form_submit_button("💾 儲存"):
            if pn and amt > 0:
                b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else dv["ib64"]
                f_db = load_data()
                if st.session_state.edit_id:
                    idx = f_db[f_db["單號"]==st.session_state.edit_id].index[0]
                    f_db.loc[idx, ["申請人", "專案名稱", "專案編號", "專案負責人", "總金額", "請款說明", "影像Base64", "幣別"]] = [app_val, pn, pi, exe, amt, desc, b_ims, curr]
                    st.session_state.edit_id = None
                else:
                    tid = f"{datetime.date.today().strftime('%Y%m%d')}-{len(f_db[f_db['單號'].str.startswith(datetime.date.today().strftime('%Y%m%d'))])+1:02d}"
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"採購單", "申請人":app_val, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":desc, "總金額":amt, "幣別":curr, "狀態":"已儲存", "影像Base64":b_ims}
                    f_db = pd.concat([f_db, pd.DataFrame([nr])], ignore_index=True); st.session_state.last_id = tid
                save_data(f_db); st.success("儲存成功！"); st.rerun()

    if st.session_state.last_id:
        c1, c2, c3 = st.columns(3)
        if c1.button("🚀 提交審核"):
            f_db = load_data(); f_db.loc[f_db["單號"]==st.session_state.last_id, ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]
            save_data(f_db); send_line_message(f"🔔 採購單 {st.session_state.last_id} 待簽核"); st.session_state.last_id = None; st.rerun()
        if c2.button("🔍 預覽"): st.session_state.view_id = st.session_state.last_id; st.rerun()
        if c3.button("🆕 下一筆"): st.session_state.last_id = None; st.rerun()

    st.divider(); st.subheader("📋 申請追蹤清單")
    # --- 恢復與請款單完全一致的列寬比例 ---
    f_db = load_data(); my_db = f_db[f_db["類型"]=="採購單"]
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    
    cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
    for c, h in zip(cols, ["申請單號", "專案名稱", "負責執行長", "申請人", "金額", "狀態", "操作"]): c.write(f"**{h}**")
    for i, r in my_db.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"])
        c[4].write(f"${clean_amount(r['總金額']):,}"); c[5].write(r["狀態"])
        with c[6]:
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("預覽", key=f"v_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
            if b2.button("列印", key=f"p_{i}"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write('{clean_for_js(render_html(r))}');w.print();w.close();</script>", height=0)
            if b3.button("修改", key=f"e_{i}"): st.session_state.edit_id = r["單號"]; st.rerun()
            if b4.button("刪除", key=f"d_{i}"):
                f_db = load_data(); f_db.at[f_db[f_db["單號"]==r["單號"]].index[0], "狀態"] = "已刪除"; save_data(f_db); st.rerun()

# ================= 頁面 2 & 3: 簽核 (簡化保留) =================
elif menu in ["2. 專案執行長簽核", "3. 財務長簽核"]:
    st.subheader(menu)
    f_db = load_data(); my_db = f_db[(f_db["類型"]=="採購單") & (f_db["狀態"]=="待簽核")]
    if my_db.empty: st.info("無待審單據")
    else: st.dataframe(my_db[["單號", "專案名稱", "總金額", "申請人"]])

# ================= 頁面 5: 系統設定 (與各系統同步) =================
elif menu == "5. 請款狀態/系統設定":
    render_header()
    st.error("⚠️ **雲端暫存機制提醒：** 資料請務必備份！")
    with st.expander("💾 1. 資料庫管理", expanded=True):
        if os.path.exists(D_FILE):
            with open(D_FILE, "rb") as f: st.download_button("⬇️ 下載備份", f, file_name="database.csv")
        up = st.file_uploader("⬆️ 還原備份", type=["csv"])
        if up and st.button("確認還原"):
            with open(D_FILE, "wb") as f: f.write(up.getbuffer())
            st.success("成功！"); st.rerun()

    with st.expander("🔔 2. LINE 通知設定"):
        ct, cu = get_line_credentials()
        nt = st.text_input("Token", value=ct, type="password")
        nu = st.text_input("行政 ID", value=cu)
        if st.button("儲存 LINE 設定"): save_line_credentials(nt, nu); st.success("儲存成功")

    st.divider(); st.subheader("💰 財務匯款註記 (僅管理員)")
    f_db = load_data(); df_pay = f_db[f_db["類型"]=="採購單"].copy()
    if not df_pay.empty:
        ed = st.data_editor(df_pay[["單號", "專案名稱", "總金額", "匯款狀態", "匯款日期"]], hide_index=True)
        if st.button("💾 儲存匯款資訊"):
            for _, row in ed.iterrows():
                f_db.loc[f_db["單號"]==row["單號"], ["匯款狀態", "匯款日期"]] = [row["匯款狀態"], str(row["匯款日期"])]
            save_data(f_db); st.success("已更新"); st.rerun()

# ================= 全域預覽 =================
if st.session_state.view_id:
    st.divider(); r = load_data(); r = r[r["單號"]==st.session_state.view_id].iloc[0]
    if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
    st.markdown(render_html(r), unsafe_allow_html=True)
    if r.get("影像Base64"):
        for f_b64 in r["影像Base64"].split('|'):
            try: st.image(base64.b64decode(f_b64))
            except: st.error("圖片損壞")
