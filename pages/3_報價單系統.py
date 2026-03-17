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

# --- [資料庫] 依照上傳檔案提取的工程、細項、單位資料 ---
# 包含：假設工程, 泥作與防水工程, 木作裝修工程, 塗裝裝修工程, 水電弱電工程, 清潔工程等
QUOTE_ENGINEERING_DB = {
    "假設工程": [
        {"name": "保護工程", "unit": "式", "price": 245000, "spec": "依管委會標準"},
        {"name": "原廚房與主浴輕隔間拆除清運", "unit": "式", "price": 22000, "spec": "原隔間拆除"},
        {"name": "放樣工程", "unit": "式", "price": 10000, "spec": "現場放樣"}
    ],
    "泥作與防水工程": [
        {"name": "玄關花磚", "unit": "片", "price": 550, "spec": "進口花磚"},
        {"name": "浴室壁磚/地磚鋪設", "unit": "坪", "price": 8500, "spec": "含水泥沙料"},
        {"name": "全室地面找平工程", "unit": "坪", "price": 2500, "spec": "厚度3-5cm"},
        {"name": "防水工程(三道施作)", "unit": "式", "price": 35000, "spec": "浴室專用"}
    ],
    "木作裝修工程": [
        {"name": "天花板平釘", "unit": "坪", "price": 3800, "spec": "矽酸鈣板"},
        {"name": "造型木作電視牆", "unit": "式", "price": 65000, "spec": "含底板結構"},
        {"name": "更衣室拉門", "unit": "才", "price": 950, "spec": "木工訂製"}
    ],
    "塗裝裝修工程": [
        {"name": "全室乳膠漆粉刷", "unit": "坪", "price": 1200, "spec": "得利乳膠漆"},
        {"name": "木作表面噴漆", "unit": "式", "price": 45000, "spec": "白色冷烤漆"}
    ],
    "清潔工程": [
        {"name": "施工中粗清", "unit": "式", "price": 55000, "spec": "廢棄物搬運"},
        {"name": "竣工後細清", "unit": "式", "price": 120000, "spec": "全室除塵窗溝"}
    ],
    "其他工程": [
        {"name": "現場代辦費", "unit": "式", "price": 0, "spec": "其他雜項"}
    ]
}

ALL_UNITS = ["式", "片", "坪", "才", "個", "組", "天", "米", "尺", "工", "台", "處", "車", "迴", "開", "包", "樘", "盞"]

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
    except PermissionError: st.error("⚠️ 無法寫入檔案！"); st.stop()

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
if 'quote_items' not in st.session_state: st.session_state.quote_items = []

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

# --- HTML 報價單渲染 ---
def render_html(row):
    data = parse_quote_json(row.get("請款說明", ""))
    logo_b64 = get_b64_logo()
    lg_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:50px;">' if logo_b64 else ''
    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;font-family:sans-serif;">'
    h += f'<div style="text-align:center;">{lg_html}<h2>工程報價單</h2></div>'
    h += f'<p>客戶名稱：{data.get("c_name")} &nbsp;&nbsp; 報價單號：{row["單號"]}<br>專案名稱：{row["專案名稱"]}<br>施工地址：{data.get("address")}</p>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:13px;text-align:center;" border="1">'
    h += '<tr bgcolor="#eee"><th>工程類別</th><th>品名與規格</th><th>數量</th><th>單位</th><th>單價</th><th>複價</th></tr>'
    for item in data.get("items", []):
        qty, price = clean_amount(item.get("qty")), clean_amount(item.get("price"))
        h += f'<tr><td>{item.get("eng")}</td><td align="left">{item.get("name")}</td><td>{qty}</td><td>{item.get("unit")}</td><td align="right">{price:,}</td><td align="right">{qty*price:,}</td></tr>'
    h += f'<tr><td colspan="5" align="right"><b>總計金額 (TWD)</b></td><td align="right"><b>{clean_amount(row["總金額"]):,}</b></td></tr></table>'
    h += f'<p>備註：{data.get("desc")}</p></div>'
    return h

# ================= 頁面邏輯 =================
if menu == "1. 填寫申請單":
    render_header()
    st.subheader("📝 填寫工程報價單")
    db = load_data(); staffs = st.session_state.staff_df["name"].tolist()
    
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id].iloc[0]
        init_data = parse_quote_json(r["請款說明"])
        st.session_state.quote_items = init_data.get("items", [])
    
    with st.expander("👤 1. 基本資料輸入", expanded=True):
        cx1, cx2 = st.columns(2)
        pn = cx1.text_input("專案名稱")
        c_name = cx2.text_input("客戶名稱")
        address = st.text_input("施工地址")

    with st.expander("📐 2. 報價細項編輯 (下拉選單)", expanded=True):
        st.write("請從下方選單選取工程類別與品名：")
        sc1, sc2, sc3 = st.columns([1, 1.5, 1])
        sel_eng = sc1.selectbox("工程類別", list(QUOTE_ENGINEERING_DB.keys()))
        
        # 根據工程類別過濾品名
        item_options = [i['name'] for i in QUOTE_ENGINEERING_DB[sel_eng]]
        sel_item_name = sc2.selectbox("品名與規格", item_options)
        
        # 抓取預設資料
        default_info = next(i for i in QUOTE_ENGINEERING_DB[sel_eng] if i['name'] == sel_item_name)
        
        sc4, sc5, sc6 = st.columns([1, 1, 1])
        sel_unit = sc4.selectbox("單位", ALL_UNITS, index=ALL_UNITS.index(default_info['unit']) if default_info['unit'] in ALL_UNITS else 0)
        sel_qty = sc5.number_input("數量", min_value=1, value=1)
        sel_price = sc6.number_input("單價", min_value=0, value=default_info['price'])
        
        if st.button("➕ 新增至清單"):
            st.session_state.quote_items.append({
                "eng": sel_eng, "name": sel_item_name, "unit": sel_unit, "qty": sel_qty, "price": sel_price
            })
            st.rerun()

    if st.session_state.quote_items:
        st.write("**📋 目前已加入細項**")
        temp_df = pd.DataFrame(st.session_state.quote_items)
        st.table(temp_df)
        if st.button("🗑️ 清空所有細項"):
            st.session_state.quote_items = []; st.rerun()

    if st.button("💾 儲存並產生報價單", type="primary"):
        if pn and c_name and st.session_state.quote_items:
            total = sum(i['qty'] * i['price'] for i in st.session_state.quote_items)
            packed = "[報價單資料]\n" + json.dumps({"c_name": c_name, "address": address, "items": st.session_state.quote_items}, ensure_ascii=False)
            tid = f"Q{datetime.date.today().strftime('%Y%m%d')}-{len(db[db['單號'].str.startswith('Q')])+1:02d}"
            nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"報價單", "申請人":curr_name, "專案名稱":pn, "請款說明":packed, "總金額":total, "狀態":"已核准", "尚未請款金額":total, "已請款金額":0}
            save_data(pd.concat([db, pd.DataFrame([nr])], ignore_index=True)); st.success("儲存成功！"); st.session_state.last_id = tid; st.rerun()
        else: st.error("請填寫專案名稱、客戶名稱並至少新增一項細項")

    if st.session_state.last_id:
        c1, c2 = st.columns(2)
        if c1.button("🔍 預覽"): st.session_state.view_id = st.session_state.last_id; st.rerun()
        if c2.button("🆕 下一筆"): st.session_state.last_id = None; st.session_state.quote_items = []; st.rerun()

elif menu == "4. 表單狀態總覽及轉採購單":
    render_header()
    st.subheader("📊 表單狀態總覽及轉採購單")
    sys_db = get_filtered_db()
    if not sys_db.empty:
        st.info("💡 勾選報價單並填入「本次轉採購金額」，點擊按鈕即可一鍵生成採購單草稿。")
        df = sys_db.copy(); df.insert(0, "轉成採購單", False); df.insert(1, "本次轉採購金額", 0)
        target_cols = ["轉成採購單", "本次轉採購金額", "單號", "專案名稱", "總金額", "狀態", "已請款金額", "尚未請款金額"]
        edited = st.data_editor(df[target_cols], disabled=["單號","專案名稱","總金額","狀態","已請款金額","尚未請款金額"], hide_index=True, use_container_width=True, column_config={"轉成採購單": st.column_config.CheckboxColumn("勾選轉換"), "本次轉採購金額": st.column_config.NumberColumn("金額 (雙擊輸入)", min_value=0)})
        
        if st.button("🚀 執行轉換 (產生採購單草稿)"):
            fdb = load_data(); count = 0
            for i, row in edited.iterrows():
                amt = row["本次轉採購金額"]
                if row["轉成採購單"] and amt > 0:
                    orig_idx = fdb[fdb["單號"]==row["單號"]].index[0]
                    if amt > clean_amount(fdb.at[orig_idx, "尚未請款金額"]): st.error("超額！"); continue
                    fdb.at[orig_idx, "已請款金額"] += amt; fdb.at[orig_idx, "尚未請款金額"] -= amt
                    new_id = f"PO-FROM-{row['單號']}-{int(time.time())%1000}"
                    nr = {"單號":new_id, "日期":str(datetime.date.today()), "類型":"採購單", "申請人":curr_name, "專案名稱":row["專案名稱"], "總金額":amt, "狀態":"已儲存", "請款說明":f"由報價單 {row['單號']} 轉換"}
                    fdb = pd.concat([fdb, pd.DataFrame([nr])], ignore_index=True); count += 1
            if count > 0: save_data(fdb); st.success(f"成功轉換 {count} 筆！"); st.rerun()

elif menu == "5. 請款狀態/系統設定":
    render_header(); st.subheader("⚙️ 系統設定與資料備份")
    if os.path.exists(D_FILE):
        with open(D_FILE, "rb") as f: st.download_button("⬇️ 下載資料庫備份", f, file_name="系統備份.csv")
    up = st.file_uploader("⬆️ 上傳備份還原")
    if up and st.button("確認還原"):
        with open(D_FILE, "wb") as f: f.write(up.getbuffer())
        st.success("還原成功！"); st.rerun()

# --- 全域預覽 ---
if st.session_state.view_id:
    st.divider(); r = load_data(); r = r[r["單號"]==st.session_state.view_id].iloc[0]
    if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
    st.markdown(render_html(r), unsafe_allow_html=True)
