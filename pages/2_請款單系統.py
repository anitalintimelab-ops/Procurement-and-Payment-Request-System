import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  
import json
import io

# --- 1. 系統鎖定與介面設定 ---
st.session_state['sys_choice'] = "請款單系統"
st.set_page_config(page_title="時研-請款單系統", layout="wide", page_icon="🏢")

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

# --- 2. 路徑定位 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) 
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- 3. 基礎工具 ---
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
    try:
        df.columns = [c.strip() for c in df.columns]
        if "專案執行人" in df.columns: df = df.rename(columns={"專案執行人": "專案負責人"})
        for c in cols:
            if c not in df.columns: df[c] = ""
        for c in ["總金額", "已請款金額", "尚未請款金額"]:
            df[c] = df[c].apply(clean_amount)
        return df[cols]
    except:
        return pd.DataFrame(columns=cols)

def save_data(df):
    try: df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except: st.error("⚠️ 檔案鎖定中！請關閉電腦上的 database.csv。"); st.stop()

def load_staff():
    df = read_csv_robust(S_FILE)
    if df is None or df.empty: return pd.DataFrame({"name": DEFAULT_STAFF, "status":["在職"]*5, "password":["0000"]*5})
    return df

def save_staff(df): df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

# --- 4. 請款單資料打包解析器 ---
def parse_req_json(desc_raw):
    try:
        if "[請款單資料]" in desc_raw:
            return json.loads(desc_raw.split("[請款單資料]")[1].strip())
    except: pass
    return {"desc": desc_raw, "net_amt": 0, "tax_amt": 0, "fee": 0, "inv_no": ""}

# --- 5. HTML 渲染 ---
def render_html(row):
    amt = clean_amount(row['總金額'])
    data = parse_req_json(row.get("請款說明", ""))
    
    # 判斷代申請人顯示方式
    display_app = f"{row['申請人']} ({row.get('代申請人', '')} 代申請)" if row.get("代申請人") else row['申請人']
    
    legacy_net = amt if data.get("net_amt", 0) == 0 and data.get("tax_amt", 0) == 0 else data.get("net_amt", 0)
    fee = data.get("fee", 0)

    # 頁腳審核資訊格式化
    sub_time = str(row.get("提交時間", ""))
    sub_time_str = sub_time[:16] if sub_time else ""
    fst_appr = str(row.get("初審人", ""))
    fst_time = str(row.get("初審時間", ""))[:16] if str(row.get("初審時間", "")) else ""
    sec_appr = str(row.get("複審人", ""))
    sec_time = str(row.get("複審時間", ""))[:16] if str(row.get("複審時間", "")) else ""

    s_submit = f"提交: {display_app} {sub_time_str}".strip()
    s_first = f"初審: {fst_appr} {fst_time}".strip() if fst_appr else "初審: "
    s_second = f"複審: {sec_appr} {sec_time}".strip() if sec_appr else "複審: "

    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;font-family:sans-serif;">'
    h += f'<div style="text-align:center;"><h2>時研國際設計 - 請款申請單</h2></div>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += f'<tr><td bgcolor="#eee" width="25%">單號</td><td>{row["單號"]}</td><td bgcolor="#eee">執行長</td><td>{row["專案負責人"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">專案</td><td>{row["專案名稱"]}</td><td bgcolor="#eee">編號</td><td>{row["專案編號"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">申請人</td><td colspan="3">{display_app}</td></tr>'
    h += f'<tr><td bgcolor="#eee">請款廠商</td><td>{row.get("請款廠商","")}</td><td bgcolor="#eee">匯款帳戶</td><td>{row.get("匯款帳戶","")}</td></tr>'
    h += f'<tr><td bgcolor="#eee">發票/憑證</td><td colspan="3">{data.get("inv_no","")}</td></tr>'
    h += f'<tr><td bgcolor="#eee">付款方式</td><td colspan="3">{row.get("付款方式","")}</td></tr>'
    h += f'<tr><td bgcolor="#eee">請款說明</td><td colspan="3">{data.get("desc","")}</td></tr>'
    
    h += f'<tr><td colspan="3" align="right"><b>金額 (未稅)</b></td><td align="right"><b>{row.get("幣別","TWD")} {legacy_net:,}</b></td></tr>'
    h += f'<tr><td colspan="3" align="right"><b>稅額</b></td><td align="right"><b>{row.get("幣別","TWD")} {data.get("tax_amt", 0):,}</b></td></tr>'
    h += f'<tr><td colspan="3" align="right"><b>手續費</b></td><td align="right"><b>{row.get("幣別","TWD")} {fee:,}</b></td></tr>'
    h += f'<tr><td colspan="3" align="right"><b>請款總金額</b></td><td align="right"><b>{row.get("幣別","TWD")} {amt:,}</b></td></tr></table>'
    
    h += f'<p style="font-size:14px;margin-top:15px;">{s_submit} | {s_first} | {s_second}</p></div>'
    return h

def clean_for_js(h_str): return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

def render_upload_popover(container, r, prefix):
    with container.popover("📎 附件"):
        st.write("**上傳附件 (圖/Excel)**")
        nf_acc = st.file_uploader("存摺", type=["png", "jpg", "xlsx", "xls"], key=f"{prefix}_a")
        nf_ims = st.file_uploader("憑證", type=["png", "jpg", "xlsx", "xls"], accept_multiple_files=True, key=f"{prefix}_i")
        if st.button("💾 儲存附件", key=f"{prefix}_b"):
            fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
            if nf_acc: fresh_db.at[idx, "帳戶影像Base64"] = base64.b64encode(nf_acc.getvalue()).decode()
            if nf_ims: fresh_db.at[idx, "影像Base64"] = "|".join([base64.b64encode(f.getvalue()).decode() for f in nf_ims])
            save_data(fresh_db); st.rerun()

# --- 6. Session 初始化 ---
if st.session_state.get('user_id') is None: st.switch_page("app.py")
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
for k in ['edit_id', 'last_id', 'view_id', 'print_id', 'last_msg']: 
    if k not in st.session_state: st.session_state[k] = None

curr_name, is_admin = st.session_state.user_id, (st.session_state.user_id in ADMINS)
is_active = (st.session_state.user_status == "在職")

# --- 7. 左側側邊欄 ---
st.sidebar.markdown(f"**📌 目前系統：** `{st.session_state.sys_choice}`")
st.sidebar.divider()

avatar_b64 = ""
try: avatar_b64 = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0].get("avatar", "")
except: pass

if avatar_b64: st.sidebar.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:15px;"><img src="data:image/jpeg;base64,{avatar_b64}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;border:3px solid #eee;"><span style="font-size:22px;font-weight:bold;color:#333;">{curr_name}</span></div>', unsafe_allow_html=True)
else: st.sidebar.markdown(f"### 👤 {curr_name}")

st.sidebar.info(f"🟢 目前在線人數：**{get_online_users(curr_name)}** 人")

with st.sidebar.expander("📸 修改大頭貼"):
    new_avatar = st.file_uploader("上傳圖片", type=["jpg", "png"], key="req_side_avatar")
    if st.button("更新大頭貼", key="req_update_avatar") and new_avatar:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "avatar"] = base64.b64encode(new_avatar.getvalue()).decode()
        save_staff(s_df); st.session_state.staff_df = s_df; st.rerun()

with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password", key="req_side_pw")
    if st.button("更新密碼", key="req_update_pw") and len(new_pw) >= 4:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "password"] = str(new_pw); save_staff(s_df); st.success("成功")

# --- 管理員專屬區塊 (僅管理員可見，非管理員完全隱藏) ---
if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.success("管理員專屬區塊 (已解鎖)")
    
    with st.sidebar.expander("🔑 所有人員密碼清單"):
        st.dataframe(st.session_state.staff_df[["name", "password"]], hide_index=True)
        st.write("**恢復預設密碼 (0000)**")
        reset_target = st.selectbox("選擇人員", st.session_state.staff_df["name"].tolist(), key="req_rst_sel")
        if st.button("確認恢復預設", key="req_rst_btn"):
            s_df = load_staff()
            idx = s_df[s_df["name"] == reset_target].index[0]
            s_df.at[idx, "password"] = "0000"
            save_staff(s_df)
            st.session_state.staff_df = s_df
            st.success(f"{reset_target} 密碼已重置")
            
    with st.sidebar.expander("➕ 新增人員"):
        n = st.text_input("姓名", key="req_new_staff_name")
        if st.button("新增", key="req_add_staff"):
            s_df = load_staff()
            if n and n not in s_df["name"].values:
                new_row = pd.DataFrame([{"name": n, "status": "在職", "password": "0000", "avatar": "", "line_uid": ""}])
                s_df = pd.concat([s_df, new_row], ignore_index=True)
                save_staff(s_df)
                st.session_state.staff_df = s_df
                st.success("人員新增成功")
                st.rerun()
            elif n in s_df["name"].values:
                st.error("人員已存在")

    with st.sidebar.expander("⚙️ 人員設定 (狀態 & LINE ID)"):
        edited_staff = st.data_editor(
            st.session_state.staff_df[["name", "status", "line_uid"]], 
            column_config={
                "name": st.column_config.TextColumn("姓名", disabled=True),
                "status": st.column_config.SelectboxColumn("狀態", options=["在職", "離職"])
            }, 
            hide_index=True, 
            key="req_staff_editor_admin"
        )
        if st.button("💾 儲存人員設定", key="req_save_staff_admin"):
            s_df = load_staff()
            for idx, row in edited_staff.iterrows():
                s_df.at[idx, "status"] = row["status"]
                s_df.at[idx, "line_uid"] = str(row["line_uid"]).strip() if pd.notna(row["line_uid"]) else ""
            save_staff(s_df)
            st.session_state.staff_df = s_df
            st.rerun()

if st.sidebar.button("登出系統", key="req_logout"): st.session_state.user_id = None; st.switch_page("app.py")

# 導覽列移至最下方
menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽", "5. 請款狀態/系統設定"]
menu = st.sidebar.radio("導覽", menu_options, key="req_menu_radio")


# --- 8. 簽核列表渲染模組 ---
def render_signing_table(df_list, sign_type, is_history=False):
    if df_list.empty:
        st.info("目前無相關紀錄")
        return
    
    cols_header = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
    headers = ["單號", "專案名稱", "負責執行長", "申請人", "請款金額", "提交時間", "操作"]
    for c, h in zip(cols_header, headers): c.write(f"**{h}**")
    
    for i, r in df_list.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"])
        c[4].write(f"${clean_amount(r['總金額']):,}"); c[5].write(str(r["提交時間"])[5:16] if pd.notna(r["提交時間"]) else "")
        
        with c[6]:
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            if btn_col1.button("預覽", key=f"sv_{sign_type}_{i}_{is_history}"):
                st.session_state.view_id = r["單號"]; st.rerun()
            
            if not is_history:
                can_sign = (r["專案負責人"] == curr_name if sign_type == "EXE" else curr_name == CFO_NAME) and is_active
                if btn_col2.button("✅ 核准", key=f"sok_{sign_type}_{i}", disabled=not can_sign):
                    fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    if sign_type == "EXE":
                        fresh_db.loc[idx, ["狀態", "初審人", "初審時間"]] = ["待複審", curr_name, get_taiwan_time()]
                        sys_name = st.session_state.get('sys_choice', '請款單系統')
                        send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{r['單號']}\n專案名稱：{r['專案名稱']}\n執行長已核准，有一筆表單需要財務長 ({CFO_NAME}) 進行簽核！")
                    else:
                        fresh_db.loc[idx, ["狀態", "複審人", "複審時間"]] = ["已核准", curr_name, get_taiwan_time()]
                    save_data(fresh_db); st.success("已核准！"); time.sleep(0.5); st.rerun()
                
                if can_sign:
                    with btn_col3.popover("❌ 駁回"):
                        reason = st.text_input("駁回原因", key=f"sr_{sign_type}_{i}")
                        if st.button("確認", key=f"sno_{sign_type}_{i}"):
                            fresh_db = load_data(); idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                            field_prefix = "初審" if sign_type == "EXE" else "複審"
                            fresh_db.loc[idx, ["狀態", "駁回原因", f"{field_prefix}人", f"{field_prefix}時間"]] = ["已駁回", reason, curr_name, get_taiwan_time()]
                            save_data(fresh_db); st.rerun()
                else:
                    btn_col3.button("❌ 駁回", disabled=True, key=f"fk_sno_{sign_type}_{i}")
            else:
                btn_col2.write(f"[{r['狀態']}]")

# ================= 頁面邏輯 =================
if menu == "1. 填寫申請單":
    st.title("時研國際設計股份有限公司")
    st.subheader("📝 填寫請款申請單")
    
    # 頂部即時顯示操作成功訊息
    if st.session_state.get('last_msg'):
        st.success(st.session_state.last_msg)
        st.session_state.last_msg = None

    db = load_data(); staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
    
    dv = {"app": curr_name, "pn": "", "pi": "", "exe": staffs[0], "net_amt": 0, "tax_amt": 0, "desc": "", "ib64": "", "cur": "TWD", "ab64":"", "vdr":"", "acc":"", "pay":"匯款(扣30手續費)", "inv_no":""}
    if st.session_state.edit_id:
        match_r = db[db["單號"]==st.session_state.edit_id]
        if not match_r.empty:
            r = match_r.iloc[0]
            jd = parse_req_json(r["請款說明"])
            legacy_net = clean_amount(r["總金額"]) if jd.get("net_amt", 0) == 0 and jd.get("tax_amt", 0) == 0 else jd.get("net_amt", 0)
            dv.update({"app": r["申請人"], "pn": r["專案名稱"], "pi": r["專案編號"], "exe": r["專案負責人"], "net_amt": legacy_net, "tax_amt": jd.get("tax_amt", 0), "desc": jd.get("desc", ""), "ib64": r["影像Base64"], "cur": r.get("幣別","TWD"), "ab64": r["帳戶影像Base64"], "vdr": r.get("請款廠商",""), "acc": r.get("匯款帳戶",""), "pay": r.get("付款方式","匯款(扣30手續費)"), "inv_no": jd.get("inv_no", "")})

    with st.form("req_form"):
        c1, c2, c3 = st.columns(3)
        app_val = c1.selectbox("申請人", staffs, index=staffs.index(dv["app"]) if dv["app"] in staffs else 0) if curr_name == "Anita" else curr_name
        if curr_name != "Anita": c1.text_input("申請人", value=app_val, disabled=True)
        pn = c2.text_input("專案名稱", value=dv["pn"]); pi = c3.text_input("專案編號", value=dv["pi"])
        cx1, cx2, cx3 = st.columns(3)
        exe = cx1.selectbox("負責執行長", staffs, index=staffs.index(dv["exe"]) if dv["exe"] in staffs else 0)
        net_amt = cx2.number_input("金額 (未稅)", value=int(dv["net_amt"]), min_value=0); tax_amt = cx3.number_input("稅額", value=int(dv["tax_amt"]), min_value=0)
        cv1, cv2, cv3 = st.columns(3)
        vdr = cv1.text_input("請款廠商", value=dv["vdr"]); acc = cv2.text_input("匯款帳戶", value=dv["acc"]); inv_no = cv3.text_input("發票號碼或憑證 (非必填)", value=dv["inv_no"])
        c_cur, c_pay = st.columns([1, 2])
        curr = c_cur.selectbox("幣別", ["TWD", "USD", "EUR"], index=["TWD", "USD", "EUR"].index(dv["cur"]) if dv["cur"] in ["TWD", "USD", "EUR"] else 0)
        pay_idx = ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"].index(dv["pay"]) if dv["pay"] in ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"] else 2
        pay = c_pay.radio("付款方式", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], index=pay_idx, horizontal=True)
        desc = st.text_area("請款說明", value=dv["desc"])
        st.info("💡 **提示：點擊下方「💾 存檔」後，系統會自動加總「金額(未稅) + 稅額」，若選擇「扣30手續費」，總金額會自動扣除 30 元。**")
        f_acc = st.file_uploader("上傳存摺/匯款資料 (圖/Excel)", type=["png", "jpg", "xlsx", "xls"]); f_ims = st.file_uploader("上傳請款憑證 (圖/Excel)", type=["png", "jpg", "xlsx", "xls"], accept_multiple_files=True)
        
        # 5 按鈕操作列
        c_btn1, c_btn2, c_btn3, c_btn4, c_btn5 = st.columns(5)
        btn_save = c_btn1.form_submit_button("💾 存檔", use_container_width=True)
        btn_submit = c_btn2.form_submit_button("🚀 提交", use_container_width=True)
        btn_preview = c_btn3.form_submit_button("🔍 預覽", use_container_width=True)
        btn_print = c_btn4.form_submit_button("🖨️ 列印", use_container_width=True)
        btn_next = c_btn5.form_submit_button("🆕 下一筆申請", use_container_width=True)

        if btn_save or btn_submit or btn_preview or btn_print:
            fee = 30 if "扣30手續費" in pay else 0
            total_amt = net_amt + tax_amt - fee
            if not pn or (net_amt + tax_amt) <= 0:
                st.error("⚠️ 請填寫「專案名稱」且金額須大於 0")
            else:
                b_acc = base64.b64encode(f_acc.getvalue()).decode() if f_acc else dv["ab64"]; b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else dv["ib64"]
                packed_desc = "[請款單資料]\n" + json.dumps({"net_amt": net_amt, "tax_amt": tax_amt, "fee": fee, "inv_no": inv_no, "desc": desc}, ensure_ascii=False)
                f_db = load_data()
                
                # 自動判斷並記錄代申請人
                proxy_app = curr_name if (curr_name == "Anita" and app_val != curr_name) else ""
                
                if st.session_state.edit_id:
                    idx = f_db[f_db["單號"]==st.session_state.edit_id].index[0]
                    f_db.loc[idx, ["申請人", "代申請人", "專案名稱", "專案編號", "專案負責人", "總金額", "請款說明", "請款廠商", "匯款帳戶", "付款方式", "影像Base64", "帳戶影像Base64", "幣別"]] = [app_val, proxy_app, pn, pi, exe, total_amt, packed_desc, vdr, acc, pay, b_ims, b_acc, curr]
                    tid = st.session_state.edit_id
                    msg_prefix = "修改完畢並存檔"
                else:
                    tid = f"{datetime.date.today().strftime('%Y%m%d')}-{len(f_db[f_db['單號'].str.startswith(datetime.date.today().strftime('%Y%m%d'))])+1:02d}"
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"請款單", "申請人":app_val, "代申請人":proxy_app, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":packed_desc, "總金額":total_amt, "幣別":curr, "請款廠商":vdr, "匯款帳戶":acc, "付款方式":pay, "狀態":"已存檔未提交", "影像Base64":b_ims, "帳戶影像Base64":b_acc}
                    f_db = pd.concat([f_db, pd.DataFrame([nr])], ignore_index=True)
                    msg_prefix = "存檔成功"
                
                save_data(f_db)

                if btn_submit:
                    f_db = load_data()
                    idx = f_db[f_db["單號"]==tid].index[0]
                    f_db.loc[idx, ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]
                    save_data(f_db)
                    sys_name = st.session_state.get('sys_choice', '請款單系統')
                    send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{tid}\n專案名稱：{pn}\n有一筆新的表單需要執行長 ({exe}) 進行簽核！")
                    
                    st.session_state.edit_id = None
                    st.session_state.last_msg = f"🚀 單據 {tid} 已成功提交簽核！"
                else:
                    st.session_state.edit_id = tid  # 保持編輯狀態
                    if btn_preview:
                        st.session_state.view_id = tid
                        st.session_state.last_msg = f"📄 單據 {tid} 已{msg_prefix}，正在產生預覽..."
                    elif btn_print:
                        st.session_state.print_id = tid
                        st.session_state.last_msg = f"🖨️ 單據 {tid} 已{msg_prefix}，正在準備列印..."
                    else:
                        st.session_state.last_msg = f"📄 單據 {tid} 已{msg_prefix}！您可以繼續修改或點擊提交。"
                
                st.rerun()

        if btn_next:
            st.session_state.edit_id = None
            st.session_state.last_id = None
            st.session_state.last_msg = None
            st.rerun()

    st.divider(); st.subheader("📋 申請追蹤清單")
    f_db = load_data(); my_db = f_db[f_db["類型"]=="請款單"]
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
    for c, h in zip(cols, ["申請單號", "專案名稱", "負責執行長", "申請人", "請款總金額", "狀態", "操作"]): c.write(f"**{h}**")
    for i, r in my_db.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"]); c[4].write(f"{r.get('幣別','TWD')} ${clean_amount(r['總金額']):,}")
        
        stt = r["狀態"]
        # 新增的「已存檔未提交」也統一顯示藍色
        color = "blue" if stt in ["已儲存", "草稿", "已存檔未提交"] else "orange" if "待" in stt else "green" if stt == "已核准" else "red" if stt == "已駁回" else "gray"
        c[5].markdown(f":{color}[**{stt}**]")
        
        with c[6]:
            b1, b2, b3, b4, b5, b6 = st.columns(6)
            
            # --- 權限判斷：只有本人(申請人) 或 代申請人(Anita) 才能編輯 ---
            is_own = (str(r["申請人"]).strip() == curr_name) or (str(r.get("代申請人", "")).strip() == curr_name)
            # 已將新狀態「已存檔未提交」加入可修改的條件清單
            can_edit = (stt in ["已儲存", "草稿", "已駁回", "已存檔未提交"]) and is_own and is_active
            
            if b1.button("提交", key=f"s{i}", disabled=not can_edit):
                fdb = load_data(); fdb.loc[fdb["單號"]==r["單號"], ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]; save_data(fdb)
                sys_name = st.session_state.get('sys_choice', '請款單系統')
                send_line_message(f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{r['單號']}\n專案名稱：{r['專案名稱']}\n有一筆新的表單需要執行長 ({r['專案負責人']}) 進行簽核！"); st.rerun()
            if b2.button("預覽", key=f"v{i}"): st.session_state.view_id = r["單號"]; st.rerun()
            if b3.button("列印", key=f"p{i}"): st.components.v1.html(f"<script>var w=window.open();w.document.write('{clean_for_js(render_html(r))}');w.print();w.close();</script>", height=0)
            if b4.button("修改", key=f"e{i}", disabled=not can_edit): st.session_state.edit_id = r["單號"]; st.rerun()
            
            if can_edit:
                with b5.popover("刪除"):
                    reason = st.text_input("刪除原因", key=f"d_res_{i}")
                    if st.button("確認", key=f"d{i}"):
                        if reason:
                            fresh_db = load_data(); fresh_db.loc[fresh_db["單號"]==r["單號"], ["狀態", "刪除人", "刪除時間", "刪除原因"]] = ["已刪除", curr_name, get_taiwan_time(), reason]; save_data(fresh_db); st.rerun()
                        else: st.error("請輸入原因")
            else: b5.button("刪除", disabled=True, key=f"fake_d_{i}")
            
            render_upload_popover(b6, r, f"up{i}")

# ================= 頁面 2: 專案執行長簽核 =================
elif menu == "2. 專案執行長簽核":
    st.title("👨‍💼 專案執行長簽核管理")
    f_db = load_data(); req_db = f_db[f_db["類型"]=="請款單"]
    t1, t2 = st.tabs(["⏳ 待簽核清單", "📜 歷史紀錄 (已核准/已駁回)"])
    with t1:
        pending = req_db[req_db["狀態"].isin(["待簽核", "待初審"])]
        if not is_admin: pending = pending[pending["專案負責人"] == curr_name]
        render_signing_table(pending, "EXE")
    with t2:
        history = req_db[(req_db["初審人"] == curr_name) | ((req_db["狀態"].isin(["已核准","已駁回","待複審"])) & (req_db["專案負責人"] == curr_name))]
        if is_admin: history = req_db[req_db["初審人"] != ""]
        render_signing_table(history, "EXE", is_history=True)

# ================= 頁面 3: 財務長簽核 =================
elif menu == "3. 財務長簽核":
    st.title("💰 財務長簽核管理")
    f_db = load_data(); req_db = f_db[f_db["類型"]=="請款單"]
    t1, t2 = st.tabs(["⏳ 待簽核清單", "📜 歷史紀錄 (已核准/已駁回)"])
    with t1:
        pending = req_db[req_db["狀態"] == "待複審"]
        if not is_admin and curr_name != CFO_NAME: pending = pd.DataFrame()
        render_signing_table(pending, "CFO")
    with t2:
        if is_admin:
            history = req_db[req_db["複審人"] != ""]
        elif curr_name == CFO_NAME:
            history = req_db[req_db["複審人"] == curr_name]
        else:
            history = req_db[(req_db["複審人"] != "") & ((req_db["申請人"] == curr_name) | (req_db["專案負責人"] == curr_name))]
        render_signing_table(history, "CFO", is_history=True)

# ================= 頁面 4: 總覽 =================
elif menu == "4. 表單狀態總覽":
    st.subheader("📊 表單狀態總覽")
    f_db = load_data(); my_db = f_db[f_db["類型"]=="請款單"]
    if not is_admin: my_db = my_db[(my_db["申請人"] == curr_name) | (my_db["專案負責人"] == curr_name)]
    st.dataframe(my_db[["單號", "專案名稱", "請款廠商", "總金額", "申請人", "狀態", "付款方式", "匯款狀態", "匯款日期"]], hide_index=True)

# ================= 頁面 5: 系統設定 =================
elif menu == "5. 請款狀態/系統設定":
    st.title("⚙️ 請款狀態 / 系統設定")
    
    if is_admin:
        st.error("⚠️ **雲端暫存機制提醒：** 免費雲端主機重啟會清空資料。請管理員務必在下班前下載備份！")

        with st.expander("💾 1. 表單資料庫備份與還原", expanded=True):
            col_down, col_up = st.columns(2)
            with col_down:
                st.write("⬇️ **步驟一：下載最新表單資料庫**")
                if os.path.exists(D_FILE):
                    with open(D_FILE, "rb") as f: st.download_button("下載表單備份檔", f, file_name=f"時研系統表單備份_{datetime.date.today()}.csv", mime="text/csv")
            with col_up:
                st.write("⬆️ **步驟二：還原表單資料庫**")
                up_db = st.file_uploader("上傳表單 CSV 檔", type=["csv"], key="up_db", label_visibility="collapsed")
                if up_db and st.button("確認還原表單"):
                    with open(D_FILE, "wb") as f: f.write(up_db.getbuffer())
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

        with st.expander("🔔 3. LINE 官方帳號推播設定 (全域 Token & 行政副本 ID)", expanded=True):
            st.write("請填寫從 LINE Developers 取得的兩組關鍵代碼：")
            ct, cu = get_line_credentials()
            nt = st.text_input("Channel Access Token (長字串)", value=ct, type="password")
            nu = st.text_input("行政專屬 User ID (U開頭，用來接收所有副本)", value=cu)
            if st.button("💾 儲存 LINE 設定"): 
                save_line_credentials(nt, nu)
                st.success("LINE 推播設定已成功儲存並啟用！")
                time.sleep(1)
                st.rerun()
        st.divider()

    st.subheader("💰 財務匯款註記")
    f_db = load_data(); df_pay = f_db[f_db["類型"]=="請款單"].copy()
    
    if not is_admin and curr_name != CFO_NAME:
        df_pay = df_pay[(df_pay["申請人"] == curr_name) | (df_pay["專案負責人"] == curr_name)]
    
    if not df_pay.empty:
        df_pay["匯款日期"] = pd.to_datetime(df_pay["匯款日期"], errors='coerce').dt.date
        
        if is_admin:
            ed = st.data_editor(df_pay[["單號", "專案名稱", "請款廠商", "總金額", "匯款狀態", "匯款日期"]], hide_index=True, column_config={"匯款狀態": st.column_config.SelectboxColumn("匯款狀態", options=["尚未匯款", "已匯款"]), "匯款日期": st.column_config.DateColumn("匯款日期", format="YYYY-MM-DD")})
            if st.button("💾 儲存匯款資訊"):
                for _, row in ed.iterrows():
                    f_db.loc[f_db["單號"]==row["單號"], ["匯款狀態", "匯款日期"]] = [row["匯款狀態"], str(row["匯款日期"]) if pd.notna(row["匯款日期"]) else ""]
                save_data(f_db); st.success("已更新"); st.rerun()
        else:
            st.dataframe(df_pay[["單號", "專案名稱", "請款廠商", "總金額", "匯款狀態", "匯款日期"]], hide_index=True)

# ================= 全域預覽/列印模組 =================
if st.session_state.get('print_id'):
    r = load_data(); r = r[r["單號"]==st.session_state.print_id].iloc[0]
    st.components.v1.html(f"<script>var w=window.open();w.document.write('{clean_for_js(render_html(r))}');w.print();w.close();</script>", height=0)
    st.session_state.print_id = None

if st.session_state.view_id:
    st.divider(); r = load_data(); r = r[r["單號"]==st.session_state.view_id].iloc[0]
    if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
    st.markdown(render_html(r), unsafe_allow_html=True)
    
    all_files = []
    if r.get("帳戶影像Base64"): all_files.append(r["帳戶影像Base64"])
    if r.get("影像Base64"): all_files.extend(r["影像Base64"].split('|'))
    
    if all_files:
        st.write("#### 📎 附件內容預覽")
        for f_b64 in all_files:
            # 增加嚴格的防呆機制，若存檔時讀到空字串則自動略過，不報錯
            if not isinstance(f_b64, str) or not f_b64.strip():
                continue
            try:
                raw = base64.b64decode(f_b64)
                if raw.startswith(b'PK\x03\x04') or raw.startswith(b'\xd0\xcf\x11\xe0'):
                    st.info("📊 偵測到 Excel 檔案：")
                    st.dataframe(pd.read_excel(io.BytesIO(raw)), use_container_width=True)
                else:
                    st.image(raw, use_container_width=True)
            except Exception:
                st.warning("此附件格式無法預覽，請確認檔案是否損壞。")
