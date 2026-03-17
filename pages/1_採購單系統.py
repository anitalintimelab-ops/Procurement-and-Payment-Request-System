import streamlit as st
import pandas as pd
import datetime, os, base64, time, requests

# --- 系統鎖定與介面設定 ---
st.session_state['sys_choice'] = "採購單系統"
st.set_page_config(page_title="時研-採購單系統", layout="wide", page_icon="🏢")
st.markdown("""<style>[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; } .stApp { overflow-x: hidden; }</style>""", unsafe_allow_html=True)

# --- 路徑定位 ---
B_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D_FILE, S_FILE, O_FILE, L_FILE = [os.path.join(B_DIR, f) for f in ["database.csv", "staff_v2.csv", "online.csv", "line_credentials.txt"]]
ADMINS, CFO_NAME, DEFAULT_STAFF = ["Anita"], "Charles", ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

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

def send_line_message(msg):
    try:
        if os.path.exists(L_FILE):
            with open(L_FILE, "r", encoding="utf-8") as f: token = f.read().splitlines()[0].strip()
            requests.post("https://api.line.me/v2/bot/message/broadcast", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, json={"messages": [{"type": "text", "text": msg}]}, timeout=5)
    except: pass

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "代申請人", "專案負責人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱", "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", "刪除原因", "駁回原因", "匯款狀態", "匯款日期", "支付條件", "支付期數", "請款狀態", "已請款金額", "尚未請款金額", "最後採購金額"]
    if not os.path.exists(D_FILE): return pd.DataFrame(columns=cols)
    for enc in ['utf-8-sig', 'utf-8', 'cp950']:
        try:
            df = pd.read_csv(D_FILE, encoding=enc, dtype=str).fillna("")
            if "專案執行人" in df.columns: df = df.rename(columns={"專案執行人": "專案負責人"})
            for c in cols:
                if c not in df.columns: df[c] = ""
            for col in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]: df[col] = df[col].apply(clean_amount)
            for col in ["專案負責人", "申請人", "代申請人"]: df[col] = df[col].astype(str).apply(clean_name)
            df["狀態"] = df["狀態"].astype(str).str.strip()
            return df[cols]
        except: continue
    return pd.DataFrame(columns=cols)

def save_data(df):
    try:
        for col in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]: df[col] = df[col].apply(clean_amount)
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError: st.error("⚠️ 無法寫入檔案！請關閉 Excel。"); st.stop()

def load_staff():
    if not os.path.exists(S_FILE):
        df = pd.DataFrame({"name": DEFAULT_STAFF, "status": ["在職"]*5, "password": ["0000"]*5, "avatar": [""]*5, "line_uid": [""]*5})
        df.to_csv(S_FILE, index=False, encoding='utf-8-sig'); return df
    for enc in ['utf-8-sig', 'utf-8']:
        try: return pd.read_csv(S_FILE, encoding=enc, dtype=str).fillna("")
        except: continue
    return pd.DataFrame()

def save_staff(df): df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            if any(x in f.lower() for x in ["logo", "timelab"]) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                with open(os.path.join(B_DIR, f), "rb") as img: return base64.b64encode(img.read()).decode()
    except: pass
    return ""

def is_pdf(b64_str): return str(b64_str).startswith("JVBERi")

# --- 無下載按鈕、原生渲染 PDF ---
def display_pdf(b64_str, height=700):
    clean_b64 = str(b64_str).replace('\n', '').replace('\r', '')
    html_code = f"""
    <iframe id="pdf-viewer" width="100%" height="{height}px" style="border:none; border-radius:5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);"></iframe>
    <script>
        try {{
            const b64Data = "{clean_b64}";
            const byteCharacters = atob(b64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {{ byteNumbers[i] = byteCharacters.charCodeAt(i); }}
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], {{type: 'application/pdf'}});
            document.getElementById('pdf-viewer').src = URL.createObjectURL(blob);
        }} catch (e) {{ document.getElementById('pdf-viewer').outerHTML = '<p style="color:red; text-align:center;">❌ PDF 載入失敗，檔案可能損毀。</p>'; }}
    </script>
    """
    st.components.v1.html(html_code, height=height)

# --- 登入與基礎設置 ---
if 'user_id' not in st.session_state or st.session_state.user_id is None: st.switch_page("app.py")
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
for key in ['edit_id', 'last_id', 'view_id']:
    if key not in st.session_state: st.session_state[key] = None
if 'form_key' not in st.session_state: st.session_state.form_key = 0 

curr_name, is_active, is_admin = st.session_state.user_id, (st.session_state.user_status == "在職"), (st.session_state.user_id in ADMINS)

# --- 左側選單 (嚴格遵守請款單格式) ---
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
            staff_df = load_staff(); staff_df.loc[staff_df["name"] == reset_target, "password"] = "0000"
            save_staff(staff_df); st.session_state.staff_df = staff_df; st.success("已重置")
    with st.sidebar.expander("➕ 新增人員"):
        n = st.text_input("姓名")
        if st.button("新增") and n not in st.session_state.staff_df["name"].values:
            st.session_state.staff_df = pd.concat([st.session_state.staff_df, pd.DataFrame([{"name":n, "status":"在職", "password":"0000", "avatar":"", "line_uid":""}])])
            save_staff(st.session_state.staff_df); st.success("成功"); st.rerun()
    with st.sidebar.expander("⚙️ 人員設定 (狀態 & LINE ID)"):
        edited_staff = st.data_editor(st.session_state.staff_df[["name", "status", "line_uid"]], column_config={"name": st.column_config.TextColumn("姓名", disabled=True), "status": st.column_config.SelectboxColumn("狀態", options=["在職", "離職"])}, hide_index=True)
        if st.button("💾 儲存人員設定"):
            for idx, row in edited_staff.iterrows(): st.session_state.staff_df.loc[idx, ["status", "line_uid"]] = [row["status"], str(row["line_uid"]).strip() if pd.notna(row["line_uid"]) else ""]
            save_staff(st.session_state.staff_df); st.success("已更新！"); time.sleep(0.5); st.rerun()

if st.sidebar.button("登出"):
    st.session_state.user_id = None
    if 'menu_radio' in st.session_state: del st.session_state['menu_radio']
    st.switch_page("app.py")

# --- 導覽與共用組件 ---
menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽及轉請款單"]
if is_admin: menu_options.append("5. 請款狀態/系統設定")
menu = st.sidebar.radio("導覽", menu_options)

def render_header():
    logo_b64 = get_b64_logo()
    if logo_b64: st.markdown(f'<div style="display:flex;align-items:center;justify-content:center;gap:15px;margin-bottom:20px;"><img src="data:image/png;base64,{logo_b64}" style="height:60px;"><h2>時研國際設計股份有限公司</h2></div>', unsafe_allow_html=True)
    else: st.title("時研國際設計股份有限公司")
    st.divider()

def render_html(row):
    amt = clean_amount(row['總金額'])
    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;"><h2 style="text-align:center;border-bottom:2px solid #000;padding-bottom:10px;">時研國際設計 - 採購單</h2>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;table-layout:fixed;" border="1">'
    h += f'<tr><td bgcolor="#eee" width="25%">單號</td><td width="25%">{row["單號"]}</td><td bgcolor="#eee" width="25%">負責執行長</td><td width="25%">{clean_name(row["專案負責人"])}</td></tr>'
    h += f'<tr><td bgcolor="#eee">專案</td><td>{row["專案名稱"]}</td><td bgcolor="#eee">編號</td><td>{row["專案編號"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">申請人</td><td colspan="3">{row["申請人"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">說明</td><td colspan="3">{row["請款說明"]}</td></tr>'
    c_cur = str(row.get("幣別", "TWD")).replace("nan", "TWD")
    h += f'<tr><td colspan="3" align="right">預計採購金額</td><td align="right">{c_cur} {amt:,.0f}</td></tr></table>'
    if row["狀態"] == "已駁回": h += f'<p style="color:red;margin-top:10px;"><b>❌ 駁回原因：</b>{row["駁回原因"]}</p>'
    h += f'<p style="margin-top:10px;">提交: {row.get("提交時間","")} | 初審: {row.get("初審人","")} {row.get("初審時間","")}</p></div>'
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

# --- 歷史清單共用模組 (省去重複程式碼，避免斷掉) ---
def render_history_list(h_df, is_ceo_page=False):
    if h_df.empty: st.info("尚無紀錄")
    else: 
        cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1, 3.5])
        headers = ["單號", "專案名稱", "負責執行長", "申請人", "總金額", "狀態", "操作"]
        for c, h in zip(cols, headers): c.write(f"**{h}**")
        for i, r in h_df.iterrows():
            c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1, 3.5])
            c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"]))
            c[3].write(r["申請人"]); c[4].write(f"${clean_amount(r['總金額']):,.0f}"); c[5].write(r["狀態"])
            with c[6]:
                b1, b2, b3, b4 = st.columns(4)
                if b1.button("🔍 預覽", key=f"hv_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
                if b2.button("🖨️ 列印", key=f"hp_{i}"):
                    js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                    st.components.v1.html(f"<script>{js_p}</script>", height=0)
                if is_ceo_page and (r["專案負責人"] == curr_name) and is_active and (r["狀態"] == "已核准"):
                    with b3.popover("📝 更新"):
                        bs = st.text_input("請款狀態", value=str(r.get("請款狀態", "")), key=f"cbs_{i}")
                        ba = st.number_input("已請款金額", value=int(clean_amount(r.get("已請款金額", 0))), min_value=0, key=f"cba_{i}")
                        ua = st.number_input("尚未請款金額", value=int(clean_amount(r.get("尚未請款金額", 0))), min_value=0, key=f"cua_{i}")
                        dc = st.text_area("修改說明內容", value=str(r.get("請款說明", "")), key=f"cdesc_{i}")
                        if st.button("💾 儲存修改", key=f"csm_{i}"):
                            fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                            fresh_db.loc[idx, ["請款狀態", "已請款金額", "尚未請款金額", "請款說明"]] = [bs, ba, ua, dc]
                            save_data(fresh_db); st.success("已更新！"); time.sleep(0.5); st.rerun()
                else:
                    if is_ceo_page: b3.button("✏️ 修改", disabled=True, key=f"fce_{i}")
                render_upload_popover(b4 if is_ceo_page else b3, r, f"hup_{i}")

# ================= 頁面邏輯 =================
if menu == "1. 填寫申請單":
    render_header()
    st.subheader("填寫申請單")
    db = load_data()
    staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
    if curr_name not in staffs: staffs.append(curr_name)
    dv = {"pn":"", "exe":staffs[0], "pi":"", "amt":0, "curr":"TWD", "pay":"現金", "vdr":"", "acc":"", "desc":"", "ab64":"", "ib64":"", "app": curr_name, "pay_cond": "", "pay_inst": "", "final_amt": 0, "billed_amt": 0, "unbilled_amt": 0, "bill_stat": ""}
    
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id]
        if not r.empty:
            row = r.iloc[0]
            st.info(f"📝 修改中: {st.session_state.edit_id}")
            dv.update({"app": clean_name(row.get("申請人", curr_name)), "pn": str(row.get("專案名稱", "")), "exe": clean_name(row.get("專案負責人", staffs[0])), "pi": str(row.get("專案編號", "")), "amt": clean_amount(row.get("總金額", 0)), "curr": str(row.get("幣別", "TWD")), "pay": str(row.get("付款方式", "現金")), "vdr": str(row.get("請款廠商", "")), "acc": str(row.get("匯款帳戶", "")), "desc": str(row.get("請款說明", "")), "ab64": str(row.get("帳戶影像Base64", "")), "ib64": str(row.get("影像Base64", "")), "pay_cond": str(row.get("支付條件", "")), "pay_inst": str(row.get("支付期數", "")), "final_amt": clean_amount(row.get("最後採購金額", 0)), "billed_amt": clean_amount(row.get("已請款金額", 0)), "unbilled_amt": clean_amount(row.get("尚未請款金額", 0)), "bill_stat": str(row.get("請款狀態", ""))})

    with st.form("form"):
        mode_sfx = f"{st.session_state.edit_id}_{st.session_state.form_key}" if st.session_state.edit_id else f"new_{st.session_state.form_key}"
        c1, c2 = st.columns(2)
        if curr_name == "Anita": app_val = c1.selectbox("申請人 (可代申請)", staffs, index=staffs.index(dv["app"]) if dv["app"] in staffs else staffs.index(curr_name))
        else: app_val = curr_name; c1.text_input("申請人", value=app_val, disabled=True)
        pn = c1.text_input("專案名稱", value=dv["pn"])
        exe = c1.selectbox("負責執行長", staffs, index=staffs.index(dv["exe"]) if dv["exe"] in staffs else 0)
        pi = c2.text_input("專案編號", value=dv["pi"])
        amt = c2.number_input("預計採購金額", value=int(max(0, dv["amt"])), min_value=0)
        currency = c2.selectbox("幣別", ["TWD", "USD", "EUR", "JPY", "CNY", "HKD", "GBP", "AUD"], index=["TWD", "USD", "EUR", "JPY", "CNY", "HKD", "GBP", "AUD"].index(dv["curr"]) if dv["curr"] in ["TWD", "USD", "EUR", "JPY", "CNY", "HKD", "GBP", "AUD"] else 0)
        
        st.markdown("---")
        st.markdown("**(採購單專屬欄位 - 皆為非必填)**")
        cp1, cp2, cp3 = st.columns(3)
        pay_cond = cp1.text_input("支付條件", value=dv["pay_cond"])
        pay_inst = cp2.text_input("支付期數", value=dv["pay_inst"])
        final_amt = cp3.number_input("最後採購金額", value=int(max(0, dv["final_amt"])), min_value=0)
        cp4, cp5, cp6 = st.columns(3)
        bill_stat = cp4.text_input("請款狀態", value=dv["bill_stat"])
        billed_amt = cp5.number_input("已請款金額", value=int(max(0, dv["billed_amt"])), min_value=0)
        unbilled_amt = cp6.number_input("尚未請款金額", value=int(max(0, dv["unbilled_amt"])), min_value=0)
        st.markdown("---")
        
        pay_idx = ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"].index(dv["pay"]) if dv["pay"] in ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"] else 1
        pay = st.radio("付款方式", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], index=pay_idx, horizontal=True)
        vdr = st.text_input("廠商", value=dv["vdr"])
        acc = st.text_input("帳戶", value=dv["acc"])
        desc = st.text_area("說明", value=dv["desc"])
        
        del_acc = False
        if dv["ab64"]:
            st.write("✅ 已有存摺")
            if is_pdf(dv["ab64"]): display_pdf(dv["ab64"], height=250)
            else: st.image(base64.b64decode(dv["ab64"]), width=200)
            del_acc = st.checkbox("❌ 刪除此存摺")
        f_acc = st.file_uploader("上傳存摺 (支援圖/PDF)", type=["png", "jpg", "jpeg", "pdf"])
        
        del_ims = False
        if dv["ib64"]:
            st.write("✅ 已有憑證")
            del_ims = st.checkbox("❌ 刪除所有憑證")
        f_ims = st.file_uploader("上傳憑證 (支援圖/PDF)", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
        
        if st.form_submit_button("💾 儲存", disabled=not is_active):
            db = load_data()
            if not (pn and pi and amt>0 and desc): st.error("請填寫必填欄位 (專案名稱、編號、金額、說明)")
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
                    tid = f"{today_str}-{len(db[db['單號'].astype(str).str.startswith(today_str)])+1:02d}" if not db.empty else f"{today_str}-01"
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"採購單", "申請人":app_val, "代申請人":proxy_val, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":desc, "總金額":amt, "幣別":currency, "付款方式":pay, "請款廠商":vdr, "匯款帳戶":acc, "帳戶影像Base64":b_acc, "狀態":"已儲存", "影像Base64":b_ims, "提交時間":"", "申請人信箱":curr_name, "初審人":"", "初審時間":"", "複審人":"", "複審時間":"", "刪除人":"", "刪除時間":"", "刪除原因":"", "駁回原因":"", "支付條件": pay_cond, "支付期數": pay_inst, "請款狀態": bill_stat, "已請款金額": billed_amt, "尚未請款金額": amt, "最後採購金額": final_amt}
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
    # --- 恢復與請款單完全一致的列寬 [1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5] ---
    cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
    headers = ["申請單號", "專案名稱", "負責執行長", "申請人", "預計採購金額", "狀態", "操作"]
    for col, hdr in zip(cols, headers): col.write(f"**{hdr}**")
    
    my_db = load_data()
    my_db = my_db[my_db["類型"] == "採購單"]
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    
    for i, r in my_db.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"])
        c_cur = str(r.get('幣別','TWD')).replace("nan", "TWD")
        c[4].write(f"{c_cur} ${clean_amount(r['總金額']):,.0f}")
        stt = r["狀態"]
        c[5].markdown(f":{'blue' if stt in ['已儲存', '草稿'] else 'orange' if '待' in stt else 'green' if stt == '已核准' else 'red' if stt == '已駁回' else 'gray'}[**{stt}**]")
        
        with c[6]:
            b1, b2, b3, b4, b5, b6 = st.columns(6)
            is_own = (str(r["申請人"]).strip() == curr_name) or (str(r.get("代申請人", "")).strip() == curr_name)
            can_edit = (stt in ["已儲存", "草稿", "已駁回"]) and is_own and is_active
            
            if b1.button("提交", key=f"s{i}", disabled=not can_edit):
                fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                fresh_db.loc[idx, ["狀態", "提交時間", "初審人", "初審時間", "複審人", "複審時間", "駁回原因"]] = ["待簽核", get_taiwan_time(), "", "", "", "", ""]
                save_data(fresh_db); send_line_message(f"🔔【待簽核】\n單號：{r['單號']}\n專案：{r['專案名稱']}\n需簽核！"); st.rerun()
            if b2.button("預覽", key=f"v{i}"): st.session_state.view_id = r["單號"]; st.rerun()
            if b3.button("列印", key=f"p{i}"):
                js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                st.components.v1.html(f'<script>{js_p}</script>', height=0)
            if b4.button("修改", key=f"e{i}", disabled=not can_edit): st.session_state.edit_id = r["單號"]; st.rerun()
            
            if stt == "已核准" and is_active:
                with b5.popover("📝 更新"):
                    bs = st.text_input("請款狀態", value=str(r.get("請款狀態", "")), key=f"m1_bs_{i}")
                    ba = st.number_input("已請款金額", value=int(clean_amount(r.get("已請款金額", 0))), min_value=0, key=f"m1_ba_{i}")
                    ua = st.number_input("尚未請款金額", value=int(clean_amount(r.get("尚未請款金額", 0))), min_value=0, key=f"m1_ua_{i}")
                    dc = st.text_area("說明內容", value=str(r.get("請款說明", "")), key=f"m1_desc_{i}")
                    if st.button("💾 儲存修改", key=f"m1_save_{i}"):
                        fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                        fresh_db.loc[idx, ["請款狀態", "已請款金額", "尚未請款金額", "請款說明"]] = [bs, ba, ua, dc]
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

# --- 頁面 2: 執行長簽核 ---
elif menu == "2. 專案執行長簽核":
    render_header()
    st.subheader("🔍 專案執行長簽核")
    sys_db = load_data(); sys_db = sys_db[sys_db["類型"] == "採購單"]
    p_df = sys_db[sys_db["狀態"].isin(["待簽核", "待初審"])] if is_admin else sys_db[(sys_db["狀態"].isin(["待簽核", "待初審"])) & (sys_db["專案負責人"] == curr_name)]
    
    st.subheader("⏳ 待簽核清單")
    if p_df.empty: st.info("目前無待簽核單據")
    else: 
        cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
        headers = ["單號", "專案名稱", "負責執行長", "申請人", "預計採購金額", "提交時間", "操作"]
        for c, h in zip(cols, headers): c.write(f"**{h}**")
        for i, r in p_df.iterrows():
            c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
            c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"])
            c_cur = str(r.get('幣別','TWD')).replace("nan", "TWD")
            c[4].write(f"{c_cur} ${clean_amount(r['總金額']):,.0f}"); c[5].write(r["提交時間"])
            with c[6]:
                b1, b2, b3 = st.columns(3)
                can_sign = (r["專案負責人"] == curr_name) and is_active
                if b1.button("預覽", key=f"cv_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
                if b2.button("✅ 核准", key=f"cok_{i}", disabled=not can_sign):
                    fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    fresh_db.loc[idx, ["狀態", "初審人", "初審時間"]] = ["已核准", curr_name, get_taiwan_time()]
                    send_line_message(f"🔔 【採購單核准】\n單號：{r['單號']}\n專案：{r['專案名稱']}\n已核准此採購單！")
                    save_data(fresh_db); st.rerun()
                if can_sign:
                    with b3.popover("❌ 駁回"):
                        reason = st.text_input("駁回原因", key=f"cr_{i}")
                        if st.button("確認", key=f"cno_{i}"):
                            fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                            fresh_db.loc[idx, ["狀態", "駁回原因", "初審人", "初審時間"]] = ["已駁回", reason, curr_name, get_taiwan_time()]
                            save_data(fresh_db); st.rerun()
                else: b3.button("❌ 駁回", disabled=True, key=f"fk_no_{i}")
    
    st.divider(); st.subheader("📜 歷史紀錄 (已核准/已駁回)")
    h_df = sys_db[sys_db["狀態"].isin(["待複審", "已核准", "已駁回"])] if is_admin else sys_db[(sys_db["專案負責人"] == curr_name) & (sys_db["狀態"].isin(["待複審", "已核准", "已駁回"]))]
    render_history_list(h_df, is_ceo_page=True)

# --- 頁面 3: 財務長簽核 ---
elif menu == "3. 財務長簽核":
    render_header()
    st.subheader("🏁 財務長簽核 (功能保留)")
    sys_db = load_data(); sys_db = sys_db[sys_db["類型"] == "採購單"]
    st.subheader("⏳ 待財務長簽核")
    p_df = sys_db[sys_db["狀態"] == "待複審"] if is_admin or curr_name == CFO_NAME else sys_db[(sys_db["狀態"] == "待複審") & (sys_db["專案負責人"] == curr_name)]
        
    if p_df.empty: st.info("無待審單據")
    else: 
        cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 2.5])
        headers = ["單號", "專案名稱", "負責執行長", "申請人", "總金額", "操作"]
        for c, h in zip(cols, headers): c.write(f"**{h}**")
        for i, r in p_df.iterrows():
            c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 2.5])
            c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"]); c[4].write(f"${clean_amount(r['總金額']):,.0f}")
            with c[5]:
                b1, b2, b3 = st.columns(3)
                is_cfo_act = (curr_name == CFO_NAME) and is_active
                if b1.button("預覽", key=f"cfv_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
                if b2.button("👑 核准", key=f"cfok_{i}", disabled=not is_cfo_act):
                    fresh_db = load_data(); fresh_db.loc[fresh_db["單號"]==r["單號"], ["狀態", "複審人", "複審時間"]] = ["已核准", curr_name, get_taiwan_time()]
                    save_data(fresh_db); st.rerun()
                if is_cfo_act:
                    with b3.popover("❌ 駁回"):
                        reason = st.text_input("原因", key=f"cfr_{i}")
                        if st.button("確認", key=f"cfno_{i}"):
                            fresh_db = load_data(); fresh_db.loc[fresh_db["單號"]==r["單號"], ["狀態", "駁回原因", "複審人", "複審時間"]] = ["已駁回", reason, curr_name, get_taiwan_time()]
                            save_data(fresh_db); st.rerun()
                else: b3.button("❌ 駁回", disabled=True, key=f"fk_cfno_{i}")
    st.divider(); st.subheader("📜 歷史紀錄 (已核准/已駁回)")
    f_df = sys_db[sys_db["狀態"].isin(["已核准", "已駁回"])] if is_admin or curr_name == CFO_NAME else sys_db[(sys_db["專案負責人"] == curr_name) & (sys_db["狀態"].isin(["已核准", "已駁回"]))]
    render_history_list(f_df, is_ceo_page=False)

# --- 頁面 4: 表單狀態總覽及轉請款單 ---
elif menu == "4. 表單狀態總覽及轉請款單":
    render_header()
    st.subheader("📊 表單狀態總覽及轉請款單")
    sys_db = load_data(); sys_db = sys_db[sys_db["類型"] == "採購單"]
    if not is_admin: sys_db = sys_db[(sys_db["申請人"] == curr_name) | (sys_db["代申請人"] == curr_name) | (sys_db["專案負責人"] == curr_name)]
    
    if not sys_db.empty:
        st.info("💡 勾選採購單並「雙擊」下方輸入框填寫【本次請款金額】，確認無誤後點擊送出，即可一鍵建立新的請款單草稿！(請款金額不得超過尚未請款金額)")
        display_df = sys_db.copy()
        display_df.insert(0, "轉成請款單", False)
        display_df.insert(1, "本次請款金額(點擊輸入)", 0)
        display_df["負責執行長"] = display_df["專案負責人"]
        display_df["預計採購金額"] = display_df.apply(lambda x: f"{str(x.get('幣別','TWD')).replace('nan','TWD')} ${clean_amount(x.get('總金額',0)):,.0f}", axis=1)
        display_df["請款狀態"] = display_df["請款狀態"].fillna("").astype(str)
        display_df["已請款金額"] = display_df["已請款金額"].apply(clean_amount)
        display_df["尚未請款金額"] = display_df["尚未請款金額"].apply(clean_amount)
        display_df = display_df.rename(columns={"單號": "申請單號"})
        
        target_cols = ["轉成請款單", "本次請款金額(點擊輸入)", "申請單號", "專案名稱", "負責執行長", "申請人", "預計採購金額", "狀態", "請款狀態", "已請款金額", "尚未請款金額"]
        edited_df = st.data_editor(
            display_df[target_cols], disabled=["申請單號", "專案名稱", "負責執行長", "申請人", "預計採購金額", "狀態", "請款狀態", "已請款金額", "尚未請款金額"], hide_index=True, use_container_width=True,
            column_config={"轉成請款單": st.column_config.CheckboxColumn("勾選轉換"), "本次請款金額(點擊輸入)": st.column_config.NumberColumn("本次請款金額 (雙擊輸入)", min_value=0, step=1)}
        )
        
        if st.button("🚀 確認將勾選項目轉成請款單"):
            fresh_db = load_data()
            converted_count, has_error = 0, False
            for i, row in edited_df.iterrows():
                conv_amt = row.get("本次請款金額(點擊輸入)")
                if bool(row.get("轉成請款單")) and pd.notna(conv_amt) and int(float(conv_amt)) > 0:
                    orig_id = row["申請單號"]
                    orig_idx = fresh_db[fresh_db["單號"]==orig_id].index[0]
                    orig_row = fresh_db.iloc[orig_idx]
                    real_conv_amt = int(float(conv_amt))
                    
                    final_amt = clean_amount(orig_row.get("最後採購金額", 0))
                    if final_amt == 0: final_amt = clean_amount(orig_row.get("總金額", 0))
                    current_billed = clean_amount(orig_row.get("已請款金額", 0))
                    current_unbilled = final_amt - current_billed
                    
                    if real_conv_amt > current_unbilled:
                        st.error(f"❌ 單號 {orig_id} 失敗：本次請款金額 ({real_conv_amt:,}) 超過尚未請款金額 ({current_unbilled:,})！")
                        has_error = True; continue 
                    
                    fresh_db.at[orig_idx, "已請款金額"] = current_billed + real_conv_amt
                    fresh_db.at[orig_idx, "尚未請款金額"] = current_unbilled - real_conv_amt
                    fresh_db.at[orig_idx, "請款狀態"] = "已轉請款單"
                    
                    today_str = datetime.date.today().strftime('%Y%m%d')
                    new_tid = f"{today_str}-{len(fresh_db[fresh_db['單號'].astype(str).str.startswith(today_str)])+1:02d}"
                    nr = {"單號": new_tid, "日期": str(datetime.date.today()), "類型": "請款單", "申請人": "Anita", "代申請人": "", "專案負責人": orig_row.get("專案負責人",""), "專案名稱": orig_row.get("專案名稱",""), "專案編號": orig_row.get("專案編號",""), "請款說明": f"自採購單 {orig_id} 轉換 (轉換金額: {real_conv_amt})", "總金額": real_conv_amt, "幣別": orig_row.get("幣別","TWD"), "付款方式": orig_row.get("付款方式",""), "請款廠商": orig_row.get("請款廠商",""), "匯款帳戶": orig_row.get("匯款帳戶",""), "帳戶影像Base64": orig_row.get("帳戶影像Base64",""), "狀態": "已儲存", "影像Base64": orig_row.get("影像Base64",""), "提交時間": "", "申請人信箱": "Anita", "初審人": "", "初審時間": "", "複審人": "", "複審時間": "", "刪除人": "", "刪除時間": "", "刪除原因": "", "駁回原因": "", "支付條件": "", "支付期數": "", "請款狀態": "", "已請款金額": 0, "尚未請款金額": 0, "最後採購金額": 0}
                    fresh_db = pd.concat([fresh_db, pd.DataFrame([nr])], ignore_index=True)
                    converted_count += 1
            if converted_count > 0:
                save_data(fresh_db); st.success(f"✅ 成功轉換 {converted_count} 筆！請至「請款單系統」提交。")
                time.sleep(1.5); st.rerun()
            elif not has_error: st.warning("請確保有勾選項目，且輸入金額大於 0！")
    else: st.info("尚無您的表單狀態紀錄。")

# --- 頁面 5: 請款狀態/系統設定 (與請款單完全一致) ---
elif menu == "5. 請款狀態/系統設定":
    render_header()
    st.error("⚠️ **雲端暫存機制提醒：** 免費雲端主機重啟會清空資料。請管理員務必在下班前下載備份！")
    
    with st.expander("💾 1. 表單資料庫備份與還原", expanded=True):
        col_down, col_up = st.columns(2)
        with col_down:
            st.write("⬇️ **步驟一：下載最新表單資料庫**")
            if os.path.exists(D_FILE):
                with open(D_FILE, "rb") as f: st.download_button("下載表單備份檔", f, file_name=f"時研系統表單備份_{datetime.date.today()}.csv", mime="text/csv")
        with col_up:
            st.write("⬆️ **步驟二：還原表單資料庫**")
            uploaded_db = st.file_uploader("上傳表單 CSV 檔", type=["csv"], key="up_db", label_visibility="collapsed")
            if uploaded_db and st.button("確認還原表單"):
                with open(D_FILE, "wb") as f: f.write(uploaded_db.getbuffer())
                st.success("表單資料庫已還原！"); time.sleep(1); st.rerun()

    with st.expander("👥 2. 人員與大頭貼資料備份與還原"):
        col_down2, col_up2 = st.columns(2)
        with col_down2:
            st.write("⬇️ **步驟一：下載最新人員資料 (含大頭貼與LINE ID)**")
            if os.path.exists(S_FILE):
                with open(S_FILE, "rb") as f: st.download_button("下載人員備份檔", f, file_name=f"時研系統人員備份_{datetime.date.today()}.csv", mime="text/csv")
        with col_up2:
            st.write("⬆️ **步驟二：還原人員資料**")
            uploaded_staff = st.file_uploader("上傳人員 CSV 檔", type=["csv"], key="up_staff", label_visibility="collapsed")
            if uploaded_staff and st.button("確認還原人員資料"):
                with open(S_FILE, "wb") as f: f.write(uploaded_staff.getbuffer())
                st.session_state.staff_df = load_staff()
                st.success("人員資料已還原！"); time.sleep(1); st.rerun()

    with st.expander("🔔 3. LINE 官方帳號推播設定 (全域 Token & 行政副本 ID)"):
        st.write("請填寫從 LINE Developers 取得的兩組關鍵代碼：")
        curr_token, curr_uid = get_line_credentials()
        new_token = st.text_input("Channel Access Token (長字串)", value=curr_token, type="password")
        new_uid = st.text_input("行政專屬 User ID (U開頭，用來接收所有副本)", value=curr_uid)
        if st.button("💾 儲存 LINE 設定"):
            save_line_credentials(new_token, new_uid) 
            st.success("LINE 推播設定已成功儲存並啟用！"); time.sleep(1); st.rerun()

    st.divider()
    st.subheader("💰 財務匯款註記 (僅管理員)")
    st.info("💡 溫馨提醒：此處編輯的「匯款狀態」與「匯款日期」都已包含在上方的「表單資料庫備份」中，還原時會一併恢復，無須重新手動輸入！")
    try:
        sys_db = load_data()
        display_df = sys_db[sys_db["類型"] == "採購單"].copy()
        if not display_df.empty:
            display_df["負責執行長"] = display_df["專案負責人"]
            display_df["總金額"] = display_df.apply(lambda x: f"{str(x.get('幣別','TWD')).replace('nan','TWD')} ${clean_amount(x.get('總金額',0)):,.0f}", axis=1)
            display_df = display_df.rename(columns={"單號": "申請單號"})
            
            def parse_date(d_str):
                if pd.isna(d_str) or str(d_str).strip() == "": return None
                try: return datetime.datetime.strptime(str(d_str).strip(), "%Y-%m-%d").date()
                except: return None
                
            display_df["匯款日期"] = display_df["匯款日期"].apply(parse_date)
            target_cols = ["申請單號", "專案名稱", "負責執行長", "申請人", "總金額", "狀態", "匯款狀態", "匯款日期"]
            
            edited_df = st.data_editor(
                display_df[target_cols], disabled=["申請單號", "專案名稱", "負責執行長", "申請人", "總金額", "狀態"],
                use_container_width=True,
                column_config={"匯款狀態": st.column_config.SelectboxColumn("匯款狀態", options=["尚未匯款", "已匯款"], required=True, width="medium"), "匯款日期": st.column_config.DateColumn("匯款日期", format="YYYY-MM-DD", width="medium", min_value=datetime.date(2020, 1, 1), max_value=datetime.date(2030, 12, 31))}
            )
            
            if st.button("💾 儲存匯款資訊"):
                valid = True
                for i, row in edited_df.iterrows():
                    if row["匯款狀態"] == "已匯款" and (pd.isna(row["匯款日期"]) or str(row["匯款日期"]) == "NaT"):
                        st.error(f"❌ 申請單號 {row['申請單號']}：選擇「已匯款」時，必須填寫匯款日期！"); valid = False
                if valid:
                    fresh_db = load_data()
                    for i, row in edited_df.iterrows():
                        orig_idx = fresh_db[fresh_db["單號"]==row["申請單號"]].index[0]
                        fresh_db.at[orig_idx, "匯款狀態"] = str(row["匯款狀態"]) if row["匯款狀態"] else "尚未匯款"
                        date_val = row["匯款日期"]
                        fresh_db.at[orig_idx, "匯款日期"] = str(date_val) if pd.notna(date_val) and str(date_val) != "NaT" else ""
                    save_data(fresh_db); st.success("✅ 匯款資訊已成功更新！"); time.sleep(1); st.rerun()
        else: st.info("尚無資料。")
    except Exception as e: st.error(f"錯誤：{str(e)}")

# --- 全域預覽 ---
if st.session_state.view_id:
    st.markdown("---")
    try:
        r = load_data(); r = r[r["單號"]==st.session_state.view_id]
        if not r.empty:
            c1, c2 = st.columns([8, 2])
            c1.markdown("### 🔍 表單預覽")
            if c2.button("❌ 關閉預覽", key="close_view"): st.session_state.view_id = None; st.rerun()
            
            st.markdown(render_html(r.iloc[0]), unsafe_allow_html=True)
            if r.iloc[0].get("影像Base64"):
                st.markdown("#### 📎 附件檔案")
                for img in r.iloc[0]["影像Base64"].split('|'):
                    if is_pdf(img): display_pdf(img)
                    else: st.image(base64.b64decode(img), use_container_width=True)
    except Exception as e: st.error(f"預覽發生錯誤：{str(e)}")
