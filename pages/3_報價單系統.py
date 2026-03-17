import streamlit as st
import pandas as pd
import datetime, os, base64, time, requests, json, io

# --- 1. 系統鎖定與介面設定 ---
st.session_state['sys_choice'] = "報價單系統"
st.set_page_config(page_title="時研-報價單系統", layout="wide", page_icon="🏢")

st.markdown("""
<style>
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }
.stApp { overflow-x: hidden; }
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    table { font-size: 13px !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 2. 路徑與資料庫定位 ---
B_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D_FILE, S_FILE, O_FILE, L_FILE = [os.path.join(B_DIR, f) for f in ["database.csv", "staff_v2.csv", "online.csv", "line_credentials.txt"]]
ADMINS, DEFAULT_STAFF = ["Anita"], ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- 3. [資料庫] 報價細項選單 (嚴格依照 Excel 內容) ---
QUOTE_DB = {
    "假設工程": ["保護工程", "原隔間拆除清運", "放樣工程", "大樓清潔管理費", "臨時隔間+門"],
    "泥作與防水工程": ["玄關花磚", "浴室磚鋪設", "地面找平", "防水工程", "紅磚隔間", "牆面粉刷"],
    "木作裝修工程": ["天花板平釘", "造型木作電視牆", "冷氣包樑", "暗門製作", "窗簾盒", "木作櫃體"],
    "水電弱電工程": ["開關插座移位", "燈具安裝", "迴路新增", "冷熱水管更新", "消防灑水修改"],
    "油漆裝修工程": ["全室乳膠漆", "木作噴漆", "天花板批土粉刷", "牆面跳色"],
    "清潔工程": ["施工中粗清", "竣工後細清", "廢棄物清運"],
    "(空白/手動輸入)": ["(空白/手動輸入)"]
}
UNITS = ["式", "坪", "片", "才", "個", "組", "天", "米", "工", "樘", "迴", "(空白/手動輸入)"]

# --- 4. 基礎工具 ---
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
        df.to_csv(O_FILE, index=False); return len(df["user"].unique())
    except: return 1

def load_data():
    if not os.path.exists(D_FILE): return pd.DataFrame()
    try:
        df = pd.read_csv(D_FILE, encoding='utf-8-sig', dtype=str).fillna("")
        for c in ["總金額", "已請款金額", "尚未請款金額"]:
            if c in df.columns: df[c] = df[c].apply(clean_amount)
        return df
    except: return pd.DataFrame()

def save_data(df):
    try: df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except: st.error("⚠️ 存檔失敗！請關閉電腦上的 database.csv。"); st.stop()

def load_staff():
    if not os.path.exists(S_FILE): return pd.DataFrame({"name": DEFAULT_STAFF, "password": ["0000"]*5})
    return pd.read_csv(S_FILE, encoding='utf-8-sig', dtype=str).fillna("")

def parse_quote_json(desc_raw):
    try:
        if "[報價單資料]" in desc_raw: return json.loads(desc_raw.split("[報價單資料]")[1].strip())
    except: pass
    return {"c_name": "", "address": "", "is_inv": False, "inv_no": "", "tax": 0, "items": []}

# --- 5. HTML 專業報價單渲染 ---
def render_html(row):
    data = parse_quote_json(row.get("請款說明", ""))
    total_net = clean_amount(row['總金額']) - data.get("tax", 0)
    h = f'<div style="padding:20px;border:2px solid #000;background:#fff;color:#000;font-family:sans-serif;">'
    h += f'<div style="text-align:center;"><h2>時研國際設計 - 工程報價單</h2></div>'
    h += f'<p>客戶：{data.get("c_name")} &nbsp; 單號：{row["單號"]}<br>專案：{row["專案名稱"]} ({row.get("專案編號","")}) &nbsp; 地址：{data.get("address")}</p>'
    if data.get("is_inv"): h += f'<p><b>發票號碼：{data.get("inv_no","尚未填寫")}</b></p>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:13px;text-align:center;" border="1"><tr bgcolor="#eee"><th>工程大類</th><th>品名細項</th><th>數量</th><th>單位</th><th>單價</th><th>複價</th><th>備註</th></tr>'
    for i in data.get("items", []):
        q, p = clean_amount(i.get("qty")), clean_amount(i.get("price"))
        h += f'<tr><td>{i.get("eng")}</td><td align="left">{i.get("name")}</td><td>{q}</td><td>{i.get("unit")}</td><td align="right">{p:,}</td><td align="right">{q*p:,}</td><td>{i.get("note","")}</td></tr>'
    h += f'<tr><td colspan="5" align="right">合計淨額</td><td align="right">{total_net:,}</td><td></td></tr>'
    if data.get("is_inv"): h += f'<tr><td colspan="5" align="right">營業稅 (5%)</td><td align="right">{data.get("tax",0):,}</td><td></td></tr>'
    h += f'<tr><td colspan="5" align="right"><b>總計報價金額</b></td><td align="right"><b>{clean_amount(row["總金額"]):,}</b></td><td></td></tr></table>'
    h += f'<p style="font-size:11px;margin-top:10px;">申請人：{row["申請人"]} &nbsp; 執行長：{row["專案負責人"]} &nbsp; 日期：{row["日期"]}</p></div>'
    return h

def clean_for_js(h_str): return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# --- 6. Session 與身分檢查 ---
if st.session_state.get('user_id') is None: st.switch_page("app.py")
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
for k in ['edit_id', 'last_id', 'view_id']: 
    if k not in st.session_state: st.session_state[k] = None
if 'quote_items' not in st.session_state: st.session_state.quote_items = []

curr_name, is_active, is_admin = st.session_state.user_id, (st.session_state.user_status == "在職"), (st.session_state.user_id in ADMINS)

# --- 7. 左側側邊欄 (嚴格對齊) ---
st.sidebar.markdown(f"**📌 目前系統：** `報價單系統`")
st.sidebar.divider()
avatar_b64 = ""
try: avatar_b64 = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].iloc[0].get("avatar", "")
except: pass

if avatar_b64: st.sidebar.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:15px;"><img src="data:image/jpeg;base64,{avatar_b64}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;border:3px solid #eee;"><span style="font-size:22px;font-weight:bold;color:#333;">{curr_name}</span></div>', unsafe_allow_html=True)
else: st.sidebar.markdown(f"### 👤 {curr_name}")

st.sidebar.info(f"🟢 在線人數：**{get_online_users(curr_name)}** 人")
with st.sidebar.expander("🔐 修改密碼/大頭貼"):
    new_pw = st.text_input("新密碼", type="password")
    if st.button("更新密碼") and len(new_pw) >= 4:
        s_df = load_staff(); idx = s_df[s_df["name"] == curr_name].index[0]
        s_df.at[idx, "password"] = str(new_pw); save_staff(s_df); st.success("成功")

if is_admin:
    st.sidebar.success("管理員模式")
    with st.sidebar.expander("⚙️ 系統資料管理"):
        if st.button("下載資料庫備份"):
            with open(D_FILE, "rb") as f: st.download_button("點此下載", f, file_name="database.csv")

if st.sidebar.button("登出系統"): st.session_state.user_id = None; st.switch_page("app.py")

menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽及轉採購單", "5. 請款狀態/系統設定"]
menu = st.sidebar.radio("導覽", menu_options, key="menu_radio")

# ================= 頁面 1: 填寫申請單 (恢復工程與細項) =================
if menu == "1. 填寫申請單":
    st.title("時研國際設計股份有限公司")
    st.subheader("📝 填寫工程報價單")
    db = load_data(); staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
    
    dv = {"app": curr_name, "pn": "", "pi": "", "exe": staffs[0], "c_name": "", "address": "", "ib64": "", "is_inv": False, "inv_no": ""}
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id].iloc[0]
        jd = parse_quote_json(r["請款說明"])
        dv.update({"app": r["申請人"], "pn": r["專案名稱"], "pi": r["專案編號"], "exe": r["專案負責人"], "c_name": jd.get("c_name"), "address": jd.get("address"), "ib64": r["影像Base64"], "is_inv": jd.get("is_inv"), "inv_no": jd.get("inv_no")})
        if not st.session_state.quote_items: st.session_state.quote_items = jd.get("items", [])

    with st.expander("👤 1. 基本資料", expanded=True):
        c1, c2, c3 = st.columns(3)
        app_val = c1.selectbox("申請人", staffs, index=staffs.index(dv["app"]) if dv["app"] in staffs else 0) if curr_name == "Anita" else curr_name
        if curr_name != "Anita": c1.text_input("申請人", value=app_val, disabled=True)
        pn = c2.text_input("專案名稱", value=dv["pn"]); pi = c3.text_input("專案編號", value=dv["pi"])
        cx1, cx2, cx3 = st.columns(3)
        exe = cx1.selectbox("負責執行長", staffs, index=staffs.index(dv["exe"]) if dv["exe"] in staffs else 0)
        c_name = cx2.text_input("客戶名稱", value=dv["c_name"]); address = cx3.text_input("施工地址", value=dv["address"])
        st.markdown("---")
        ic1, ic2 = st.columns([1, 2])
        is_inv = ic1.checkbox("是否開立發票", value=dv["is_inv"])
        inv_no = ic2.text_input("發票號碼 (若有)", value=dv["inv_no"]) if is_inv else ""
        f_ims = st.file_uploader("上傳憑證 (圖/Excel)", type=["png", "jpg", "jpeg", "xlsx"], accept_multiple_files=True)

    with st.expander("📐 2. 報價細項編輯", expanded=True):
        sc1, sc2 = st.columns(2)
        eng_sel = sc1.selectbox("工程類別", list(QUOTE_DB.keys()))
        f_eng = st.text_input("請手動輸入工程大類") if eng_sel == "(空白/手動輸入)" else eng_sel
        item_sel = sc2.selectbox("品名項目", QUOTE_DB.get(eng_sel, ["(空白/手動輸入)"]))
        f_name = st.text_input("請手動輸入品名項目") if item_sel == "(空白/手動輸入)" else item_sel
        sc3, sc4, sc5 = st.columns(3)
        unit_sel = sc3.selectbox("單位", UNITS)
        f_unit = st.text_input("請手動輸入單位") if unit_sel == "(空白/手動輸入)" else unit_sel
        qty = sc4.number_input("數量", min_value=1.0, value=1.0); price = sc5.number_input("單價", min_value=0, value=0)
        note = st.text_input("項目備註")
        if st.button("➕ 新增此工項"):
            if f_eng and f_name:
                st.session_state.quote_items.append({"eng": f_eng, "name": f_name, "unit": f_unit, "qty": qty, "price": price, "note": note})
                st.rerun()

    if st.session_state.quote_items:
        df_tmp = pd.DataFrame(st.session_state.quote_items)
        net_total = sum(i['qty'] * i['price'] for i in st.session_state.quote_items)
        tax = int(net_total * 0.05) if is_inv else 0
        total = net_total + tax
        st.markdown(f"### 💰 報價總計：`{total:,}` (淨額: {net_total:,} / 稅額: {tax:,})")
        st.table(df_tmp)
        if st.button("🗑️ 清空所有細項"): st.session_state.quote_items = []; st.rerun()

    if st.button("💾 儲存報價單", type="primary"):
        if pn and c_name and st.session_state.quote_items:
            packed = "[報價單資料]\n" + json.dumps({"c_name": c_name, "address": address, "is_inv": is_inv, "inv_no": inv_no, "tax": tax, "items": st.session_state.quote_items}, ensure_ascii=False)
            b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else dv["ib64"]
            fresh_db = load_data()
            if st.session_state.edit_id:
                idx = fresh_db[fresh_db["單號"]==st.session_state.edit_id].index[0]
                fresh_db.loc[idx, ["申請人", "專案名稱", "專案編號", "專案負責人", "請款說明", "總金額", "影像Base64", "尚未請款金額"]] = [app_val, pn, pi, exe, packed, total, b_ims, total]
                st.session_state.edit_id = None
            else:
                tid = f"Q{datetime.date.today().strftime('%Y%m%d')}-{len(fresh_db[fresh_db['單號'].str.startswith('Q')])+1:02d}"
                nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"報價單", "申請人":app_val, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":packed, "總金額":total, "狀態":"已核准", "影像Base64":b_ims, "尚未請款金額":total, "已請款金額":0}
                fresh_db = pd.concat([fresh_db, pd.DataFrame([nr])], ignore_index=True)
            save_data(fresh_db); st.success("報價單已成功存檔！"); st.session_state.quote_items = []; time.sleep(1); st.rerun()

    st.divider(); st.subheader("📋 報價追蹤清單")
    my_db = load_data(); my_db = my_db[my_db["類型"] == "報價單"]
    if not is_admin: my_db = my_db[my_db["申請人"] == curr_name]
    cols = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
    for c, h in zip(cols, ["報價單號", "專案名稱", "執行長", "申請人", "報價金額", "狀態", "操作"]): c.write(f"**{h}**")
    for i, r in my_db.iterrows():
        c = st.columns([1.2, 1.8, 1.2, 1, 1.2, 1.5, 3.5])
        c[0].write(r["單號"]); c[1].write(r["專案名稱"]); c[2].write(clean_name(r["專案負責人"])); c[3].write(r["申請人"]); c[4].write(f"${clean_amount(r['總金額']):,}"); c[5].write(r["狀態"])
        with c[6]:
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("預覽", key=f"v_{i}"): st.session_state.view_id = r["單號"]; st.rerun()
            if b2.button("列印", key=f"p_{i}"): st.components.v1.html(f"<script>var w=window.open();w.document.write('{clean_for_js(render_html(r))}');w.print();w.close();</script>", height=0)
            if b3.button("修改", key=f"e_{i}"): st.session_state.edit_id = r["單號"]; st.rerun()
            if b4.button("刪除", key=f"d_{i}"):
                fdb = load_data(); fdb.at[fdb[fdb["單號"]==r["單號"]].index[0], "狀態"] = "已刪除"; save_data(fdb); st.rerun()

# ================= 頁面 2 & 3: 簽核 (保留畫面) =================
elif menu in ["2. 專案執行長簽核", "3. 財務長簽核"]:
    st.title(menu); st.info("報價單預設免簽核。此處供查閱使用。")

# ================= 頁面 4: 轉採購單 =================
elif menu == "4. 表單狀態總覽及轉採購單":
    st.subheader("📊 表單狀態總覽及轉採購單")
    sys_db = load_data(); sys_db = sys_db[sys_db["類型"] == "報價單"]
    if not sys_db.empty:
        df = sys_db.copy(); df.insert(0, "轉成採購單", False); df.insert(1, "本次轉入金額", 0)
        ed = st.data_editor(df, disabled=["單號","專案名稱","總金額","狀態","已請款金額","尚未請款金額"], hide_index=True)
        if st.button("🚀 執行轉換 (生成採購單草稿)"):
            fdb = load_data(); count = 0
            for _, row in ed.iterrows():
                if row["轉成採購單"] and row["本次轉入金額"] > 0:
                    idx = fdb[fdb["單號"]==row["單號"]].index[0]
                    if row["本次轉入金額"] > clean_amount(fdb.at[idx, "尚未請款金額"]): st.error(f"{row['單號']} 超額"); continue
                    fdb.at[idx, "已請款金額"] += row["本次轉入金額"]; fdb.at[idx, "尚未請款金額"] -= row["本次轉入金額"]
                    nr = {"單號":f"PO-F-{row['單號']}-{int(time.time())%100}", "日期":str(datetime.date.today()), "類型":"採購單", "申請人":curr_name, "專案名稱":row["專案名稱"], "總金額":row["本次轉入金額"], "狀態":"已儲存", "請款說明":f"從報價單 {row['單號']} 轉入"}
                    fdb = pd.concat([fdb, pd.DataFrame([nr])], ignore_index=True); count += 1
            if count > 0: save_data(fdb); st.success(f"成功轉換 {count} 筆！"); st.rerun()

# ================= 頁面 5: 系統設定 (同步對齊) =================
elif menu == "5. 請款狀態/系統設定":
    st.title("⚙️ 請款狀態 / 系統設定")
    with st.expander("💾 資料庫備份與還原", expanded=True):
        if os.path.exists(D_FILE):
            with open(D_FILE, "rb") as f: st.download_button("⬇️ 下載最新備份", f, file_name="database.csv")
        up = st.file_uploader("⬆️ 上傳 CSV 還原備份", type=["csv"])
        if up and st.button("確認還原"):
            with open(D_FILE, "wb") as f: f.write(up.getbuffer())
            st.success("還原成功！"); st.rerun()

# ================= 全域預覽 =================
if st.session_state.view_id:
    st.divider(); r = load_data(); r = r[r["單號"]==st.session_state.view_id].iloc[0]
    if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
    st.markdown(render_html(r), unsafe_allow_html=True)
    if r.get("影像Base64"):
        for f_b64 in r["影像Base64"].split('|'):
            try:
                raw = base64.b64decode(f_b64)
                if raw.startswith(b'PK\x03\x04'): st.write("📊 Excel 內容："); st.dataframe(pd.read_excel(io.BytesIO(raw)))
                else: st.image(raw)
            except: st.error("附件解析失敗")
