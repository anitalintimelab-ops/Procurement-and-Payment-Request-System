import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  

# --- 強制系統身分鎖定 ---
st.session_state['sys_choice'] = "採購單系統"

# --- 1. 系統設定 ---
st.set_page_config(page_title="時研-採購單系統", layout="wide", page_icon="🏢")

# [手機版 RWD 響應式優化 CSS & 隱藏左側 app 選單]
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

# --- 絕對路徑定位 ---
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
def get_taiwan_time(): return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return 0
    try: return int(float(str(val).replace(",", "").replace("$", "").replace("，", "").replace(" ", "")))
    except: return 0

def clean_name(val): return "" if pd.isna(val) or val is None or str(val).strip() == "" else str(val).strip().split(" ")[0]

def get_online_users(curr_user):
    try:
        now = time.time()
        df = pd.read_csv(O_FILE) if os.path.exists(O_FILE) else pd.DataFrame(columns=["user", "time"])
        if "user" not in df.columns: df = pd.DataFrame(columns=["user", "time"])
        df = df[df["user"] != curr_user]
        df = pd.concat([df, pd.DataFrame([{"user": curr_user, "time": now}])], ignore_index=True)
        df["time"] = pd.to_numeric(df["time"], errors='coerce').fillna(now)
        df = df[now - df["time"] <= 300]
        df.to_csv(O_FILE, index=False)
        return len(df["user"].unique())
    except: return 1

def get_line_credentials():
    try:
        with open(L_FILE, "r", encoding="utf-8") as f: lines = f.read().splitlines(); return lines[0].strip(), lines[1].strip()
    except: return "", ""

def save_line_credentials(token, user_id):
    try:
        with open(L_FILE, "w", encoding="utf-8") as f: f.write(f"{token.strip()}\n{user_id.strip()}")
    except: pass

def send_line_message(msg):
    token, _ = get_line_credentials()
    if token:
        try: requests.post("https://api.line.me/v2/bot/message/broadcast", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, json={"messages": [{"type": "text", "text": msg}]}, timeout=5)
        except: pass

def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try: return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except: continue
    return pd.DataFrame()

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "代申請人", "專案負責人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱", "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", "刪除原因", "駁回原因", "匯款狀態", "匯款日期", "支付條件", "支付期數", "請款狀態", "已請款金額", "尚未請款金額", "最後採購金額"]
    df = read_csv_robust(D_FILE)
    if df is None or df.empty: return pd.DataFrame(columns=cols)
    if "專案執行人" in df.columns: df = df.rename(columns={"專案執行人": "專案負責人"})
    for c in cols:
        if c not in df.columns: df[c] = ""
    for col in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]: df[col] = df[col].apply(clean_amount)
    df["專案負責人"] = df["專案負責人"].astype(str).apply(clean_name)
    df["申請人"] = df["申請人"].astype(str).apply(clean_name)
    df["代申請人"] = df["代申請人"].astype(str).apply(clean_name)
    df["狀態"] = df["狀態"].astype(str).str.strip()
    return df[cols]

def save_data(df):
    try:
        for col in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]: df[col] = df[col].apply(clean_amount)
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError: st.error("⚠️ 無法寫入檔案！請關閉 Excel。"); st.stop()

def load_staff():
    df = read_csv_robust(S_FILE)
    if df is None or df.empty:
        df = pd.DataFrame({"name": DEFAULT_STAFF, "status": ["在職"]*5, "password": ["0000"]*5, "avatar": [""]*5, "line_uid": [""]*5})
        df.to_csv(S_FILE, index=False, encoding='utf-8-sig')
        return df
    if "status" not in df.columns: df["status"] = "在職"
    if "avatar" not in df.columns: df["avatar"] = ""
    if "line_uid" not in df.columns: df["line_uid"] = ""
    df["name"] = df["name"].astype(str).str.strip()
    return df

def save_staff(df): df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            if any(x in f.lower() for x in ["logo", "timelab"]) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                with open(os.path.join(B_DIR, f), "rb") as img: return base64.b64encode(img.read()).decode()
    except: pass
    return ""

def render_header():
    logo_b64 = get_b64_logo()
    if logo_b64: st.markdown(f'<div style="display:flex;align-items:center;justify-content:center;gap:15px;margin-bottom:20px;"><img src="data:image/png;base64,{logo_b64}" style="height:60px;"><h2>時研國際設計股份有限公司</h2></div>', unsafe_allow_html=True)
    else: st.title("時研國際設計股份有限公司")
    st.divider()

def clean_for_js(h_str): return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")
def is_pdf(b64_str): return str(b64_str).startswith("JVBERi")

# --- 全新 PDF 預覽核心引擎 (徹底解決無法預覽與語法錯誤) ---
def display_pdf(b64_str, height=650):
    clean_b64 = str(b64_str).replace('\n', '').replace('\r', '')
    html_code = f"""
    <script>
        try {{
            var pdfData = "{clean_b64}";
            var byteCharacters = atob(pdfData);
            var byteNumbers = new Array(byteCharacters.length);
            for (var i = 0; i < byteCharacters.length; i++) {{ 
                byteNumbers[i] = byteCharacters.charCodeAt(i); 
            }}
            var byteArray = new Uint8Array(byteNumbers);
            var blob = new Blob([byteArray], {{type: "application/pdf"}});
            var url = URL.createObjectURL(blob);
            document.write('<iframe src="' + url + '" width="100%" height="{height}px" style="border:none;"></iframe>');
        }} catch (e) {{
            document.write('<p style="color:red; text-align:center;">❌ PDF 載入發生錯誤，請確認檔案格式是否正確。</p>');
        }}
    </script>
    """
    st.components.v1.html(html_code, height=height)

# --- 初始化 ---
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'user_status' not in st.session_state: st.session_state.user_status = "在職"
for key in ['edit_id', 'last_id', 'view_id']:
    if key not in st.session_state: st.session_state[key] = None
if 'form_key' not in st.session_state: st.session_state.form_key = 0 

if st.session_state.user_id is None: st.switch_page("app.py")

curr_name = st.session_state.user_id
is_active = (st.session_state.user_status == "在職")
is_admin = (curr_name in ADMINS)

# --- 左側側邊欄 ---
st.sidebar.markdown(f"**📌 目前系統：** `{st.session_state.sys_choice}`")
st.sidebar.divider()

avatar_b64 = ""
try: avatar_b64 = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0].get("avatar", "")
except: pass

if avatar_b64: st.sidebar.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:15px;"><img src="data:image/jpeg;base64,{avatar_b64}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;border:3px solid #eee;"><span style="font-size:22px;font-weight:bold;color:#333;">{curr_name}</span></div>', unsafe_allow_html=True)
else: st.sidebar.markdown(f"### 👤 {curr_name}")

st.sidebar.info(f"🟢 目前在線人數：**{get_online_users(curr_name)}** 人")
if not is_active: st.sidebar.error("⛔ 已離職")

with st.sidebar.expander("📸 修改大頭貼"):
    new_avatar = st.file_uploader("上傳您的圖片", type=["jpg", "jpeg", "png"])
    if st.button("更新大頭貼", disabled=not is_active) and new_avatar:
        staff_df = load_staff()
        staff_df.loc[staff_df["name"] == curr_name, "avatar"] = base64.b64encode(new_avatar.getvalue()).decode()
        save_staff(staff_df); st.session_state.staff_df = staff_df; st.success("已更新！"); time.sleep(0.5); st.rerun()

with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password")
    confirm_pw = st.text_input("確認新密碼", type="password")
    if st.button("更新密碼", disabled=not is_active):
        if new_pw != confirm_pw: st.error("兩次輸入不符")
        elif len(str(new_pw)) < 4: st.error("密碼過短")
        else:
            staff_df = load_staff()
            staff_df.loc[staff_df["name"] == curr_name, "password"] = str(new_pw)
            save_staff(staff_df); st.session_state.staff_df = staff_df; st.success("成功")

if is_admin:
    st.sidebar.success("管理員模式")
    with st.sidebar.expander("🔑 所有人員密碼清單"):
        st.dataframe(st.session_state.staff_df[["name", "password"]], hide_index=True)
        reset_target = st.selectbox("選擇人員", st.session_state.staff_df["name"].tolist(), key="rst_sel")
        if st.button("確認恢復預設(0000)", key="rst_btn"):
            staff_df = load_staff()
            staff_df.loc[staff_df["name"] == reset_target, "password"] = "0000"
            save_staff(staff_df); st.session_state.staff_df = staff_df; st.success("已重置")
    with st.sidebar.expander("➕ 新增人員"):
        n = st.text_input("姓名")
        if st.button("新增") and n not in st.session_state.staff_df["name"].values:
            st.session_state.staff_df = pd.concat([st.session_state.staff_df, pd.DataFrame([{"name":n, "status":"在職", "password":"0000", "avatar":"", "line_uid":""}])])
            save_staff(st.session_state.staff_df); st.success("成功"); st.rerun()
    with st.sidebar.expander("⚙️ 人員設定 (狀態 & LINE ID)"):
        edited_staff = st.data_editor(st.session_state.staff_df[["name", "status", "line_uid"]], column_config={"name": st.column_config.TextColumn("姓名", disabled=True), "status": st.column_config.SelectboxColumn("狀態", options=["在職", "離職"])}, hide_index=True)
        if st.button("💾 儲存人員設定"):
            for idx, row in edited_staff.iterrows():
                st.session_state.staff_df.loc[idx, ["status", "line_uid"]] = [row["status"], str(row["line_uid"]).strip() if pd.notna(row["line_uid"]) else ""]
            save_staff(st.session_state.staff_df); st.success("已更新！"); time.sleep(0.5); st.rerun()

if st.sidebar.button("登出"):
    st.session_state.user_id = None; st.switch_page("app.py")

# --- 導覽選單 ---
menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽及轉請款單", "5. 請款狀態/系統設定"]
menu = st.sidebar.radio("導覽", menu_options)

def get_filtered_db(): return load_data()[load_data()["類型"] == "採購單"]

def render_html(row):
    amt = clean_amount(row['總金額'])
    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;"><h2 style="text-align:center;border-bottom:2px solid #000;">時研國際設計 - 採購單</h2>'
    h += '<table style="width:100%;border-collapse:collapse;" border="1">'
    h += f'<tr><td bgcolor="#eee">單號</td><td>{row["單號"]}</td><td bgcolor="#eee">執行長</td><td>{clean_name(row["專案負責人"])}</td></tr>'
    h += f'<tr><td bgcolor="#eee">專案</td><td>{row["專案名稱"]}</td><td bgcolor="#eee">編號</td><td>{row["專案編號"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">申請人</td><td colspan="3">{row["申請人"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">說明</td><td colspan="3">{row["請款說明"]}</td></tr>'
    c_cur = str(row.get("幣別", "TWD")).replace("nan", "TWD")
    h += f'<tr><td colspan="3" align="right">預計採購金額</td><td align="right">{c_cur} {amt:,.0f}</td></tr></table>'
    if row["狀態"] == "已駁回": h += f'<p style="color:red;"><b>❌ 駁回原因：</b>{row["駁回原因"]}</p>'
    h += f'<p>提交: {row.get("提交時間","")} | 初審: {row.get("初審人","")} {row.get("初審時間","")}</p></div>'
    return h

def render_upload_popover(container, r, prefix):
    with container.popover("📎 附件"):
        st.write("**上傳新附件 (支援圖/PDF)**")
        new_f_acc = st.file_uploader("存摺", type=["png", "jpg", "jpeg", "pdf"], key=f"{prefix}_a")
        new_f_ims = st.file_uploader("憑證", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True, key=f"{prefix}_i")
        if st.button("💾 儲存", key=f"{prefix}_b"):
            fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
            if new_f_acc: fresh_db.at[idx, "帳戶影像Base64"] = base64.b64encode(new_f_acc.getvalue()).decode()
            if new_f_ims: fresh_db.at[idx, "影像Base64"] = "|".join([base64.b64encode(f.getvalue()).decode() for f in new_f_ims])
            save_data(fresh_db); st.rerun()

# --- 頁面 1: 填寫申請單 ---
if menu == "1. 填寫申請單":
    render_header()
    st.subheader("填寫申請單")
    
    try:
        db = load_data()
        staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
        if curr_name not in staffs: staffs.append(curr_name)
        
        sys_save_type = "採購單" 
        curr_options = ["TWD", "USD", "EUR", "JPY", "CNY", "HKD", "GBP", "AUD"]
        dv = {"pn":"", "exe":staffs[0], "pi":"", "amt":0, "curr":"TWD", "pay":"現金", "vdr":"", "acc":"", "desc":"", "ab64":"", "ib64":"", "app": curr_name, "pay_cond": "", "pay_inst": "", "final_amt": 0, "billed_amt": 0, "unbilled_amt": 0, "bill_stat": ""}
        
        if st.session_state.edit_id:
            r = db[db["單號"]==st.session_state.edit_id]
            if not r.empty:
                row = r.iloc[0]
                st.info(f"📝 修改中: {st.session_state.edit_id}")
                dv.update({"app": clean_name(row.get("申請人", curr_name)), "pn": str(row.get("專案名稱", "")), "exe": clean_name(row.get("專案負責人", staffs[0])), "pi": str(row.get("專案編號", "")), "amt": clean_amount(row.get("總金額", 0)), "curr": str(row.get("幣別", "TWD")), "pay": str(row.get("付款方式", "現金")), "vdr": str(row.get("請款廠商", "")), "acc": str(row.get("匯款帳戶", "")), "desc": str(row.get("請款說明", "")), "ab64": str(row.get("帳戶影像Base64", "")), "ib64": str(row.get("影像Base64", "")), "pay_cond": str(row.get("支付條件", "")), "pay_inst": str(row.get("支付期數", "")), "final_amt": clean_amount(row.get("最後採購金額", 0)), "billed_amt": clean_amount(row.get("已請款金額", 0)), "unbilled_amt": clean_amount(row.get("尚未請款金額", 0)), "bill_stat": str(row.get("請款狀態", ""))})

        with st.form("form"):
            mode_suffix = f"{st.session_state.edit_id}_{st.session_state.form_key}" if st.session_state.edit_id else f"new_{st.session_state.form_key}"
            c1, c2 = st.columns(2)
            
            if curr_name == "Anita": app_val = c1.selectbox("申請人 (可代申請)", staffs, index=staffs.index(dv["app"]) if dv["app"] in staffs else staffs.index(curr_name), key=f"app_{mode_suffix}")
            else: app_val = curr_name; c1.text_input("申請人", value=app_val, disabled=True, key=f"app_{mode_suffix}")
                
            pn = c1.text_input("專案名稱", value=dv["pn"], key=f"pn_{mode_suffix}")
            exe = c1.selectbox("負責執行長", staffs, index=staffs.index(dv["exe"]) if dv["exe"] in staffs else 0, key=f"exe_{mode_suffix}")
            pi = c2.text_input("專案編號", value=dv["pi"], key=f"pi_{mode_suffix}")
            amt = c2.number_input("預計採購金額", value=int(max(0, dv["amt"])), min_value=0, key=f"amt_{mode_suffix}")
            currency = c2.selectbox("幣別", curr_options, index=curr_options.index(dv["curr"]) if dv["curr"] in curr_options else 0, key=f"curr_{mode_suffix}")
            
            st.markdown("---")
            st.markdown("**(採購單專屬欄位 - 皆為非必填)**")
            cp1, cp2, cp3 = st.columns(3)
            pay_cond = cp1.text_input("支付條件", value=dv["pay_cond"], key=f"pc_{mode_suffix}")
            pay_inst = cp2.text_input("支付期數", value=dv["pay_inst"], key=f"pinst_{mode_suffix}")
            final_amt = cp3.number_input("最後採購金額", value=int(max(0, dv["final_amt"])), min_value=0, key=f"famt_{mode_suffix}")
            
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
                if is_pdf(dv["ab64"]): display_pdf(dv["ab64"], height=250)
                else: st.image(base64.b64decode(dv["ab64"]), width=200)
                del_acc = st.checkbox("❌ 刪除此存摺", key=f"da_{mode_suffix}")
            f_acc = st.file_uploader("上傳存摺 (支援圖片與PDF)", type=["png", "jpg", "jpeg", "pdf"], key=f"fa_{mode_suffix}")
            
            del_ims = False
            if dv["ib64"]:
                st.write("✅ 已有憑證")
                del_ims = st.checkbox("❌ 刪除所有憑證", key=f"di_{mode_suffix}")
            f_ims = st.file_uploader("上傳憑證 (支援圖片與PDF)", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True, key=f"fi_{mode_suffix}")
            
            if st.form_submit_button("💾 儲存", disabled=not is_active):
                db = load_data()
                if not (pn and pi and amt>0 and desc):
                    st.error("請確認必填欄位 (專案名稱、編號、金額、說明) 已填寫")
                else:
                    b_acc = base64.b64encode(f_acc.getvalue()).decode() if f_acc else ("" if del_acc else dv["ab64"])
                    b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else ("" if del_ims else dv["ib64"])
                    proxy_val = curr_name if app_val != curr_name else ""
                    
                    if st.session_state.edit_id:
                        idx = db[db["單號"]==st.session_state.edit_id].index[0]
                        db.loc[idx, ["申請人", "代申請人", "專案名稱", "專案負責人", "專案編號", "總金額", "請款說明", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "影像Base64", "支付條件", "支付期數", "最後採購金額", "請款狀態", "已請款金額", "尚未請款金額"]] = [app_val, proxy_val, pn, exe, pi, amt, desc, currency, pay, vdr, acc, b_acc, b_ims, pay_cond, pay_inst, final_amt, bill_stat, billed_amt, unbilled_amt]
                        st.session_state.edit_id = None
                    else:
                        today_str = datetime.date.today().strftime('%Y%m%d')
                        next_num = len(db[db["單號"].astype(str).str.startswith(today_str)]) + 1 if not db.empty else 1
                        tid = f"{today_str}-{next_num:02d}"
                        nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":sys_save_type, "申請人":app_val, "代申請人":proxy_val, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":desc, "總金額":amt, "幣別":currency, "付款方式":pay, "請款廠商":vdr, "匯款帳戶":acc, "帳戶影像Base64":b_acc, "狀態":"已儲存", "影像Base64":b_ims, "提交時間":"", "申請人信箱":curr_name, "初審人":"", "初審時間":"", "複審人":"", "複審時間":"", "刪除人":"", "刪除時間":"", "刪除原因":"", "駁回原因":"", "支付條件": pay_cond, "支付期數": pay_inst, "請款狀態": bill_stat, "已請款金額": billed_amt, "尚未請款金額": amt, "最後採購金額": final_amt}
                        db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                        st.session_state.last_id = tid
                        st.session_state.form_key += 1
                    save_data(db); st.success("成功"); st.rerun()

        if st.session_state.last_id:
            c1, c2, c3, c4, c5 = st.columns(5)
            temp_db = load_data(); curr_row = temp_db[temp_db["單號"]==st.session_state.last_id]
            can_act = False if curr_row.empty else (curr_row.iloc[0]["狀態"] in ["已儲存", "草稿", "已駁回"] and is_active)

            if c1.button("🚀 提交", disabled=not can_act):
                idx = temp_db[temp_db["單號"]==st.session_state.last_id].index[0]
                temp_db.loc[idx, ["狀態", "提交時間", "初審人", "初審時間", "複審人", "複審時間", "駁回原因"]] = ["待簽核", get_taiwan_time(), "", "", "", "", ""]
                save_data(temp_db)
                send_line_message(f"🔔【待簽核提醒】\n單號：{st.session_state.last_id}\n專案：{temp_db.at[idx, '專案名稱']}\n需執行長簽核！")
                st.success("已提交！"); st.rerun()
            if c2.button("🔍 線上預覽"): st.session_state.view_id = st.session_state.last_id; st.rerun()
            if c3.button("🖨️ 線上列印"):
                js = "var w=window.open();w.document.write('" + clean_for_js(render_html(curr_row.iloc[0])) + "');w.print();w.close();"
                st.components.v1.html(f"<script>{js}</script>", height=0)
            if c4.button("✏️ 修改", disabled=not can_act): st.session_state.edit_id = st.session_state.last_id; st.session_state.last_id = None; st.rerun()
            if c5.button("🆕 下一筆"): st.session_state.last_id = None; st.rerun()

        st.divider()
        st.subheader("📋 申請追蹤清單")
        h1, h2, hx, h3, h4, h5, h6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        h1.write("**申請單號**"); h2.write("**專案名稱**"); hx.write("**負責執行長**"); h3.write("**申請人**"); h4.write("**預計採購金額**"); h5.write("**狀態**"); h6.write("**操作**") 
        
        my_db = get_filtered_db()
        if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
        
        for i, r in my_db.iterrows():
            c1, c2, cx, c3, c4, c5, c6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
            c1.write(r["單號"]); c2.write(r["專案名稱"]); cx.write(clean_name(r["專案負責人"])); c3.write(r["申請人"]); c4.write(f"{str(r.get('幣別','TWD')).replace('nan','TWD')} ${clean_amount(r['總金額']):,.0f}")
            stt = r["狀態"]
            c5.markdown(f":{'blue' if stt in ['已儲存', '草稿'] else 'orange' if '待' in stt else 'green' if stt == '已核准' else 'red' if stt == '已駁回' else 'gray'}[**{stt}**]")
            
            with c6:
                b1, b2, b3, b4, b5, b6 = st.columns(6)
                is_own = (str(r["申請人"]).strip() == curr_name) or (str(r.get("代申請人", "")).strip() == curr_name)
                can_edit = (stt in ["已儲存", "草稿", "已駁回"]) and is_own and is_active
                
                if b1.button("提交", key=f"s{i}", disabled=not can_edit):
                    fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    fresh_db.loc[idx, ["狀態", "提交時間", "初審人", "初審時間", "複審人", "複審時間", "駁回原因"]] = ["待簽核", get_taiwan_time(), "", "", "", "", ""]
                    save_data(fresh_db); send_line_message(f"🔔【待簽核提醒】\n單號：{r['單號']}\n專案：{r['專案名稱']}\n需執行長簽核！"); st.rerun()
                if b2.button("預覽", key=f"v{i}"): st.session_state.view_id = r["單號"]; st.rerun()
                if b3.button("列印", key=f"p{i}"):
                    js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                    st.components.v1.html('<script>' + js_p + '</script>', height=0)
                if b4.button("修改", key=f"e{i}", disabled=not can_edit): st.session_state.edit_id = r["單號"]; st.rerun()
                
                if stt == "已核准" and is_active:
                    with b5.popover("📝 更新"):
                        st.write("**採購單後續更新**")
                        new_bill_stat = st.text_input("請款狀態", value=str(r.get("請款狀態", "")), key=f"m1_bs_{i}")
                        new_billed = st.number_input("已請款金額", value=int(clean_amount(r.get("已請款金額", 0))), min_value=0, key=f"m1_ba_{i}")
                        new_unbilled = st.number_input("尚未請款金額", value=int(clean_amount(r.get("尚未請款金額", 0))), min_value=0, key=f"m1_ua_{i}")
                        new_desc = st.text_area("修改說明內容", value=str(r.get("請款說明", "")), key=f"m1_desc_{i}")
                        if st.button("💾 儲存修改", key=f"m1_save_pur_{i}"):
                            fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                            fresh_db.loc[idx, ["請款狀態", "已請款金額", "尚未請款金額", "請款說明"]] = [new_bill_stat, new_billed, new_unbilled, new_desc]
                            save_data(fresh_db); st.success("已更新！"); time.sleep(0.5); st.rerun()
                else:
                    if can_edit:
                        with b5.popover("刪除"):
                            reason = st.text_input("刪除原因", key=f"d_res_{i}")
                            if st.button("確認", key=f"d{i}"):
                                if reason:
                                    fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                                    fresh_db.loc[idx, ["狀態", "刪除人", "刪除時間", "刪除原因"]] = ["已刪除", curr_name, get_taiwan_time(), reason]
                                    save_data(fresh_db); st.rerun()
                                else: st.error("請輸入原因")
                    else: b5.button("刪除", disabled=True, key=f"fake_d_{i}")
                render_upload_popover(b6, r, f"m1_up_{i}")

    except Exception as e: st.error(f"錯誤：{e}")

# --- 頁面 2: 執行長簽核 ---
elif menu == "2. 專案執行長簽核":
    render_header()
    st.subheader("🔍 專案執行長簽核")
    sys_db = get_filtered_db()
    p_df = sys_db[sys_db["狀態"].isin(["待簽核", "待初審"])] if is_admin else sys_db[(sys_db["狀態"].isin(["待簽核", "待初審"])) & (sys_db["專案負責人"] == curr_name)]
    
    st.subheader("⏳ 待簽核清單")
    if p_df.empty: st.info("目前無待簽核單據")
    else: 
        h1, h2, hx, h3, h4, h5, h6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
        h1.write("**單號**"); h2.write("**專案名稱**"); hx.write("**負責執行長**"); h3.write("**申請人**"); h4.write("**預計採購金額**"); h5.write("**提交時間**"); h6.write("**操作**")
        for i, r in p_df.iterrows():
            c1, c2, cx, c3, c4, c5, c6 = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
            c1.write(r["單號"]); c2.write(r["專案名稱"]); cx.write(clean_name(r["專案負責人"])); c3.write(r["申請人"]); c4.write(f"${clean_amount(r['總金額']):,.0f}"); c5.write(r["提交時間"])
            with c6:
                b1, b2, b3 = st.columns(3)
                can_sign = (r["專案負責人"] == curr_name) and is_active
                if b1.button("預覽", key=f"ceo_v_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
                if b2.button("✅ 核准", key=f"ceo_ok_{i}", disabled=not can_sign):
                    fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    fresh_db.loc[idx, ["狀態", "初審人", "初審時間"]] = ["已核准", curr_name, get_taiwan_time()]
                    send_line_message(f"🔔 【採購單核准】\n單號：{r['單號']}\n專案：{r['專案名稱']}\n已核准此採購單！")
