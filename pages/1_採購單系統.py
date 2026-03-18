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

# --- 4. HTML 渲染 ---
def render_html(row):
    amt = clean_amount(row['總金額'])
    sub_time = str(row.get("提交時間", "")) or get_taiwan_time()
    display_app = f"{row['申請人']} ({row.get('代申請人', '')} 代)" if row.get("代申請人") else row['申請人']
    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;font-family:sans-serif;">'
    h += f'<div style="text-align:center;"><h2>時研國際設計 - 採購申請單</h2></div>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += f'<tr><td bgcolor="#eee" width="25%">單號</td><td>{row["單號"]}</td><td bgcolor="#eee">執行長</td><td>{row["專案負責人"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">專案</td><td>{row["專案名稱"]}</td><td bgcolor="#eee">編號</td><td>{row["專案編號"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">申請人</td><td colspan="3">{display_app}</td></tr>'
    h += f'<tr><td bgcolor="#eee">說明</td><td colspan="3">{row["請款說明"]}</td></tr>'
    h += f'<tr><td colspan="3" align="right"><b>預計採購總金額</b></td><td align="right"><b>{row.get("幣別","TWD")} {amt:,}</b></td></tr></table>'
    h += f'<p style="font-size:11px;margin-top:10px;">提交：{sub_time} | 初審：{row.get("初審人","")} | 複審：{row.get("複審人","")}</p></div>'
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

# --- 5. Session 初始化 ---
if st.session_state.get('user_id') is None: st.switch_page("app.py")
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
for k in ['edit_id', 'last_id', 'view_id']: 
    if k not in st.session_state: st.session_state[k] = None

curr_name, is_admin = st.session_state.user_id, (st.session_state.user_id in ADMINS)
is_active = (st.session_state.user_status == "在職")

# --- 6. 左側側邊欄 (與請款單完全一致的排版) ---
st.sidebar.markdown(f"**📌 目前系統：** `{st.session_state.sys_choice}`")
st.sidebar.divider()

avatar_b64 = ""
try: avatar_b64 = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0].get("avatar", "")
except: pass

if avatar_b64: st.sidebar.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:15px;"><img src="data:image/jpeg;base64,{avatar_b64}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;border:3px solid #eee;"><span style="font-size:22px;font-weight:bold;color:#333;">{curr_name}</span></div>', unsafe_allow_html=True)
else: st.sidebar.markdown(f"### 👤 {curr_name}")

st.sidebar.info(f"🟢 目前在線人數：**{get_online_users(curr_name)}** 人")

with st.sidebar.expander("📸 修改大頭貼"):
    new_avatar = st.file_uploader("上傳圖片", type=["jpg", "png"], key="side_avatar")
    if st.button("更新大頭貼", key="btn_update_avatar") and new_avatar:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "avatar"] = base64.b64encode(new_avatar.getvalue()).decode()
        save_staff(s_df); st.session_state.staff_df = s_df; st.rerun()

with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password", key="side_pw")
    if st.button("更新密碼", key="btn_update_pw") and len(new_pw) >= 4:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "password"] = str(new_pw); save_staff(s_df); st.success("成功")

# --- 管理員專屬區塊 (非管理員完全隱藏) ---
if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.success("管理員專屬區塊 (已解鎖)")
    
    with st.sidebar.expander("🔑 所有人員密碼清單"):
        st.dataframe(st.session_state.staff_df[["name", "password"]], hide_index=True)
        st.write("**恢復預設密碼 (0000)**")
        reset_target = st.selectbox("選擇人員", st.session_state.staff_df["name"].tolist(), key="po_rst_sel")
        if st.button("確認恢復預設", key="po_rst_btn"):
            s_df = load_staff(); idx = s_df[s_df["name"] == reset_target].index[0]
            s_df.at[idx, "password"] = "0000"; save_staff(s_df); st.session_state.staff_df = s_df; st.success("已重置")

    with st.sidebar.expander("➕ 新增人員"):
        n = st.text_input("姓名", key="po_new_staff_name")
        if st.button("新增", key="po_add_staff"):
            s_df = load_staff()
            if n and n not in s_df["name"].values:
                new_row = pd.DataFrame([{"name": n, "status": "在職", "password": "0000", "avatar": "", "line_uid": ""}])
                s_df = pd.concat([s_df, new_row], ignore_index=True); save_staff(s_df); st.session_state.staff_df = s_df; st.success("成功"); st.rerun()

    with st.sidebar.expander("⚙️ 人員設定 (狀態 & LINE ID)"):
        edited_staff = st.data_editor(
            st.session_state.staff_df[["name", "status", "line_uid"]], 
            column_config={"name": st.column_config.TextColumn("姓名", disabled=True), "status": st.column_config.SelectboxColumn("狀態", options=["在職", "離職"])}, 
            hide_index=True, 
            key="po_staff_editor_admin"
        )
        if st.button("💾 儲存人員設定", key="po_save_staff_admin"):
            s_df = load_staff()
            for idx, row in edited_staff.iterrows(): s_df.at[idx, "status"] = row["status"]; s_df.at[idx, "line_uid"] = str(row["line_uid"]).strip() if pd.notna(row["line_uid"]) else ""
            save_staff(s_df); st.session_state.staff_df = s_df; st.rerun()

if st.sidebar.button("登出系統", key="po_logout"): st.session_state.user_id = None; st.switch_page("app.py")

# 動態產生導覽列 (非管理員看不到系統設定)
menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽"]
if is_admin:
    menu_options.append("5. 系統設定")
menu = st.sidebar.radio("導覽", menu_options, key="po_menu_radio")


# --- 8. 簽核列表渲染模組 (採購單專用) ---
def render_signing_table(df_list, sign_type, is_history=False):
    if df_list.empty:
        st.info("目前無相關紀錄")
        return
    
    cols_header = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
    headers = ["單號", "專案名稱", "負責執行長", "申請人", "預計採購金額", "提交時間", "操作"]
    for c, h in zip(cols_header, headers): c.write(f"**{h}**")
    
    for i, r in df_list.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.0])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"])
        c[4].write(f"{r.get('幣別','TWD')} ${clean_amount(r['總金額']):,}"); c[5].write(str(r["提交時間"])[5:16] if pd.notna(r["提交時間"]) else "")
        
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
                        sys_name = st.session_state.get('sys_choice', '採購單系統')
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
    st.subheader("📝 填寫採購申請單")
    db = load_data(); staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
    
    dv = {"app": curr_name, "pn": "", "pi": "", "exe": staffs[0], "amt": 0, "desc": "", "ib64": "", "cur": "TWD", "ab64":""}
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id].iloc[0]
        dv.update({"app": r["申請人"], "pn": r["專案名稱"], "pi": r["專案編號"], "exe": r["專案負責人"], "amt": r["總金額"], "desc": r["請款說明"], "ib64": r["影像Base64"], "cur": r.get("幣別","TWD"), "ab64": r["帳戶影像Base64"]})

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
        f_acc = st.file_uploader("上傳存摺 (圖/Excel)", type=["png", "jpg", "xlsx", "xls"])
        f_ims = st.file_uploader("上傳憑證 (圖/Excel)", type=["png", "jpg", "xlsx", "xls"], accept_multiple_files=True)
        
        if st.form_submit_button("💾 儲存並進入提交模式"):
            if pn and amt > 0:
                b_acc = base64.b64encode(f_acc.getvalue()).decode() if f_acc else dv["ab64"]
                b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else dv["ib64"]
                f_db = load_data()
                if st.session_state.edit_id:
                    idx = f_db[f_db["單號"]==st.session_state.edit_id].index[0]
                    f_db.loc[idx, ["申請人", "專案名稱", "專案編號", "專案負責人", "總金額", "請款說明", "影像Base64", "帳戶影像Base64", "幣別"]] = [app_val, pn, pi, exe, amt, desc, b_ims, b_acc, curr]
                    st.session_state.edit_id = None
                else:
                    tid = f"{datetime.date.today().strftime('%Y%m%d')}-{len(f_db[f_db['單號'].str.startswith(datetime.date.today().strftime('%Y%m%d'))])+1:02d}"
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"採購單", "申請人":app_val, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":desc, "總金額":amt, "幣別":curr, "狀態":"已儲存", "影像Base64":b_ims, "帳戶影像Base64":b_acc}
                    f_db = pd.concat([f_db, pd.DataFrame([nr])], ignore_index=True); st.session_state.last_id = tid
                save_data(f_db); st.success("儲存成功！"); st.rerun()

    if st.session_state.last_id:
        c1, c2, c3 = st.columns(3)
        if c1.button("🚀 提交審核"):
            f_db = load_data()
            idx = f_db[f_db["單號"]==st.session_state.last_id].index[0]
            f_db.loc[idx, ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]
            save_data(f_db)
            
            sys_name = st.session_state.get('sys_choice', '採購單系統')
            pj_name = f_db.at[idx, '專案名稱']
            exe_name = f_db.at[idx, '專案負責人']
            msg = f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{st.session_state.last_id}\n專案名稱：{pj_name}\n有一筆新的表單需要執行長 ({exe_name}) 進行簽核！"
            send_line_message(msg)
            
            st.session_state.last_id = None; st.rerun()
        if c2.button("🔍 預覽單據"): st.session_state.view_id = st.session_state.last_id; st.rerun()
        if c3.button("🆕 下一筆"): st.session_state.last_id = None; st.rerun()

    st.divider(); st.subheader("📋 申請追蹤清單")
    f_db = load_data(); my_db = f_db[f_db["類型"]=="採購單"]
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    
    cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
    for c, h in zip(cols, ["申請單號", "專案名稱", "負責執行長", "申請人", "預計採購金額", "狀態", "操作"]): 
        c.write(f"**{h}**")
        
    for i, r in my_db.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"])
        c[4].write(f"{r.get('幣別','TWD')} ${clean_amount(r['總金額']):,}")
        
        stt = r["狀態"]
        color = "blue" if stt in ["已儲存", "草稿"] else "orange" if "待" in stt else "green" if stt == "已核准" else "red" if stt == "已駁回" else "gray"
        c[5].markdown(f":{color}[**{stt}**]")
        
        with c[6]:
            b1, b2, b3, b4, b5, b6 = st.columns(6)
            is_own = (str(r["申請人"]).strip() == curr_name) or (str(r.get("代申請人", "")).strip() == curr_name)
            can_edit = (stt in ["已儲存", "草稿", "已駁回"]) and is_own and is_active
            
            if b1.button("提交", key=f"s{i}", disabled=not can_edit):
                fdb = load_data()
                fdb.loc[fdb["單號"]==r["單號"], ["狀態", "提交時間"]] = ["待簽核", get_taiwan_time()]
                save_data(fdb)
                
                sys_name = st.session_state.get('sys_choice', '採購單系統')
                msg = f"🔔【待簽核提醒】\n系統：{sys_name}\n單號：{r['單號']}\n專案名稱：{r['專案名稱']}\n有一筆新的表單需要執行長 ({r['專案負責人']}) 進行簽核！"
                send_line_message(msg)
                
                st.rerun()
            if b2.button("預覽", key=f"v{i}"): 
                st.session_state.view_id = r["單號"]; st.rerun()
            if b3.button("列印", key=f"p{i}"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write('{clean_for_js(render_html(r))}');w.print();w.close();</script>", height=0)
            if b4.button("修改", key=f"e{i}", disabled=not can_edit): 
                st.session_state.edit_id = r["單號"]; st.rerun()
                
            if stt == "已核准" and is_active:
                with b5.popover("📝 更新"):
                    st.write("**採購單後續更新**")
                    new_bill_stat = st.text_input("請款狀態", value=str(r.get("請款狀態", "")), key=f"m1_bs_{i}")
                    new_billed = st.number_input("已請款金額", value=int(clean_amount(r.get("已請款金額", 0))), min_value=0, key=f"m1_ba_{i}")
                    new_unbilled = st.number_input("尚未請款金額", value=int(clean_amount(r.get("尚未請款金額", 0))), min_value=0, key=f"m1_ua_{i}")
                    new_desc = st.text_area("說明內容", value=str(r.get("請款說明", "")), key=f"m1_desc_{i}")
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

            render_upload_popover(b6, r, f"up{i}")

# ================= 頁面 2: 專案執行長簽核 =================
elif menu == "2. 專案執行長簽核":
    st.title("👨‍💼 專案執行長簽核管理")
    f_db = load_data()
    req_db = f_db[f_db["類型"]=="採購單"]
    
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
    f_db = load_data()
    req_db = f_db[f_db["類型"]=="採購單"]
    
    t1, t2 = st.tabs(["⏳ 待簽核清單", "📜 歷史紀錄 (已核准/已駁回)"])
    
    with t1:
        pending = req_db[req_db["狀態"] == "待複審"]
        if not is_admin and curr_name != CFO_NAME: pending = pd.DataFrame()
        render_signing_table(pending, "CFO")
        
    with t2:
        history = req_db[req_db["複審人"] == curr_name] if curr_name == CFO_NAME else pd.DataFrame()
        if is_admin: history = req_db[req_db["複審人"] != ""]
        render_signing_table(history, "CFO", is_history=True)

# ================= 頁面 4: 總覽 =================
elif menu == "4. 表單狀態總覽":
    st.subheader("📊 表單狀態總覽")
    f_db = load_data(); my_db = f_db[f_db["類型"]=="採購單"]
    st.dataframe(my_db[["單號", "專案名稱", "總金額", "申請人", "狀態", "已請款金額", "尚未請款金額"]], hide_index=True)

# ================= 頁面 5: 系統設定 =================
elif menu == "5. 系統設定":
    st.title("⚙️ 系統設定")
    with st.expander("💾 1. 資料庫管理", expanded=True):
        if os.path.exists(D_FILE):
            with open(D_FILE, "rb") as f: st.download_button("⬇️ 下載資料庫", f, file_name="database.csv")
        up = st.file_uploader("⬆️ 還原資料庫", type=["csv"])
        if up and st.button("確認還原"):
            with open(D_FILE, "wb") as f: f.write(up.getbuffer())
            st.success("還原成功！"); time.sleep(1); st.rerun()
            
    with st.expander("👥 2. 人員備份與還原", expanded=True):
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

# ================= 全域預覽模組 (支援 Excel 解析) =================
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
            try:
                raw = base64.b64decode(f_b64)
                if raw.startswith(b'PK\x03\x04') or raw.startswith(b'\xd0\xcf\x11\xe0'):
                    st.info("📊 偵測到 Excel 檔案：")
                    df_preview = pd.read_excel(io.BytesIO(raw))
                    st.dataframe(df_preview, use_container_width=True)
                else:
                    st.image(raw, use_container_width=True)
            except: st.warning("此附件格式無法預覽，請確認檔案是否損壞。")
