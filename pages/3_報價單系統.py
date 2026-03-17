import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  
import json

# --- 系統鎖定與介面設定 ---
st.session_state['sys_choice'] = "報價單系統"
st.set_page_config(page_title="時研-報價單系統", layout="wide", page_icon="🏢")

st.markdown("""
<style>
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
.stApp { overflow-x: hidden; }
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
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

# --- [資料預設] 依照上傳檔案製作的細項下拉清單資料庫 ---
QUOTE_ITEMS_DB = {
    "保護工程": {"unit": "式", "price": 245000, "spec": "室內地坪三層保護(防潮布+瓦楞板+夾板)"},
    "拆除工程": {"unit": "式", "price": 22000, "spec": "原廚房與主浴輕隔間拆除清運"},
    "放樣工程": {"unit": "式", "price": 10000, "spec": "現場水平放樣工程"},
    "大樓清潔費": {"unit": "天", "price": 200, "spec": "管理員代收大樓清潔管理費"},
    "水電工程": {"unit": "式", "price": 150000, "spec": "全室開關插座與迴路更新"},
    "木作裝修": {"unit": "式", "price": 300000, "spec": "天花板平釘與造型木作"},
    "油漆裝修": {"unit": "式", "price": 120000, "spec": "全室水泥漆/乳膠漆粉刷"},
    "清潔工程": {"unit": "式", "price": 55000, "spec": "施工中粗清與竣工細清"},
    "追加水泥板": {"unit": "式", "price": 28000, "spec": "牆面局部追加水泥板裝飾"},
    "其他自填": {"unit": "式", "price": 0, "spec": "手動輸入規格內容"}
}

# --- 基礎工具 ---
def get_taiwan_time(): 
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return 0
    try: return int(float(str(val).replace(",", "").replace("$", "").replace("，", "").replace(" ", "")))
    except Exception: return 0

def clean_name(val): 
    if pd.isna(val) or val is None or str(val).strip() == "": return ""
    return str(val).strip().split(" ")[0]

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
    except Exception: return 1

def get_line_credentials():
    if os.path.exists(L_FILE):
        try:
            with open(L_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                return lines[0].strip(), lines[1].strip()
        except Exception: pass
    return "", ""

def send_line_message(msg):
    token, _ = get_line_credentials()
    if token:
        try: requests.post("https://api.line.me/v2/bot/message/broadcast", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, json={"messages": [{"type": "text", "text": msg}]}, timeout=5)
        except Exception: pass

def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try: return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except Exception: continue
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
    df["狀態"] = df["狀態"].astype(str).str.strip()
    return df[cols]

def save_data(df):
    try:
        for col in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]: df[col] = df[col].apply(clean_amount)
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError: st.error("⚠️ 警告：無法寫入檔案！請關閉 Excel。"); st.stop()

def load_staff():
    df = read_csv_robust(S_FILE)
    if df is None or df.empty: return pd.DataFrame({"name": DEFAULT_STAFF, "status": ["在職"]*5, "password": ["0000"]*5, "avatar": [""], "line_uid": [""]})
    return df

def save_staff(df): df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            if any(x in f.lower() for x in ["logo", "timelab"]) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                with open(os.path.join(B_DIR, f), "rb") as img: return base64.b64encode(img.read()).decode()
    except Exception: pass
    return ""

def render_header():
    logo_b64 = get_b64_logo()
    if logo_b64: st.markdown(f'<div style="display:flex;align-items:center;justify-content:center;gap:15px;margin-bottom:20px;flex-wrap:wrap;"><img src="data:image/png;base64,{logo_b64}" style="height:60px;max-width:100%;"><h2 style="margin:0;color:#333;text-align:center;">時研國際設計股份有限公司</h2></div>', unsafe_allow_html=True)
    else: st.title("時研國際設計股份有限公司")
    st.divider()

def parse_quote_json(desc_raw):
    try:
        if "[報價單資料]" in desc_raw:
            return json.loads(desc_raw.split("[報價單資料]")[1].strip())
    except: pass
    return {"c_name": "", "c_phone": "", "tax_id": "", "address": "", "desc": "", "items": []}

# --- Session 初始化 ---
if st.session_state.get('user_id') is None: st.switch_page("app.py")
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
for key in ['edit_id', 'last_id', 'view_id']:
    if key not in st.session_state: st.session_state[key] = None
if 'form_key' not in st.session_state: st.session_state.form_key = 0 

curr_name, is_active, is_admin = st.session_state.user_id, (st.session_state.user_status == "在職"), (st.session_state.user_id in ADMINS)

# --- 側邊欄 ---
st.sidebar.markdown(f"**📌 目前系統：** `{st.session_state.sys_choice}`")
st.sidebar.divider()

avatar_b64 = ""
try: avatar_b64 = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0].get("avatar", "")
except: pass

if avatar_b64: st.sidebar.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:15px;"><img src="data:image/jpeg;base64,{avatar_b64}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;border:3px solid #eee;"><span style="font-size:22px;font-weight:bold;color:#333;">{curr_name}</span></div>', unsafe_allow_html=True)
else: st.sidebar.markdown(f"### 👤 {curr_name}")

st.sidebar.info(f"🟢 目前在線人數：**{get_online_users(curr_name)}** 人")

with st.sidebar.expander("📸 修改大頭貼"):
    new_avatar = st.file_uploader("上傳圖片", type=["jpg", "jpeg", "png"])
    if st.button("更新大頭貼") and new_avatar:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "avatar"] = base64.b64encode(new_avatar.getvalue()).decode()
        save_staff(s_df); st.session_state.staff_df = s_df; st.success("成功"); time.sleep(0.5); st.rerun()

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
        if st.button("💾 儲存人員設定"):
            save_staff(edited_staff); st.success("成功"); time.sleep(0.5); st.rerun()

if st.sidebar.button("登出"):
    st.session_state.user_id = None; st.switch_page("app.py")

# --- 導覽選單 ---
menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽及轉採購單", "5. 請款狀態/系統設定"]
menu = st.sidebar.radio("導覽", menu_options, key="menu_radio")

def get_filtered_db(): return load_data()[load_data()["類型"] == "報價單"]

# --- HTML 報價單渲染 (專業工程格式) ---
def render_html(row):
    data = parse_quote_json(row.get("請款說明", ""))
    logo_b64 = get_b64_logo()
    lg_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:50px;">' if logo_b64 else ''
    
    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;font-family:sans-serif;">'
    h += f'<div style="text-align:center;">{lg_html}<h2>時研國際設計股份有限公司</h2><h3>工程報價單</h3></div>'
    h += f'<p>客戶名稱：{data.get("c_name")} &nbsp;&nbsp; 報價單號：{row["單號"]}<br>客戶電話：{data.get("c_phone")} &nbsp;&nbsp; 專案名稱：{row["專案名稱"]}<br>統一編號：{data.get("tax_id")} &nbsp;&nbsp; 施工地址：{data.get("address")}</p>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:13px;text-align:center;" border="1">'
    h += '<tr bgcolor="#eee"><th>品名與規格</th><th>數量</th><th>單位</th><th>單價</th><th>複價</th></tr>'
    
    for item in data.get("items", []):
        qty, price = clean_amount(item.get("qty")), clean_amount(item.get("price"))
        h += f'<tr><td align="left">{item.get("name")} ({item.get("spec")})</td><td>{qty}</td><td>{item.get("unit")}</td><td align="right">{price:,}</td><td align="right">{qty*price:,}</td></tr>'
    
    h += f'<tr><td colspan="4" align="right"><b>總計金額 (TWD)</b></td><td align="right"><b>{clean_amount(row["總金額"]):,}</b></td></tr></table>'
    h += f'<p>備註說明：{data.get("desc")}</p>'
    h += f'<p style="font-size:11px;">填單人：{row["申請人"]} &nbsp;&nbsp; 日期：{row["日期"]}</p></div>'
    return h

# ================= 頁面邏輯 =================
if menu == "1. 填寫申請單":
    render_header()
    st.subheader("📝 填寫工程報價單")
    db = load_data(); staffs = st.session_state.staff_df["name"].tolist()
    
    init_data = parse_quote_json("")
    init_pn, init_exe, init_pi = "", staffs[0], ""
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id].iloc[0]
        init_data = parse_quote_json(r["請款說明"])
        init_pn, init_exe, init_pi = r["專案名稱"], r["專案負責人"], r["專案編號"]

    with st.form("quote_form"):
        c1, c2 = st.columns(2)
        pn = c1.text_input("專案名稱", value=init_pn)
        exe = c1.selectbox("負責執行長", staffs, index=staffs.index(init_exe) if init_exe in staffs else 0)
        pi = c2.text_input("專案編號", value=init_pi)
        
        st.markdown("---")
        cx1, cx2 = st.columns(2)
        c_name = cx1.text_input("客戶名稱", value=init_data["c_name"])
        c_phone = cx2.text_input("客戶電話", value=init_data["c_phone"])
        tax_id = cx1.text_input("統一編號", value=init_data["tax_id"])
        address = cx2.text_input("施工地址", value=init_data["address"])
        
        st.write("**📐 工程細項編輯 (點擊下拉選單選擇品名)**")
        # 建立預設細項表格
        items_df = pd.DataFrame(init_data["items"] if init_data["items"] else [{"name":"保護工程", "spec":"", "unit":"式", "qty":1, "price":0}])
        
        # 使用 data_editor 並加上下拉選單
        item_names = list(QUOTE_ITEMS_DB.keys())
        edited_items = st.data_editor(items_df, num_rows="dynamic", use_container_width=True, column_config={
            "name": st.column_config.SelectboxColumn("品名工程項目", options=item_names, required=True),
            "spec": "規格描述",
            "unit": "單位",
            "qty": st.column_config.NumberColumn("數量", min_value=0, format="%d"),
            "price": st.column_config.NumberColumn("單價", min_value=0)
        })
        
        # [自動填充邏輯] 這裡在後端處理，若使用者沒填，則抓取預設值
        for idx, row in edited_items.iterrows():
            if row['name'] in QUOTE_ITEMS_DB:
                if not row['spec']: edited_items.at[idx, 'spec'] = QUOTE_ITEMS_DB[row['name']]['spec']
                if not row['unit']: edited_items.at[idx, 'unit'] = QUOTE_ITEMS_DB[row['name']]['unit']
                if row['price'] == 0: edited_items.at[idx, 'price'] = QUOTE_ITEMS_DB[row['name']]['price']

        desc = st.text_area("備註說明", value=init_data["desc"])
        
        if st.form_submit_button("💾 儲存並計算總額"):
            if pn and c_name:
                total = sum(clean_amount(r["qty"]) * clean_amount(r["price"]) for _, r in edited_items.iterrows())
                packed = "[報價單資料]\n" + json.dumps({
                    "c_name": c_name, "c_phone": c_phone, "tax_id": tax_id, "address": address, "desc": desc,
                    "items": edited_items.to_dict('records')
                }, ensure_ascii=False)
                
                if st.session_state.edit_id:
                    idx = db[db["單號"]==st.session_state.edit_id].index[0]
                    db.loc[idx, ["專案名稱", "專案負責人", "專案編號", "請款說明", "總金額", "尚未請款金額"]] = [pn, exe, pi, packed, total, total]
                    st.session_state.edit_id = None
                else:
                    tid = f"Q{datetime.date.today().strftime('%Y%m%d')}-{len(db[db['單號'].str.startswith('Q')])+1:02d}"
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"報價單", "申請人":curr_name, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":packed, "總金額":total, "狀態":"已儲存", "尚未請款金額":total, "已請款金額":0}
                    db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                    st.session_state.last_id = tid
                save_data(db); st.success(f"儲存成功！總金額：${total:,}"); st.rerun()

    if st.session_state.last_id:
        c1, c2, c3 = st.columns(3)
        if c1.button("🚀 提交審核 (直接核准)"):
            fdb = load_data(); idx = fdb[fdb["單號"]==st.session_state.last_id].index[0]
            fdb.at[idx, "狀態"] = "已核准"; save_data(fdb); st.session_state.last_id = None; st.success("已完成"); st.rerun()
        if c2.button("🔍 線上預覽"): st.session_state.view_id = st.session_state.last_id; st.rerun()
        if c3.button("🆕 下一筆"): st.session_state.last_id = None; st.rerun()

    st.divider(); st.subheader("📋 報價追蹤清單")
    my_db = get_filtered_db()
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    for i, r in my_db.iterrows():
        c1, c2, c3, c4, c5 = st.columns([1.5, 2, 1, 1, 3])
        c1.write(r["單號"]); c2.write(r["專案名稱"]); c3.write(f"${clean_amount(r['總金額']):,}"); c4.write(r["狀態"])
        with c5:
            b1, b2, b3 = st.columns(3)
            if b1.button("預覽", key=f"v_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
            if b2.button("修改", key=f"e_{i}"): st.session_state.edit_id = r["單號"]; st.rerun()
            if b3.button("刪除", key=f"d_{i}"):
                fdb = load_data(); fdb.at[fdb[fdb["單號"]==r["單號"]].index[0], "狀態"] = "已刪除"; save_data(fdb); st.rerun()

elif menu == "2. 專案執行長簽核":
    render_header(); st.info("報價單預設免簽核。此區供查閱已提交項目。")

elif menu == "4. 表單狀態總覽及轉採購單":
    render_header()
    st.subheader("📊 表單狀態總覽及轉採購單")
    sys_db = get_filtered_db()
    if not sys_db.empty:
        st.info("💡 勾選左側框並填寫【本次轉採購金額】，點擊執行後系統將自動生成採購單草稿。")
        df = sys_db.copy(); df.insert(0, "轉成採購單", False); df.insert(1, "本次轉採購金額", 0)
        target_cols = ["轉成採購單", "本次轉採購金額", "單號", "專案名稱", "專案負責人", "申請人", "總金額", "狀態", "已請款金額", "尚未請款金額"]
        edited = st.data_editor(df[target_cols], disabled=["單號","專案名稱","總金額","狀態","已請款金額","尚未請款金額"], hide_index=True, use_container_width=True, column_config={"轉成採購單": st.column_config.CheckboxColumn("勾選轉換"), "本次轉採購金額": st.column_config.NumberColumn("金額 (雙擊輸入)", min_value=0)})
        
        if st.button("🚀 執行轉換 (產生採購單草稿)"):
            fdb = load_data(); count = 0
            for i, row in edited.iterrows():
                amt = row["本次轉採購金額"]
                if row["轉成採購單"] and amt > 0:
                    orig_idx = fdb[fdb["單號"]==row["單號"]].index[0]
                    remain = clean_amount(fdb.at[orig_idx, "尚未請款金額"])
                    if amt > remain: st.error(f"❌ {row['單號']} 失敗：金額超過剩餘報價餘額！"); continue
                    
                    fdb.at[orig_idx, "已請款金額"] += amt
                    fdb.at[orig_idx, "尚未請款金額"] -= amt
                    # 產生新採購單號
                    new_id = f"PO-FROM-{row['單號']}-{int(time.time())%1000}"
                    nr = {"單號":new_id, "日期":str(datetime.date.today()), "類型":"採購單", "申請人":curr_name, "專案名稱":row["專案名稱"], "專案負責人":fdb.at[orig_idx, '專案負責人'], "總金額":amt, "狀態":"已儲存", "請款說明":f"由報價單 {row['單號']} 轉換生成"}
                    fdb = pd.concat([fdb, pd.DataFrame([nr])], ignore_index=True); count += 1
            if count > 0: save_data(fdb); st.success(f"✅ 成功轉換 {count} 筆！請至採購單系統處理發包。"); st.rerun()

elif menu == "5. 請款狀態/系統設定":
    render_header()
    st.subheader("⚙️ 系統設定 (與各系統同步)")
    col1, col2 = st.columns(2)
    with col1:
        if os.path.exists(D_FILE):
            with open(D_FILE, "rb") as f: st.download_button("⬇️ 下載資料庫備份", f, file_name="時研系統備份.csv")
    with col2:
        up = st.file_uploader("⬆️ 還原資料庫", type=["csv"])
        if up and st.button("確認還原"):
            with open(D_FILE, "wb") as f: f.write(up.getbuffer())
            st.success("還原成功！"); st.rerun()

# --- 全域預覽 ---
if st.session_state.view_id:
    st.divider(); r = load_data(); r = r[r["單號"]==st.session_state.view_id].iloc[0]
    if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
    st.markdown(render_html(r), unsafe_allow_html=True)
