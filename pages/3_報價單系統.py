import streamlit as st
import pandas as pd
import datetime
import os
import base64
import time
import requests  
import json
import io

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

# --- [資料庫] 報價細項資料 ---
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
def clean_name(val): return str(val).strip().split(" ")[0] if pd.notna(val) and str(val).strip() != "" else ""

def get_online_users(curr_user):
    try:
        now = time.time()
        df = pd.read_csv(O_FILE) if os.path.exists(O_FILE) else pd.DataFrame(columns=["user", "time"])
        df = df[df["user"] != curr_user]
        df = pd.concat([df, pd.DataFrame([{"user": curr_user, "time": now}])], ignore_index=True)
        df = df[now - pd.to_numeric(df["time"], errors='coerce').fillna(0) <= 300]
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
    return {"c_name": "", "address": "", "is_invoice": False, "invoice_no": "", "tax_amt": 0, "items": []}

# --- HTML 渲染 ---
def render_html(row):
    data = parse_quote_json(row.get("請款說明", ""))
    total_net = clean_amount(row['總金額']) - data.get("tax_amt", 0)
    
    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;font-family:sans-serif;">'
    h += f'<div style="text-align:center;"><h2>時研國際設計 - 工程報價單</h2></div>'
    h += f'<p>客戶：{data.get("c_name")} &nbsp;&nbsp; 單號：{row["單號"]}<br>專案編號：{row.get("專案編號","")} &nbsp;&nbsp; 地址：{data.get("address")}</p>'
    
    if data.get("is_invoice") and data.get("invoice_no"):
        h += f'<p><b>發票號碼：{data.get("invoice_no")}</b></p>'

    h += '<table style="width:100%;border-collapse:collapse;font-size:13px;" border="1">'
    h += '<tr bgcolor="#eee"><th>品名</th><th>數量</th><th>單位</th><th>單價</th><th>複價</th><th>備註</th></tr>'
    for item in data.get("items", []):
        q, p = clean_amount(item.get("qty")), clean_amount(item.get("price"))
        h += f'<tr><td>{item.get("name")}</td><td>{q}</td><td>{item.get("unit")}</td><td align="right">{p:,}</td><td align="right">{q*p:,}</td><td>{item.get("note","")}</td></tr>'
    
    h += f'<tr><td colspan="4" align="right">合計淨額</td><td align="right">{total_net:,}</td><td></td></tr>'
    if data.get("is_invoice"):
        h += f'<tr><td colspan="4" align="right">營業稅 (5%)</td><td align="right">{data.get("tax_amt", 0):,}</td><td></td></tr>'
    
    h += f'<tr><td colspan="4" align="right"><b>總計金額 ({row.get("幣別","TWD")})</b></td><td align="right"><b>{clean_amount(row["總金額"]):,}</b></td><td></td></tr></table>'
    h += f'<p style="font-size:11px;margin-top:10px;">申請人：{row["申請人"]} &nbsp; 執行長：{row["專案負責人"]} &nbsp; 日期：{row["日期"]}</p></div>'
    return h

def clean_for_js(h_str): return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

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

# ================= 頁面 1: 填寫申請單 =================
if menu == "1. 填寫申請單":
    st.title("時研國際設計股份有限公司")
    st.subheader("📝 填寫工程報價單")
    db = load_data(); staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
    
    # 編輯模式初始化
    dv = {"app": curr_name, "pn": "", "pi": "", "exe": staffs[0], "curr": "TWD", "c_name": "", "address": "", "ib64": "", "is_invoice": False, "invoice_no": ""}
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id].iloc[0]
        dv_data = parse_quote_json(r["請款說明"])
        dv.update({"app": r["申請人"], "pn": r["專案名稱"], "pi": r["專案編號"], "exe": r["專案負責人"], "curr": r["幣別"], "c_name": dv_data.get("c_name"), "address": dv_data.get("address"), "ib64": r["影像Base64"], "is_invoice": dv_data.get("is_invoice", False), "invoice_no": dv_data.get("invoice_no", "")})
        if not st.session_state.quote_items: st.session_state.quote_items = dv_data.get("items", [])

    with st.expander("👤 1. 基本資料與憑證", expanded=True):
        c1, c2, c3 = st.columns(3)
        if curr_name == "Anita":
            app_val = c1.selectbox("申請人 (可代申請)", staffs, index=staffs.index(dv["app"]) if dv["app"] in staffs else 0)
        else:
            app_val = curr_name; c1.text_input("申請人", value=app_val, disabled=True)
            
        pn = c2.text_input("專案名稱", value=dv["pn"])
        pi = c3.text_input("專案編號", value=dv["pi"])
        
        cx1, cx2, cx3 = st.columns(3)
        exe = cx1.selectbox("負責執行長", staffs, index=staffs.index(dv["exe"]) if dv["exe"] in staffs else 0)
        curr = cx2.selectbox("幣別", ["TWD", "USD", "JPY", "HKD"], index=0)
        c_name = cx3.text_input("客戶名稱", value=dv["c_name"])
        
        address = st.text_input("施工地址", value=dv["address"])
        
        st.markdown("---")
        # 發票邏輯
        ic1, ic2 = st.columns([1, 2])
        is_invoice = ic1.checkbox("是否開立發票", value=dv["is_invoice"])
        invoice_no = ""
        if is_invoice:
            invoice_no = ic2.text_input("請輸入發票號碼", value=dv["invoice_no"])
        
        st.markdown("---")
        f_ims = st.file_uploader("上傳憑證圖片或 Excel 檔案", type=["png", "jpg", "jpeg", "xlsx", "xls"], accept_multiple_files=True)

    with st.expander("📐 2. 報價細項編輯", expanded=True):
        sc1, sc2 = st.columns([1, 1.5])
        eng_list = list(QUOTE_ENGINEERING_DB.keys()) + ["(空白/手動輸入)"]
        sel_eng_raw = sc1.selectbox("工程類別", eng_list)
        final_eng = st.text_input("請輸入自定義工程類別") if sel_eng_raw == "(空白/手動輸入)" else sel_eng_raw
        
        sel_item_opts = ([i['name'] for i in QUOTE_ENGINEERING_DB[sel_eng_raw]] if sel_eng_raw != "(空白/手動輸入)" else []) + ["(空白/手動輸入)"]
        sel_name_raw = sc2.selectbox("品名項目", sel_item_opts)
        final_name = st.text_input("請輸入自定義品名細項") if sel_name_raw == "(空白/手動輸入)" else sel_name_raw
        
        default_p, default_u = 0, "式"
        if sel_eng_raw != "(空白/手動輸入)" and sel_name_raw != "(空白/手動輸入)":
            d_info = next(i for i in QUOTE_ENGINEERING_DB[sel_eng_raw] if i['name'] == sel_name_raw)
            default_p, default_u = d_info['price'], d_info['unit']

        sc3, sc4, sc5 = st.columns(3)
        unit_list = ALL_UNITS + ["(空白/手動輸入)"]
        sel_unit_raw = sc3.selectbox("單位", unit_list, index=unit_list.index(default_u) if default_u in unit_list else 0)
        final_unit = st.text_input("請輸入自定義單位") if sel_unit_raw == "(空白/手動輸入)" else sel_unit_raw
        
        sel_qty = sc4.number_input("數量", min_value=1, value=1)
        sel_price = sc5.number_input("單價", min_value=0, value=default_p)
        sel_note = st.text_input("項目備註")
        
        if st.button("➕ 新增至細項"):
            if final_eng and final_name:
                st.session_state.quote_items.append({"eng": final_eng, "name": final_name, "unit": final_unit, "qty": sel_qty, "price": sel_price, "note": sel_note})
                st.rerun()

    if st.session_state.quote_items:
        df_disp = pd.DataFrame(st.session_state.quote_items)
        df_disp['複價'] = df_disp['qty'] * df_disp['price']
        total_net = df_disp['複價'].sum()
        tax_amt = int(total_net * 0.05) if is_invoice else 0
        total_gross = total_net + tax_amt
        
        st.markdown(f"### 💰 報價總金額：`{total_gross:,}` {curr} (含稅: {tax_amt:,})")
        st.table(df_disp)
        if st.button("🗑️ 清空細項"): st.session_state.quote_items = []; st.rerun()

    if st.button("💾 儲存並產生報價單", type="primary"):
        if pn and c_name and st.session_state.quote_items:
            packed = "[報價單資料]\n" + json.dumps({
                "c_name": c_name, "address": address, "is_invoice": is_invoice, 
                "invoice_no": invoice_no, "tax_amt": tax_amt, "items": st.session_state.quote_items
            }, ensure_ascii=False)
            
            b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else dv["ib64"]
            
            if st.session_state.edit_id:
                idx = db[db["單號"]==st.session_state.edit_id].index[0]
                db.loc[idx, ["申請人", "專案名稱", "專案編號", "專案負責人", "幣別", "請款說明", "總金額", "影像Base64", "尚未請款金額"]] = [app_val, pn, pi, exe, curr, packed, total_gross, b_ims, total_gross]
                st.session_state.edit_id = None
            else:
                tid = f"Q{datetime.date.today().strftime('%Y%m%d')}-{len(db[db['單號'].str.startswith('Q')])+1:02d}"
                nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"報價單", "申請人":app_val, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":packed, "總金額":total_gross, "幣別":curr, "狀態":"已核准", "影像Base64":b_ims, "尚未請款金額":total_gross, "已請款金額":0}
                db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
            save_data(db); st.success("儲存成功！"); st.session_state.quote_items = []; time.sleep(1); st.rerun()

    st.divider(); st.subheader("📋 報價追蹤清單")
    my_db = db[db["類型"] == "報價單"]
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
    hdrs = ["報價單號", "專案名稱", "負責執行長", "申請人", "報價總額", "狀態", "操作"]
    for c, h in zip(cols, hdrs): c.write(f"**{h}**")
    for i, r in my_db.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"]); c[4].write(f"${clean_amount(r['總金額']):,}"); c[5].write(r["狀態"])
        with c[6]:
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("預覽", key=f"v_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
            if
