import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re
import time

# --- 1. 系統設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"
DEFAULT_STAFF = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# [工具] 取得台灣時間
def get_taiwan_time():
    tw_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    return tw_time.strftime('%Y-%m-%d %H:%M')

# [工具] 金額清洗
def clean_amount(val):
    if pd.isna(val) or str(val).strip() == "": return 0
    s_val = str(val).replace(",", "").replace("$", "").replace("，", "").replace(" ", "")
    try:
        return int(float(s_val))
    except:
        return 0

# [工具] 名字清洗 (只留英文)
def clean_name(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).strip().split(" ")[0]

# --- 2. 自動救援資料 ---
def init_rescue_data():
    if not os.path.exists(D_FILE):
        data = {
            "單號": ["20260205-01", "20260205-02"],
            "日期": ["2026-02-05", "2026-02-05"],
            "類型": ["請款單", "請款單"],
            "申請人": ["Anita", "Andy"],
            "專案負責人": ["Charles", "Andy"], 
            "專案名稱": ["公司費用", "測試專案"],
            "專案編號": ["GENERAL", "TEST01"],
            "請款說明": ["電腦維修", "測試款項"],
            "總金額": [5500, 10000],
            "幣別": ["TWD", "TWD"],
            "付款方式": ["現金", "現金"],
            "請款廠商": ["大老資訊", "測試廠商"],
            "匯款帳戶": ["", ""],
            "帳戶影像Base64": ["", ""],
            "狀態": ["待初審", "待初審"],
            "影像Base64": ["", ""], 
            "提交時間": ["2026-02-05 14:00", "2026-02-05 14:05"],
            "申請人信箱": ["Anita", "Andy"],
            "初審人": ["", ""],
            "初審時間": ["", ""],
            "複審人": ["", ""],
            "複審時間": ["", ""],
            "刪除人": ["", ""], "刪除時間": ["", ""], "刪除原因": ["", ""], "駁回原因": ["", ""]
        }
        df = pd.DataFrame(data)
        df.to_csv(D_FILE, index=False, encoding='utf-8-sig')

init_rescue_data()

# --- 3. 核心功能 ---
def validate_password(pw):
    has_letter = bool(re.search(r'[a-zA-Z]', pw))
    digit_count = len(re.findall(r'\d', pw))
    return has_letter and 4 <= digit_count <= 6

def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
        try:
            return pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
        except:
            continue
    return pd.DataFrame()

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "專案負責人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱",
            "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", "刪除原因", "駁回原因"]
    
    df = read_csv_robust(D_FILE)
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    
    if "專案執行人" in df.columns:
        df = df.rename(columns={"專案執行人": "專案負責人"})
    
    for c in cols:
        if c not in df.columns: df[c] = ""
            
    df["總金額"] = df["總金額"].apply(clean_amount)
    df["專案負責人"] = df["專案負責人"].astype(str).apply(clean_name)
    df["申請人"] = df["申請人"].astype(str).apply(clean_name)
    df["狀態"] = df["狀態"].astype(str).str.strip()
    
    return df[cols]

def save_data(df):
    try:
        df["總金額"] = df["總金額"].apply(clean_amount)
        df["專案負責人"] = df["專案負責人"].astype(str).apply(clean_name)
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError:
        st.error("⚠️ 警告：無法寫入檔案！請關閉 Excel。")
        st.stop()

def load_staff():
    default_df = pd.DataFrame({
        "name": DEFAULT_STAFF, 
        "status": ["在職"]*len(DEFAULT_STAFF), 
        "password": ["0000"]*len(DEFAULT_STAFF)
    })
    
    df = read_csv_robust(S_FILE)
    
    # [關鍵修復] 這裡增加 df is None 的判斷，防止 AttributeError
    if df is None or df.empty or "name" not in df.columns:
        df = default_df.copy()
        df.to_csv(S_FILE, index=False, encoding='utf-8-sig')
        return df
        
    if "status" not in df.columns: df["status"] = "在職"
    df["name"] = df["name"].str.strip()
    return df

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            if any(x in f.lower() for x in ["logo", "timelab"]) and f.lower().endswith(('.png', '.jpg')):
                with open(os.path.join(B_DIR, f), "rb") as img:
                    return base64.b64encode(img.read()).decode()
    except: pass
    return ""

def clean_for_js(h_str):
    return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

def is_pdf(b64_str):
    return b64_str.startswith("JVBERi")

# Session Init
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'user_status' not in st.session_state: st.session_state.user_status = "在職"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None
if 'form_key' not in st.session_state: st.session_state.form_key = 0 

# --- 4. 登入 ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    staff_df = load_staff()
    with st.form("login"):
        u = st.selectbox("身分", staff_df["name"].tolist())
        p = st.text_input("密碼", type="password")
        if st.form_submit_button("登入"):
            row = staff_df[staff_df["name"] == u].iloc[0]
            stored_p = str(row["password"]).strip().replace(".0", "")
            input_p = str(p).strip()
            if input_p == stored_p or (input_p == "0000" and stored_p in ["nan", ""]):
                st.session_state.user_id = u
                st.session_state.user_status = row["status"] if pd.notna(row["status"]) else "在職"
                st.session_state.staff_df = staff_df
                st.rerun()
            else:
                st.error("密碼錯誤")
    st.stop()

curr_name = st.session_state.user_id
is_active = (st.session_state.user_status == "在職")
is_admin = (curr_name in ADMINS)

# --- 5. 側邊欄 ---
st.sidebar.markdown(f"### 👤 {curr_name}")
if not is_active: st.sidebar.error("⛔ 已離職")

if is_admin:
    st.sidebar.success("管理員模式")
    with st.sidebar.expander("➕ 新增人員"):
        n = st.text_input("姓名")
        if st.button("新增"):
            staff_df = st.session_state.staff_df
            if n not in staff_df["name"].values:
                staff_df = pd.concat([staff_df, pd.DataFrame({"name":[n], "status":["在職"], "password":["0000"]})])
                save_staff(staff_df)
                st.session_state.staff_df = staff_df
                st.success("成功")
                st.rerun()
            else: st.error("已存在")
    
    with st.sidebar.expander("⚙️ 狀態管理"):
        staff_df = st.session_state.staff_df
        for i, r in staff_df.iterrows():
            c1, c2 = st.columns([2, 1])
            c1.write(r["name"])
            nst = c2.selectbox("", ["在職", "離職"], index=["在職", "離職"].index(r["status"]), key=f"s_{i}", label_visibility="collapsed")
            if nst != r["status"]:
                staff_df.at[i, "status"] = nst
                save_staff(staff_df)
                st.rerun()

if st.sidebar.button("登出"):
    st.session_state.user_id = None
    st.rerun()

menu = st.sidebar.radio("導覽", ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核"])

# --- HTML 渲染 ---
def render_html(row):
    amt = clean_amount(row['總金額'])
    fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0
    sub_time = row["提交時間"] if row["提交時間"] and str(row["提交時間"]) != "nan" else get_taiwan_time()
    
    h = f'<div style="padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += f'<h3>時研國際設計 - {row["類型"]}</h3><hr>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += f'<tr><td bgcolor="#eee">單號</td><td>{row["單號"]}</td><td bgcolor="#eee">負責人</td><td>{clean_name(row["專案負責人"])}</td></tr>'
    h += f'<tr><td bgcolor="#eee">專案</td><td>{row["專案名稱"]}</td><td bgcolor="#eee">編號</td><td>{row["專案編號"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">申請人</td><td>{row["申請人"]}</td><td bgcolor="#eee">廠商</td><td>{row["請款廠商"]}</td></tr>'
    h += f'<tr><td bgcolor="#eee">說明</td><td colspan="3">{row["請款說明"]}</td></tr>'
    h += f'<tr><td colspan="3" align="right">金額</td><td align="right">{amt:,.0f}</td></tr>'
    h += f'<tr><td colspan="3" align="right">實付</td><td align="right">{amt-fee:,.0f}</td></tr></table>'
    
    if row['帳戶影像Base64']:
        h += '<br><b>存摺：</b><br>'
        if is_pdf(row['帳戶影像Base64']): h += f'<embed src="data:application/pdf;base64,{row["帳戶影像Base64"]}" width="100%" height="300px" />'
        else: h += f'<img src="data:image/jpeg;base64,{row["帳戶影像Base64"]}" width="100%">'
        
    if row["狀態"] == "已駁回" and str(row.get("駁回原因", "")) != "":
        h += f'<div style="color:red;border:1px solid red;padding:5px;margin-top:5px;"><b>❌ 駁回原因：</b>{row["駁回原因"]}</div>'
        
    h += f'<p>提交: {sub_time} | 初審: {row["初審人"]} | 複審: {row["複審人"]}</p></div>'
    
    v = ""
    if row['影像Base64']:
        imgs = row['影像Base64'].split('|')
        for i, img in enumerate(imgs):
            v += '<div style="page-break-before:always;padding:20px;">'
            if is_pdf(img): v += f'<embed src="data:application/pdf;base64,{img}" width="100%" height="800px" />'
            else: v += f'<img src="data:image/jpeg;base64,{img}" width="100%">'
            v += '</div>'
    return h + v

# --- 主程式 ---
if menu == "1. 填寫申請單":
    st.subheader("填寫申請單")
    db = load_data()
    staffs = st.session_state.staff_df["name"].apply(clean_name).tolist()
    if curr_name not in staffs: staffs.append(curr_name)
    
    dv = {"pn":"", "exe":staffs[0], "pi":"", "amt":0, "tp":"請款單", "pay":"現金", "vdr":"", "acc":"", "desc":"", "ab64":"", "ib64":""}
    
    if st.session_state.edit_id:
        r = db[db["單號"]==st.session_state.edit_id]
        if not r.empty:
            row = r.iloc[0]
            st.info(f"修改中: {st.session_state.edit_id}")
            dv["pn"] = row["專案名稱"]
            exe_clean = clean_name(row["專案負責人"])
            dv["exe"] = exe_clean if exe_clean in staffs else staffs[0]
            dv["pi"] = row["專案編號"]
            dv["amt"] = clean_amount(row["總金額"])
            dv["tp"] = row["類型"]
            dv["pay"] = row["付款方式"]
            dv["vdr"] = row["請款廠商"]
            dv["acc"] = row["匯款帳戶"]
            dv["desc"] = row["請款說明"]
            dv["ab64"] = row["帳戶影像Base64"]
            dv["ib64"] = row["影像Base64"]

    with st.form("form"):
        mode_suffix = f"{st.session_state.edit_id}_{st.session_state.form_key}" if st.session_state.edit_id else f"new_{st.session_state.form_key}"
        c1, c2 = st.columns(2)
        pn = c1.text_input("專案名稱", value=dv["pn"], key=f"pn_{mode_suffix}")
        exe = c1.selectbox("專案負責人", staffs, index=staffs.index(dv["exe"]), key=f"exe_{mode_suffix}")
        pi = c2.text_input("專案編號", value=dv["pi"], key=f"pi_{mode_suffix}")
        amt = c2.number_input("總金額", value=dv["amt"], min_value=0, key=f"amt_{mode_suffix}")
        tp = c2.selectbox("類型", ["請款單", "採購單"], index=["請款單", "採購單"].index(dv["tp"]), key=f"tp_{mode_suffix}")
        pay = st.radio("付款方式", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], index=["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"].index(dv["pay"]), horizontal=True, key=f"pay_{mode_suffix}")
        vdr = st.text_input("廠商", value=dv["vdr"], key=f"vdr_{mode_suffix}")
        acc = st.text_input("帳戶", value=dv["acc"], key=f"acc_{mode_suffix}")
        desc = st.text_area("說明", value=dv["desc"], key=f"desc_{mode_suffix}")
        
        del_acc = False
        if dv["ab64"]:
            st.write("✅ 已有存摺")
            if is_pdf(dv["ab64"]): st.markdown(f'<embed src="data:application/pdf;base64,{dv["ab64"]}" width="100%" height="200px" />', unsafe_allow_html=True)
            else: st.image(base64.b64decode(dv["ab64"]), width=200)
            del_acc = st.checkbox("❌ 刪除此存摺", key=f"da_{mode_suffix}")
        f_acc = st.file_uploader("上傳存摺", key=f"fa_{mode_suffix}")
        
        del_ims = False
        if dv["ib64"]:
            st.write("✅ 已有憑證")
            del_ims = st.checkbox("❌ 刪除所有憑證", key=f"di_{mode_suffix}")
        f_ims = st.file_uploader("上傳憑證", accept_multiple_files=True, key=f"fi_{mode_suffix}")
        
        if st.form_submit_button("💾 儲存", disabled=not is_active):
            db = load_data()
            if not (pn and pi and amt>0 and desc):
                st.error("未填完")
            else:
                b_acc = base64.b64encode(f_acc.getvalue()).decode() if f_acc else ("" if del_acc else dv["ab64"])
                b_ims = "|".join([base64.b64encode(f.getvalue()).decode() for f in f_ims]) if f_ims else ("" if del_ims else dv["ib64"])
                
                if st.session_state.edit_id:
                    idx = db[db["單號"]==st.session_state.edit_id].index[0]
                    db.at[idx, "專案名稱"] = pn; db.at[idx, "專案負責人"] = exe; db.at[idx, "專案編號"] = pi
                    db.at[idx, "總金額"] = amt; db.at[idx, "請款說明"] = desc; db.at[idx, "類型"] = tp
                    db.at[idx, "付款方式"] = pay; db.at[idx, "請款廠商"] = vdr; db.at[idx, "匯款帳戶"] = acc
                    db.at[idx, "帳戶影像Base64"] = b_acc; db.at[idx, "影像Base64"] = b_ims
                    st.session_state.edit_id = None
                else:
                    tid = f"{datetime.date.today().strftime('%Y%m%d')}-{len(db)+1:02d}"
                    nr = {"單號":tid, "日期":str(datetime.date.today()), "類型":tp, "申請人":curr_name, 
                          "專案負責人":exe, "專案名稱":pn, "專案編號":pi, "請款說明":desc, "總金額":amt, 
                          "幣別":"TWD", "付款方式":pay, "請款廠商":vdr, "匯款帳戶":acc, 
                          "帳戶影像Base64":b_acc, "狀態":"已儲存", "影像Base64":b_ims, "提交時間":"",
                          "申請人信箱":curr_name, "初審人":"", "初審時間":"", "複審人":"", "複審時間":"", "刪除人":"", "刪除時間":"", "刪除原因":"", "駁回原因":""}
                    db = pd.concat([db, pd.DataFrame([nr])], ignore_index=True)
                    st.session_state.last_id = tid
                    st.session_state.form_key += 1
                save_data(db)
                st.success("成功")
                st.rerun()

    if st.session_state.last_id:
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("🔍 預覽"): st.session_state.view_id = st.session_state.last_id; st.rerun()
        if c2.button("🚀 提交", disabled=not is_active):
            db = load_data()
            idx = db[db["單號"]==st.session_state.last_id].index[0]
            db.at[idx, "狀態"] = "待初審"
            db.at[idx, "提交時間"] = get_taiwan_time()
            save_data(db)
            st.session_state.last_id = None
            st.success("已提交")
            st.rerun()
        if c4.button("🆕 下一筆"): st.session_state.last_id = None; st.rerun()

    st.divider(); st.subheader("📋 申請追蹤清單")
    db = load_data()
    my_db = db if is_admin else db[(db["申請人"].str.contains(curr_name)) | (db["申請人信箱"].str.contains(curr_name))]
    
    st.dataframe(my_db[["單號", "專案名稱", "專案負責人", "總金額", "狀態"]])
    
    for i, r in my_db.iterrows():
        c1, c2, c3, c4, c5 = st.columns([1.5, 2, 1, 1, 2.5])
        c1.write(r["單號"]); c2.write(r["專案名稱"]); c3.write(clean_name(r["專案負責人"])); c4.write(clean_amount(r["總金額"]))
        
        is_own = (str(r["申請人"]).strip() == curr_name)
        can_edit = (r["狀態"] in ["已儲存", "草稿", "已駁回"]) and is_own and is_active
        
        if c5.button("修改", key=f"e{i}", disabled=not can_edit): st.session_state.edit_id = r["單號"]; st.rerun()
        if c5.button("提交", key=f"s{i}", disabled=not can_edit):
            idx = db[db["單號"]==r["單號"]].index[0]
            db.at[idx, "狀態"] = "待初審"
            db.at[idx, "提交時間"] = get_taiwan_time()
            save_data(db); st.rerun()
        with c5.popover("刪除", disabled=not can_edit):
            reason = st.text_input("原因", key=f"d_res_{i}")
            if st.button("確認", key=f"d{i}"):
                idx = db[db["單號"]==r["單號"]].index[0]
                db.at[idx, "狀態"] = "已刪除"; db.at[idx, "刪除人"] = curr_name; db.at[idx, "刪除原因"] = reason
                save_data(db); st.rerun()

elif menu == "2. 專案執行長簽核":
    st.header("🔍 專案執行長簽核")
    db = load_data()
    
    # [權限邏輯] 管理員看所有待審，執行長只看自己的
    if is_admin:
        p_df = db[db["狀態"] == "待初審"]
    else:
        p_df = db[(db["狀態"] == "待初審") & (db["專案負責人"].apply(clean_name) == curr_name)]
    
    if p_df.empty: st.info("無待審單據")
    else: st.dataframe(p_df[["單號", "專案名稱", "專案負責人", "申請人", "總金額", "提交時間"]])

    for i, r in p_df.iterrows():
        with st.expander(f"{r['單號']} - {r['專案名稱']} (負責人: {clean_name(r['專案負責人'])})"):
            st.markdown(render_html(r), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            
            # [按鈕權限] 只有當負責人是登入者本人時，按鈕才亮起
            is_responsible = (clean_name(r["專案負責人"]) == curr_name)
            can_sign = is_responsible and is_active
            
            if c1.button("✅ 核准", key=f"ok{i}", disabled=not can_sign):
                idx = db[db["單號"]==r["單號"]].index[0]
                db.at[idx, "狀態"] = "待複審"; db.at[idx, "初審人"] = curr_name
                db.at[idx, "初審時間"] = get_taiwan_time()
                save_data(db); st.rerun()
                
            with c2.popover("❌ 駁回", disabled=not can_sign):
                reason = st.text_input("原因", key=f"r{i}")
                if st.button("確認", key=f"no{i}"):
                    idx = db[db["單號"]==r["單號"]].index[0]
                    db.at[idx, "狀態"] = "已駁回"; db.at[idx, "駁回原因"] = reason
                    save_data(db); st.rerun()
    
    st.divider(); st.subheader("📜 歷史紀錄")
    if is_admin:
        h_df = db[db["初審人"].notna() & (db["初審人"] != "")]
    else:
        h_df = db[db["初審人"].apply(clean_name) == curr_name]
    st.dataframe(h_df[["單號", "專案名稱", "申請人", "總金額", "初審時間", "狀態"]])

elif menu == "3. 財務長簽核":
    st.subheader("🏁 財務長簽核")
    db = load_data()
    
    if is_admin:
        p_df = db[db["狀態"] == "待複審"]
    else:
        p_df = db[(db["狀態"] == "待複審") & (curr_name == CFO_NAME)]
        
    if p_df.empty: st.info("無待審單據")
    else: st.dataframe(p_df[["單號", "專案名稱", "申請人", "總金額"]])

    for i, r in p_df.iterrows():
        with st.expander(f"{r['單號']}"):
            st.markdown(render_html(r), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            
            # [按鈕權限] 只有 CFO 本人能簽
            is_cfo = (curr_name == CFO_NAME) and is_active
            
            if c1.button("👑 核准", key=f"cok{i}", disabled=not is_cfo):
                idx = db[db["單號"]==r["單號"]].index[0]
                db.at[idx, "狀態"] = "已核准"; db.at[idx, "複審人"] = curr_name
                db.at[idx, "複審時間"] = get_taiwan_time()
                save_data(db); st.rerun()
            with c2.popover("❌ 駁回", disabled=not is_cfo):
                reason = st.text_input("原因", key=f"cr{i}")
                if st.button("確認", key=f"cno{i}"):
                    idx = db[db["單號"]==r["單號"]].index[0]
                    db.at[idx, "狀態"] = "已駁回"; db.at[idx, "駁回原因"] = reason
                    save_data(db); st.rerun()

    st.divider(); st.subheader("📜 歷史紀錄")
    if is_admin:
        f_df = db[db["複審人"].notna() & (db["複審人"] != "")]
    else:
        f_df = db[db["複審人"].apply(clean_name) == curr_name]
    st.dataframe(f_df[["單號", "專案名稱", "申請人", "總金額", "複審時間", "狀態"]])

if st.session_state.view_id:
    r = load_data(); r = r[r["單號"]==st.session_state.view_id]
    if not r.empty:
        st.markdown(render_html(r.iloc[0]), unsafe_allow_html=True)
        if st.button("關閉"): st.session_state.view_id = None; st.rerun()
