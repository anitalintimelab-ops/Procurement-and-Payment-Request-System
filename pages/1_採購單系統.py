import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  

# --- 系統鎖定與介面設定 ---
st.session_state['sys_choice'] = "採購單系統"
st.set_page_config(page_title="時研-採購單系統", layout="wide", page_icon="🏢")

st.markdown("""
<style>
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
.stApp { overflow-x: hidden; }
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 路徑設定 ---
B_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

ADMINS = ["Anita"]
CFO_NAME = "Charles"

# --- 工具函式 ---
def get_taiwan_time(): return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return 0
    try: return int(float(str(val).replace(",", "").replace("$", "").replace("，", "").replace(" ", "")))
    except: return 0

def clean_name(val):
    return "" if pd.isna(val) or val is None or str(val).strip() == "" else str(val).strip().split(" ")[0]

def send_line_message(msg):
    if os.path.exists(L_FILE):
        try:
            with open(L_FILE, "r", encoding="utf-8") as f:
                token = f.read().splitlines()[0].strip()
                url = "https://api.line.me/v2/bot/message/broadcast"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
                requests.post(url, headers=headers, json={"messages": [{"type": "text", "text": msg}]}, timeout=5)
        except: pass

def load_data():
    if not os.path.exists(D_FILE): return pd.DataFrame()
    for enc in ['utf-8-sig', 'utf-8', 'cp950']:
        try: 
            df = pd.read_csv(D_FILE, encoding=enc, dtype=str).fillna("")
            for c in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]:
                if c in df.columns: df[c] = df[c].apply(clean_amount)
            if "專案執行人" in df.columns: df = df.rename(columns={"專案執行人": "專案負責人"})
            return df
        except: continue
    return pd.DataFrame()

def save_data(df):
    for c in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]:
        if c in df.columns: df[c] = df[c].apply(clean_amount)
    df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')

def load_staff():
    if not os.path.exists(S_FILE): return pd.DataFrame({"name": ["Anita"], "status": ["在職"]})
    try: return pd.read_csv(S_FILE, encoding='utf-8-sig', dtype=str).fillna("")
    except: return pd.DataFrame({"name": ["Anita"], "status": ["在職"]})

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

def is_pdf(b64_str): return str(b64_str).startswith("JVBERi")

def display_pdf(b64_str, height=600):
    st.markdown(f'<embed src="data:application/pdf;base64,{b64_str}" width="100%" height="{height}px" type="application/pdf">', unsafe_allow_html=True)
    st.download_button("📂 無法預覽？點此下載 PDF", data=base64.b64decode(b64_str), file_name="附件.pdf", mime="application/pdf")

# --- 登入與權限 ---
if st.session_state.get('user_id') is None:
    st.switch_page("app.py")

curr_name = st.session_state.user_id
is_admin = (curr_name in ADMINS)
is_active = True

if 'view_id' not in st.session_state: st.session_state.view_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None

st.sidebar.markdown(f"**📌 目前系統：** `採購單系統`")
st.sidebar.divider()
st.sidebar.markdown(f"### 👤 {curr_name}")

with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password")
    if st.button("更新密碼"):
        s_df = load_staff()
        if not s_df.empty:
            s_df.loc[s_df["name"] == curr_name, "password"] = str(new_pw)
            save_staff(s_df)
            st.success("成功")

if is_admin:
    st.sidebar.success("管理員模式")
    with st.sidebar.expander("🔑 所有人員密碼清單"):
        st.dataframe(load_staff()[["name", "password"]], hide_index=True)

if st.sidebar.button("登出系統"):
    st.session_state.user_id = None
    st.switch_page("app.py")

menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽及轉請款單"]
if is_admin: menu_options.append("5. 系統設定")
menu = st.sidebar.radio("導覽", menu_options)

def get_filtered_db():
    db = load_data()
    if db.empty: return db
    return db[db["類型"] == "採購單"]

# --- 頁面邏輯 ---
if menu == "1. 填寫申請單":
    render_header()
    st.subheader("📝 填寫採購申請單")
    db = load_data()
    staffs = load_staff()["name"].tolist()
    
    dv = {"pn":"", "exe":staffs[0] if staffs else "", "pi":"", "amt":0, "desc":"", "ab64":"", "ib64":""}
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id]
        if not r.empty:
            row = r.iloc[0]
            st.info(f"📝 修改中: {st.session_state.edit_id}")
            dv.update({"pn":row.get("專案名稱",""), "exe":row.get("專案負責人", staffs[0]), "pi":row.get("專案編號",""), "amt":row.get("總金額",0), "desc":row.get("請款說明",""), "ib64":row.get("影像Base64","")})

    with st.form("form"):
        c1, c2 = st.columns(2)
        pn = c1.text_input("專案名稱", value=dv["pn"])
        exe = c1.selectbox("負責執行長", staffs, index=staffs.index(dv["exe"]) if dv["exe"] in staffs else 0)
        pi = c2.text_input("專案編號", value=dv["pi"])
        amt = c2.number_input("預計採購總金額", value=int(dv["amt"]), min_value=0)
        desc = st.text_area("說明", value=dv["desc"])
        
        del_ims = False
        if dv["ib64"]:
            st.write("✅ 已有憑證")
            del_ims = st.checkbox("❌ 刪除所有舊憑證")
        f_ims = st.file_uploader("上傳報價單/憑證 (支援圖/PDF)", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
        
        if st.form_submit_button("💾 儲存"):
            if pn and pi and amt > 0:
                b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else ("" if del_ims else dv["ib64"])
                if st.session_state.edit_id:
                    idx = db[db["單號"]==st.session_state.edit_id].index[0]
                    db.at[idx, "專案名稱"] = pn
                    db.at[idx, "專案負責人"] = exe
                    db.at[idx, "專案編號"] = pi
                    db.at[idx, "總金額"] = amt
                    db.at[idx, "請款說明"] = desc
                    db.at[idx, "影像Base64"] = b_ims
                    st.session_state.edit_id = None
                else:
                    today = datetime.date.today().strftime('%Y%m%d')
                    tid = f"{today}-{len(db[db['單號'].str.startswith(today)])+1:02d}" if not db.empty else f"{today}-01"
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"採購單", "申請人":curr_name, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "總金額":amt, "請款說明":desc, "影像Base64":b_ims, "狀態":"已儲存", "尚未請款金額":amt, "已請款金額":0}
                    db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                    st.session_state.last_id = tid
                save_data(db); st.success("儲存成功"); st.rerun()
            else: st.error("請填寫專案名稱、編號與金額")

    if st.session_state.last_id:
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("🚀 提交審核"):
            fresh_db = load_data()
            idx = fresh_db[fresh_db["單號"]==st.session_state.last_id].index[0]
            fresh_db.at[idx, "狀態"] = "待簽核"
            fresh_db.at[idx, "提交時間"] = get_taiwan_time()
            save_data(fresh_db)
            send_line_message(f"🔔【待簽核】採購單 {st.session_state.last_id} 需要 {fresh_db.at[idx, '專案負責人']} 簽核。")
            st.session_state.last_id = None; st.success("已提交！"); st.rerun()
        if c2.button("🔍 預覽"): st.session_state.view_id = st.session_state.last_id; st.rerun()
        if c3.button("✏️ 修改"): st.session_state.edit_id = st.session_state.last_id; st.session_state.last_id = None; st.rerun()
        if c4.button("🆕 下一筆"): st.session_state.last_id = None; st.rerun()

    st.divider()
    st.subheader("📋 申請追蹤")
    my_db = get_filtered_db()
    if not my_db.empty:
        if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
        for i, r in my_db.iterrows():
            col1, col2, col3, col4, col5 = st.columns([1.5, 2, 1, 1, 3])
            col1.write(r["單號"]); col2.write(r["專案名稱"]); col3.write(f"${clean_amount(r['總金額']):,.0f}"); col4.write(r["狀態"])
            with col5:
                b1, b2, b3 = st.columns(3)
                if b1.button("預覽", key=f"v_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
                can_edit = r["狀態"] in ["已儲存", "已駁回"]
                if b2.button("修改", key=f"e_{i}", disabled=not can_edit): st.session_state.edit_id = r["單號"]; st.rerun()
                if b3.button("刪除", key=f"d_{i}", disabled=not can_edit):
                    fresh_db = load_data(); fresh_db.at[fresh_db[fresh_db["單號"]==r["單號"]].index[0], "狀態"] = "已刪除"
                    save_data(fresh_db); st.rerun()

elif menu == "2. 專案執行長簽核":
    render_header()
    st.subheader("🔍 專案執行長簽核")
    db = get_filtered_db()
    p_df = db[(db["狀態"] == "待簽核") & ((db["專案負責人"] == curr_name) | is_admin)]
    if p_df.empty: st.info("無待簽核單據")
    else:
        for i, r in p_df.iterrows():
            with st.expander(f"{r['單號']} - {r['專案名稱']} (${clean_amount(r['總金額']):,})"):
                st.write(f"申請人: {r['申請人']} | 說明: {r['請款說明']}")
                c1, c2, c3 = st.columns(3)
                if c1.button("✅ 核准", key=f"ok_{i}"):
                    fresh_db = load_data()
                    idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    fresh_db.at[idx, "狀態"] = "已核准"
                    fresh_db.at[idx, "初審人"] = curr_name
                    fresh_db.at[idx, "初審時間"] = get_taiwan_time()
                    save_data(fresh_db)
                    send_line_message(f"🔔 採購單 {r['單號']} 已核准！")
                    st.rerun()
                with c2.popover("❌ 駁回"):
                    reason = st.text_input("駁回原因", key=f"rr_{i}")
                    if st.button("確認駁回", key=f"rb_{i}"):
                        fresh_db = load_data()
                        fresh_db.loc[fresh_db["單號"]==r["單號"], ["狀態", "駁回原因"]] = ["已駁回", reason]
                        save_data(fresh_db); st.rerun()
                if c3.button("🔍 預覽", key=f"view_{i}"): st.session_state.view_id = r["單號"]; st.rerun()

elif menu == "3. 財務長簽核":
    render_header()
    st.subheader("🏁 財務長簽核 (功能保留)")
    db = get_filtered_db()
    p_df = db[(db["狀態"] == "待複審")]
    if p_df.empty: st.info("目前無待複審單據。")
    else: st.dataframe(p_df[["單號", "專案名稱", "總金額", "申請人"]])

elif menu == "4. 表單狀態總覽及轉請款單":
    render_header()
    st.subheader("📊 表單狀態總覽及轉請款單")
    sys_db = get_filtered_db()
    if not is_admin: sys_db = sys_db[sys_db["申請人"] == curr_name]
    
    if not sys_db.empty:
        st.info("💡 勾選左側框並雙擊填寫「本次請款金額」，即可轉為請款單草稿。 (請款金額不得超過尚未請款金額)")
        df = sys_db.copy()
        df.insert(0, "轉成請款單", False)
        df.insert(1, "本次請款金額", 0)
        
        target_cols = ["轉成請款單", "本次請款金額", "單號", "專案名稱", "專案負責人", "申請人", "總金額", "狀態", "已請款金額", "尚未請款金額"]
        edited_df = st.data_editor(
            df[target_cols],
            disabled=["單號", "專案名稱", "專案負責人", "申請人", "總金額", "狀態", "已請款金額", "尚未請款金額"],
            use_container_width=True,
            column_config={
                "轉成請款單": st.column_config.CheckboxColumn("勾選"),
                "本次請款金額": st.column_config.NumberColumn("本次請款金額(點擊輸入)", min_value=0)
            },
            hide_index=True
        )
        
        if st.button("🚀 確認將勾選項目轉成請款單"):
            fresh_db = load_data()
            count = 0
            has_error = False
            for i, row in edited_df.iterrows():
                amt_to_pay = row.get("本次請款金額", 0)
                if row.get("轉成請款單") and amt_to_pay > 0:
                    orig_id = row["單號"]
                    orig_idx = fresh_db[fresh_db["單號"]==orig_id].index[0]
                    orig_r = fresh_db.iloc[orig_idx]
                    
                    unbilled = clean_amount(orig_r.get("尚未請款金額", orig_r["總金額"]))
                    if amt_to_pay > unbilled:
                        st.error(f"❌ {orig_id} 失敗：本次請款金額 ({amt_to_pay:,}) 超過尚未請款金額 ({unbilled:,})！")
                        has_error = True; continue
                    
                    # 扣除餘額
                    fresh_db.at[orig_idx, "已請款金額"] = clean_amount(orig_r.get("已請款金額", 0)) + amt_to_pay
                    fresh_db.at[orig_idx, "尚未請款金額"] = unbilled - amt_to_pay
                    fresh_db.at[orig_idx, "請款狀態"] = "已轉請款單"
                    
                    # 建立請款單草稿
                    today = datetime.date.today().strftime('%Y%m%d')
                    tid = f"{today}-{len(fresh_db[fresh_db['單號'].str.startswith(today)])+1:02d}"
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"請款單", "申請人":"Anita", "專案名稱":orig_r["專案名稱"], "專案負責人":orig_r["專案負責人"], "總金額":amt_to_pay, "請款說明":f"由採購單 {orig_id} 轉換", "狀態":"已儲存"}
                    fresh_db = pd.concat([fresh_db, pd.DataFrame([nr])], ignore_index=True)
                    count += 1
            
            if count > 0:
                save_data(fresh_db)
                st.success(f"✅ 成功轉換 {count} 筆！請至「請款單系統」提交。")
                time.sleep(1.5); st.rerun()
            elif not has_error:
                st.warning("請確保有勾選項目且金額大於 0")
    else: st.info("尚無資料")

elif menu == "5. 系統設定":
    st.subheader("⚙️ 系統設定")
    st.info("系統設定與備份區")

# --- 全域預覽 ---
if st.session_state.view_id:
    st.divider()
    r = load_data()
    r = r[r["單號"]==st.session_state.view_id].iloc[0]
    
    c1, c2 = st.columns([8,2])
    c1.markdown("### 🔍 採購單預覽")
    if c2.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
    
    # 表格資訊
    st.markdown(f"""
    <table border="1" style="width:100%; border-collapse:collapse; text-align:center;">
        <tr><td bgcolor="#eee">單號</td><td>{r['單號']}</td><td bgcolor="#eee">專案</td><td>{r['專案名稱']}</td></tr>
        <tr><td bgcolor="#eee">申請人</td><td>{r['申請人']}</td><td bgcolor="#eee">執行長</td><td>{r['專案負責人']}</td></tr>
        <tr><td bgcolor="#eee">金額</td><td colspan="3">${clean_amount(r['總金額']):,.0f}</td></tr>
        <tr><td bgcolor="#eee">說明</td><td colspan="3">{r['請款說明']}</td></tr>
    </table>
    <br>
    """, unsafe_allow_html=True)
    
    # 附件顯示
    if r.get("影像Base64"):
        st.write("📎 **附件憑證：**")
        for img in r["影像Base64"].split('|'):
            if is_pdf(img): display_pdf(img)
            else: st.image(base64.b64decode(img))
