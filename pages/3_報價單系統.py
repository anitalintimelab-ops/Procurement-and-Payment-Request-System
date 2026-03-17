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

# --- [資料庫] 報價細項下拉選單資料 ---
QUOTE_ENGINEERING_DB = {
    "假設工程": [{"name": "保護工程", "unit": "式", "price": 245000}, {"name": "拆除工程", "unit": "式", "price": 22000}, {"name": "放樣工程", "unit": "式", "price": 10000}],
    "泥作與防水工程": [{"name": "玄關花磚", "unit": "片", "price": 550}, {"name": "浴室地磚鋪設", "unit": "坪", "price": 8500}, {"name": "地面找平", "unit": "坪", "price": 2500}],
    "木作裝修工程": [{"name": "天花板平釘", "unit": "坪", "price": 3800}, {"name": "造型木作", "unit": "式", "price": 65000}],
    "塗裝裝修工程": [{"name": "乳膠漆粉刷", "unit": "坪", "price": 1200}],
    "清潔工程": [{"name": "竣工細清", "unit": "式", "price": 120000}],
    "其他工程": [{"name": "現場代辦費", "unit": "式", "price": 0}]
}
ALL_UNITS = ["式", "片", "坪", "才", "個", "組", "天", "米", "尺", "工", "樘"]

# --- 基礎工具 ---
def get_taiwan_time(): return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": return 0
    try: return int(float(str(val).replace(",", "").replace("$", "").replace(" ", "")))
    except: return 0
def clean_name(val): return str(val).strip().split(" ")[0] if pd.notna(val) else ""

def get_online_users(curr_user):
    try:
        now = time.time()
        df = pd.read_csv(O_FILE) if os.path.exists(O_FILE) else pd.DataFrame(columns=["user", "time"])
        df = df[df["user"] != curr_user]
        df = pd.concat([df, pd.DataFrame([{"user": curr_user, "time": now}])], ignore_index=True)
        df = df[now - pd.to_numeric(df["time"], errors='coerce') <= 300]
        df.to_csv(O_FILE, index=False)
        return len(df["user"].unique())
    except: return 1

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
    df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')

def load_staff():
    if not os.path.exists(S_FILE): return pd.DataFrame({"name": DEFAULT_STAFF, "password": ["0000"]*5})
    return pd.read_csv(S_FILE, encoding='utf-8-sig', dtype=str).fillna("")

def parse_quote_json(desc_raw):
    try:
        if "[報價單資料]" in desc_raw: return json.loads(desc_raw.split("[報價單資料]")[1].strip())
    except: pass
    return {"c_name": "", "c_phone": "", "address": "", "items": []}

# --- HTML 渲染 ---
def render_html(row):
    data = parse_quote_json(row.get("請款說明", ""))
    amt = clean_amount(row['總金額'])
    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;">'
    h += f'<div style="text-align:center;"><h2>工程報價單</h2></div>'
    h += f'<p>客戶：{data.get("c_name")} &nbsp;&nbsp; 單號：{row["單號"]}<br>地址：{data.get("address")} &nbsp;&nbsp; 執行長：{row["專案負責人"]}</p>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:13px;" border="1">'
    h += '<tr bgcolor="#eee"><th>品名</th><th>數量</th><th>單位</th><th>單價</th><th>複價</th><th>備註</th></tr>'
    for item in data.get("items", []):
        q, p = clean_amount(item.get("qty")), clean_amount(item.get("price"))
        h += f'<tr><td>{item.get("name")}</td><td>{q}</td><td>{item.get("unit")}</td><td align="right">{p:,}</td><td align="right">{q*p:,}</td><td>{item.get("note","")}</td></tr>'
    h += f'<tr><td colspan="4" align="right"><b>總金額 ({row.get("幣別","TWD")})</b></td><td align="right"><b>{amt:,}</b></td><td></td></tr></table></div>'
    return h

# --- Session ---
if st.session_state.get('user_id') is None: st.switch_page("app.py")
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
for k in ['edit_id', 'last_id', 'view_id']: 
    if k not in st.session_state: st.session_state[k] = None
if 'quote_items' not in st.session_state: st.session_state.quote_items = []

curr_name, is_active, is_admin = st.session_state.user_id, (st.session_state.user_status == "在職"), (st.session_state.user_id in ADMINS)

# --- 側邊欄 ---
st.sidebar.markdown(f"**📌 目前系統：** `報價單系統`")
st.sidebar.divider()
st.sidebar.markdown(f"### 👤 {curr_name}")
st.sidebar.info(f"🟢 在線人數：**{get_online_users(curr_name)}** 人")
if st.sidebar.button("登出"):
    st.session_state.user_id = None; st.switch_page("app.py")

menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽及轉採購單", "5. 請款狀態/系統設定"]
menu = st.sidebar.radio("導覽", menu_options, key="menu_radio")

# --- 頁面 1: 填寫申請單 ---
if menu == "1. 填寫申請單":
    st.title("時研國際設計股份有限公司")
    st.subheader("📝 填寫工程報價單")
    db = load_data(); staffs = st.session_state.staff_df["name"].tolist()
    
    # 編輯模式初始化
    if st.session_state.edit_id and not st.session_state.quote_items:
        r = db[db["單號"]==st.session_state.edit_id].iloc[0]
        st.session_state.quote_items = parse_quote_json(r["請款說明"]).get("items", [])

    with st.expander("👤 1. 基本與財務資料", expanded=True):
        c1, c2, c3 = st.columns(3)
        pn = c1.text_input("專案名稱")
        exe = c2.selectbox("負責執行長", staffs, index=staffs.index(curr_name) if curr_name in staffs else 0)
        curr = c3.selectbox("幣別", ["TWD", "USD", "JPY", "HKD"], index=0)
        
        cx1, cx2 = st.columns(2)
        c_name = cx1.text_input("客戶名稱")
        address = cx2.text_input("施工地址")
        
        f_acc = st.file_uploader("上傳存摺/帳戶圖片", type=["png", "jpg", "jpeg"])

    with st.expander("📐 2. 報價細項編輯", expanded=True):
        sc1, sc2, sc3 = st.columns([1, 1.5, 1])
        sel_eng = sc1.selectbox("工程類別", list(QUOTE_ENGINEERING_DB.keys()))
        item_opts = [i['name'] for i in QUOTE_ENGINEERING_DB[sel_eng]]
        sel_name = sc2.selectbox("品名項目", item_opts)
        
        def_info = next(i for i in QUOTE_ENGINEERING_DB[sel_eng] if i['name'] == sel_name)
        
        sc4, sc5, sc6 = st.columns(3)
        sel_unit = sc4.selectbox("單位", ALL_UNITS, index=ALL_UNITS.index(def_info['unit']) if def_info['unit'] in ALL_UNITS else 0)
        sel_qty = sc5.number_input("數量", min_value=1, value=1)
        sel_price = sc6.number_input("單價", min_value=0, value=def_info['price'])
        sel_note = st.text_input("項目備註 (選填)")
        
        if st.button("➕ 新增至細項"):
            st.session_state.quote_items.append({"name": sel_name, "unit": sel_unit, "qty": sel_qty, "price": sel_price, "note": sel_note})
            st.rerun()

    if st.session_state.quote_items:
        st.write("---")
        # 總金額即時顯示
        df_display = pd.DataFrame(st.session_state.quote_items)
        df_display['複價'] = df_display['qty'] * df_display['price']
        total_amt = df_display['複價'].sum()
        
        st.markdown(f"### 💰 目前報價總金額：`{total_amt:,}` {curr}")
        st.table(df_display)
        
        if st.button("🗑️ 清空細項"): st.session_state.quote_items = []; st.rerun()

    if st.button("💾 儲存並產生報價單", type="primary"):
        if pn and c_name and st.session_state.quote_items:
            packed = "[報價單資料]\n" + json.dumps({"c_name": c_name, "address": address, "items": st.session_state.quote_items}, ensure_ascii=False)
            b_acc = base64.b64encode(f_acc.getvalue()).decode() if f_acc else ""
            tid = f"Q{datetime.date.today().strftime('%Y%m%d')}-{len(db[db['單號'].str.startswith('Q')])+1:02d}"
            
            nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"報價單", "申請人":curr_name, "專案負責人":exe, "專案名稱":pn, "請款說明":packed, "總金額":total_amt, "幣別":curr, "狀態":"已核准", "帳戶影像Base64":b_acc, "尚未請款金額":total_amt, "已請款金額":0}
            save_data(pd.concat([db, pd.DataFrame([nr])], ignore_index=True))
            st.success(f"成功！單號：{tid}"); st.session_state.quote_items = []; time.sleep(1); st.rerun()
        else: st.error("請確認專案、客戶與細項已填寫")

    st.divider()
    st.subheader("📋 報價追蹤清單")
    my_db = db[db["類型"] == "報價單"]
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    
    # 恢復寬度比例 [1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5]
    cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
    hdrs = ["報價單號", "專案名稱", "負責執行長", "申請人", "總金額", "狀態", "操作"]
    for c, h in zip(cols, hdrs): c.write(f"**{h}**")
    
    for i, r in my_db.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"])
        c[4].write(f"${clean_amount(r['總金額']):,}"); c[5].write(r["狀態"])
        with c[6]:
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("預覽", key=f"v_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
            if b2.button("列印", key=f"p_{i}"):
                js = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                st.components.v1.html(f"<script>{js}</script>", height=0)
            if b3.button("修改", key=f"e_{i}"): st.session_state.edit_id = r["單號"]; st.rerun()
            if b4.button("刪除", key=f"d_{i}"):
                fdb = load_data(); fdb.at[fdb[fdb["單號"]==r["單號"]].index[0], "狀態"] = "已刪除"; save_data(fdb); st.rerun()

# --- 頁面 4: 轉採購單 ---
elif menu == "4. 表單狀態總覽及轉採購單":
    st.subheader("📊 表單狀態總覽及轉採購單")
    sys_db = load_data(); sys_db = sys_db[sys_db["類型"] == "報價單"]
    if not sys_db.empty:
        df = sys_db.copy(); df.insert(0, "轉成採購單", False); df.insert(1, "本次轉採購金額", 0)
        edited = st.data_editor(df, disabled=["單號","專案名稱","總金額","狀態","已請款金額","尚未請款金額"], hide_index=True)
        if st.button("🚀 執行轉換"):
            fdb = load_data(); count = 0
            for i, row in edited.iterrows():
                amt = row["本次轉採購金額"]
                if row["轉成採購單"] and amt > 0:
                    orig_idx = fdb[fdb["單號"]==row["單號"]].index[0]
                    if amt > clean_amount(fdb.at[orig_idx, "尚未請款金額"]): st.error("超額！"); continue
                    fdb.at[orig_idx, "已請款金額"] += amt; fdb.at[orig_idx, "尚未請款金額"] -= amt
                    nr = {"單號":f"PO-FROM-{row['單號']}", "日期":str(datetime.date.today()), "類型":"採購單", "申請人":curr_name, "專案名稱":row["專案名稱"], "總金額":amt, "狀態":"已儲存", "請款說明":f"由報價單 {row['單號']} 轉換"}
                    fdb = pd.concat([fdb, pd.DataFrame([nr])], ignore_index=True); count += 1
            if count > 0: save_data(fdb); st.success(f"成功轉換 {count} 筆！"); st.rerun()

# --- 頁面 5: 系統設定 ---
elif menu == "5. 請款狀態/系統設定":
    st.subheader("⚙️ 系統設定與備份")
    if os.path.exists(D_FILE):
        with open(D_FILE, "rb") as f: st.download_button("⬇️ 下載資料庫備份", f, file_name="系統備份.csv")

# --- 全域預覽 ---
if st.session_state.view_id:
    st.divider(); r = load_data(); r = r[r["單號"]==st.session_state.view_id].iloc[0]
    if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
    st.markdown(render_html(r), unsafe_allow_html=True)
    if r.get("帳戶影像Base64"): st.image(base64.b64decode(r["帳戶影像Base64"]), caption="帳戶存摺")
