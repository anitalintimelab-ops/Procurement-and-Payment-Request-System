import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re
import time
import requests  
import json 

# --- 強制系統身分鎖定 ---
st.session_state['sys_choice'] = "採購單系統"

# --- 1. 系統設定 ---
st.set_page_config(page_title="時研-採購單系統", layout="wide", page_icon="🏢")

# [手機版 RWD 響應式優化 CSS & 隱藏左側 app 選單]
st.markdown("""
<style>
/* 隱藏左側選單的第一個項目(app首頁) */
[data-testid="stSidebarNav"] ul li:nth-child(1) { display: none !important; }

.stApp { overflow-x: hidden; }
@media screen and (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    table { word-wrap: break-word !important; font-size: 13px !important; }
    th, td { padding: 5px !important; }
}
</style>
""", unsafe_allow_html=True)

# --- 絕對路徑定位 (穿透 pages 資料夾尋找根目錄) ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
B_DIR = os.path.dirname(CURRENT_DIR) 
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")
O_FILE = os.path.join(B_DIR, "online.csv")
L_FILE = os.path.join(B_DIR, "line_credentials.txt") 

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- 基礎工具 ---
def get_taiwan_time():
    tw_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    return tw_time.strftime('%Y-%m-%d %H:%M')

def clean_amount(val):
    if pd.isna(val) or val is None or str(val).strip() == "": 
        return 0
    s_val = str(val).replace(",", "").replace("$", "").replace("，", "").replace(" ", "")
    try:
        return int(float(s_val))
    except Exception:
        return 0

def clean_name(val):
    if pd.isna(val) or val is None or str(val).strip() == "": 
        return ""
    return str(val).strip().split(" ")[0]

def get_online_users(curr_user):
    try:
        if not curr_user: 
            return 1
        now = time.time()
        df = pd.DataFrame(columns=["user", "time"])
        if os.path.exists(O_FILE):
            try: 
                df = pd.read_csv(O_FILE)
            except Exception: 
                pass
        if "user" not in df.columns or "time" not in df.columns:
            df = pd.DataFrame(columns=["user", "time"])
        df = df[df["user"] != curr_user]
        df = pd.concat([df, pd.DataFrame([{"user": curr_user, "time": now}])], ignore_index=True)
        df["time"] = pd.to_numeric(df["time"], errors='coerce').fillna(now)
        df = df[now - df["time"] <= 300]
        try: 
            df.to_csv(O_FILE, index=False)
        except Exception: 
            pass
        return len(df["user"].unique())
    except Exception:
        return 1

def get_line_credentials():
    if os.path.exists(L_FILE):
        try:
            with open(L_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                t = lines[0].strip() if len(lines) > 0 else ""
                u = lines[1].strip() if len(lines) > 1 else ""
                return t, u
        except Exception: 
            pass
    return "", ""

def send_line_message(msg):
    token, _ = get_line_credentials()
    if not token: return  
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    data = {"messages": [{"type": "text", "text": msg}]}
    try: requests.post(url, headers=headers, json=data, timeout=5)
    except: pass

def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try: return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except: continue
    return pd.DataFrame()

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "代申請人", "專案負責人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱",
            "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", 
            "刪除原因", "駁回原因", "匯款狀態", "匯款日期",
            "支付條件", "支付期數", "請款狀態", "已請款金額", "尚未請款金額", "最後採購金額"]
    df = read_csv_robust(D_FILE)
    if df is None or df.empty: return pd.DataFrame(columns=cols)
    if "專案執行人" in df.columns: df = df.rename(columns={"專案執行人": "專案負責人"})
    for c in cols:
        if c not in df.columns: df[c] = ""
    for col in ["總金額", "已請款金額", "尚未請款金額", "最後採購金額"]:
        df[col] = df[col].apply(clean_amount)
    return df[cols]

def save_data(df):
    try:
        df["總金額"] = df["總金額"].apply(clean_amount)
        df["已請款金額"] = df["已請款金額"].apply(clean_amount)
        df["尚未請款金額"] = df["尚未請款金額"].apply(clean_amount)
        df["最後採購金額"] = df["最後採購金額"].apply(clean_amount)
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError:
        st.error("⚠️ 無法寫入檔案！請關閉 Excel。")
        st.stop()

def load_staff():
    df = read_csv_robust(S_FILE)
    if df is None or df.empty:
        return pd.DataFrame({"name": DEFAULT_STAFF, "status": ["在職"]*5, "password": ["0000"]*5, "avatar": [""], "line_uid": [""]})
    return df

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            if any(x in f.lower() for x in ["logo", "timelab"]) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                with open(os.path.join(B_DIR, f), "rb") as img: return base64.b64encode(img.read()).decode()
    except Exception: pass
    return ""

def render_header():
    logo_b64 = get_b64_logo()
    if logo_b64:
        st.markdown(f'<div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 20px;"><img src="data:image/png;base64,{logo_b64}" style="height: 60px;"><h2>時研國際設計股份有限公司</h2></div>', unsafe_allow_html=True)
    else: st.title("時研國際設計股份有限公司")
    st.divider()

def is_pdf(b64_str): return str(b64_str).startswith("JVBERi")

# [PDF 預覽修復] 使用更安全的嵌入法
def display_pdf(b64_str, height=500):
    pdf_data = f"data:application/pdf;base64,{b64_str}"
    pdf_display = f'<embed src="{pdf_data}" width="100%" height="{height}px" type="application/pdf">'
    st.markdown(pdf_display, unsafe_allow_html=True)
    # 提供一鍵開啟連結以備不時之需
    b64 = base64.b64decode(b64_str)
    st.download_button("📂 無法預覽？點此下載 PDF 查看", data=b64, file_name="附件.pdf", mime="application/pdf")

def clean_for_js(h_str): return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# Session Init
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'user_status' not in st.session_state: st.session_state.user_status = "在職"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None
if 'form_key' not in st.session_state: st.session_state.form_key = 0 

# --- 登入檢查 ---
if st.session_state.user_id is None:
    st.switch_page("app.py")

curr_name = st.session_state.user_id
is_active = (st.session_state.user_status == "在職")
is_admin = (curr_name in ADMINS)

# --- 側邊欄 ---
st.sidebar.markdown(f"**📌 目前系統：** `{st.session_state.sys_choice}`")
st.sidebar.divider()

online_count = get_online_users(curr_name)
st.sidebar.info(f"🟢 目前在線人數：**{online_count}** 人")

with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password")
    if st.button("更新密碼", disabled=not is_active):
        staff_df = load_staff()
        idx = staff_df[staff_df["name"] == curr_name].index[0]
        staff_df.at[idx, "password"] = str(new_pw)
        save_staff(staff_df)
        st.success("密碼已更新")

if is_admin:
    st.sidebar.success("管理員模式")
    with st.sidebar.expander("🔑 所有人員密碼清單"):
        st.dataframe(load_staff()[["name", "password"]], hide_index=True)

if st.sidebar.button("登出系統"):
    st.session_state.user_id = None
    st.switch_page("app.py")

# 導覽選單
menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽及轉請款單"]
if is_admin: menu_options.append("5. 請款狀態/系統設定")

menu = st.sidebar.radio("導覽", menu_options, key="menu_radio")

def get_filtered_db():
    db = load_data()
    return db[db["類型"] == "採購單"]

# --- HTML 渲染 ---
def render_html(row):
    amt = clean_amount(row['總金額'])
    fee = 0
    logo_b64 = get_b64_logo()
    lg_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:50px;">' if logo_b64 else ''
    
    h = f'<div style="padding:20px;border:2px solid #000;max-width:680px;width:100%;margin:auto;background:#fff;color:#000;">'
    h += f'<div style="text-align:center; border-bottom:2px solid #000; padding-bottom:10px;">{lg_html}<h2>採購單</h2></div>'
    h += '<table style="width:100%;border-collapse:collapse;margin-top:10px;" border="1">'
    h += f'<tr><td bgcolor="#eee">單號</td><td>{row["單號"]}</td><td bgcolor="#eee">執行長</td><td>{row["專案負責人"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">專案</td><td colspan="3">{row["專案名稱"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">金額</td><td colspan="3" align="right">{row.get("幣別","TWD")} {amt:,.0f}</td></tr></table>'
    h += '</div>'
    return h

def render_upload_popover(container, r, prefix):
    with container.popover("📎 附件"):
        st.write("**上傳新附件 (圖/PDF)**")
        new_f_acc = st.file_uploader("上傳新存摺", type=["png", "jpg", "pdf"], key=f"{prefix}_acc")
        new_f_ims = st.file_uploader("上傳新憑證", type=["png", "jpg", "pdf"], accept_multiple_files=True, key=f"{prefix}_ims")
        if st.button("💾 儲存附件", key=f"{prefix}_btn"):
            fresh_db = load_data()
            idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
            if new_f_acc: fresh_db.at[idx, "帳戶影像Base64"] = base64.b64encode(new_f_acc.getvalue()).decode()
            if new_f_ims: fresh_db.at[idx, "影像Base64"] = "|".join([base64.b64encode(f.getvalue()).decode() for f in new_f_ims])
            save_data(fresh_db)
            st.success("已更新附件")
            st.rerun()

# --- 頁面邏輯 ---
if menu == "1. 填寫申請單":
    render_header()
    st.subheader("📝 填寫採購申請單")
    try:
        db = load_data()
        staffs = load_staff()["name"].tolist()
        with st.form("form"):
            c1, c2 = st.columns(2)
            pn = c1.text_input("專案名稱")
            exe = c1.selectbox("負責執行長", staffs)
            pi = c2.text_input("專案編號")
            amt = c2.number_input("採購總金額", min_value=0)
            desc = st.text_area("說明")
            f_ims = st.file_uploader("上傳憑證/報價單 (支援圖片與PDF)", type=["png", "jpg", "pdf"], accept_multiple_files=True)
            if st.form_submit_button("儲存申請"):
                if pn and pi and amt > 0:
                    today = datetime.date.today().strftime('%Y%m%d')
                    tid = f"{today}-{len(db[db['單號'].str.startswith(today)])+1:02d}"
                    b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else ""
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":"採購單", "申請人":curr_name, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "總金額":amt, "請款說明":desc, "影像Base64":b_ims, "狀態":"已儲存", "尚未請款金額":amt}
                    db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                    save_data(db)
                    st.success(f"儲存成功！單號：{tid}")
                    st.rerun()
    except Exception as e: st.error(f"錯誤: {e}")

elif menu == "2. 專案執行長簽核":
    render_header()
    db = get_filtered_db()
    p_df = db[(db["狀態"] == "待簽核") & (db["專案負責人"] == curr_name)]
    if p_df.empty: st.info("目前無待簽核單據")
    else:
        for i, r in p_df.iterrows():
            with st.expander(f"單號: {r['單號']} - {r['專案名稱']}"):
                if st.button("✅ 核准", key=f"ok_{i}"):
                    fresh_db = load_data()
                    idx = fresh_db[fresh_db["單號"]==r["單號"]].index[0]
                    fresh_db.at[idx, "狀態"] = "已核准"
                    save_data(fresh_db)
                    send_line_message(f"🔔【採購單已核准】\n單號：{r['單號']}\n專案：{r['專案名稱']} 已審核通過。")
                    st.rerun()

elif menu == "4. 表單狀態總覽及轉請款單":
    render_header()
    st.subheader("📊 表單狀態總覽及轉請款單")
    sys_db = get_filtered_db()
    if not display_df := sys_db.copy().empty:
        df = sys_db.copy()
        st.info("💡 雙擊「本次請款金額」欄位填入金額，勾選後點擊下方按鈕即可轉單。")
        df.insert(0, "轉成請款單", False)
        df.insert(1, "本次請款金額", 0) # 這是可編輯欄位
        
        target_cols = ["轉成請款單", "本次請款金額", "單號", "專案名稱", "專案負責人", "申請人", "總金額", "狀態", "已請款金額", "尚未請款金額"]
        edited_df = st.data_editor(
            df[target_cols],
            disabled=["單號", "專案名稱", "專案負責人", "申請人", "總金額", "狀態", "已請款金額", "尚未請款金額"],
            use_container_width=True,
            column_config={"轉成請款單": st.column_config.CheckboxColumn("勾選"), "本次請款金額": st.column_config.NumberColumn("本次請款金額", min_value=0)},
            hide_index=True
        )
        
        if st.button("🚀 確認將勾選項目轉成請款單"):
            fresh_db = load_data()
            count = 0
            for i, row in edited_df.iterrows():
                if row["轉成請款單"] and row["本次請款金額"] > 0:
                    orig_id = row["單號"]
                    orig_idx = fresh_db[fresh_db["單號"]==orig_id].index[0]
                    orig_r = fresh_db.iloc[orig_idx]
                    
                    unbilled = clean_amount(orig_r.get("尚未請款金額", orig_r["總金額"]))
                    if row["本次請款金額"] > unbilled:
                        st.error(f"❌ {orig_id} 失敗：金額超過餘額 ({unbilled:,})")
                        continue
                    
                    # 更新原始單據金額
                    new_billed = clean_amount(orig_r.get("已請款金額", 0)) + row["本次請款金額"]
                    new_unbilled = unbilled - row["本次請款金額"]
                    fresh_db.at[orig_idx, "已請款金額"] = new_billed
                    fresh_db.at[orig_idx, "尚未請款金額"] = new_unbilled
                    
                    # 建立新請款單
                    new_tid = f"PAY-{orig_id}-{int(time.time())%1000}"
                    nr = {"單號":new_tid, "日期":str(datetime.date.today()), "類型":"請款單", "申請人":"Anita", "專案名稱":orig_r["專案名稱"], "專案負責人":orig_r["專案負責人"], "總金額":row["本次請款金額"], "狀態":"已儲存", "請款說明":f"由採購單 {orig_id} 轉換"}
                    fresh_db = pd.concat([fresh_db, pd.DataFrame([nr])], ignore_index=True)
                    count += 1
            if count > 0:
                save_data(fresh_db)
                st.success(f"✅ 成功轉換 {count} 筆！請到請款單系統查看。")
                time.sleep(1)
                st.rerun()

# --- 全域預覽 ---
if st.session_state.view_id:
    st.divider()
    r = load_data(); r = r[r["單號"]==st.session_state.view_id].iloc[0]
    if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
    st.markdown(render_html(r), unsafe_allow_html=True)
    if r.get("影像Base64"):
        for img in r["影像Base64"].split('|'):
            if is_pdf(img): display_pdf(img)
            else: st.image(base64.b64decode(img))
