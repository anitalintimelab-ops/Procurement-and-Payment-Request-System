import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re

# --- 1. 系統環境與權限定義 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"
STAFF_LIST = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- 2. 核心功能函式 ---
def validate_password(pw):
    has_letter = bool(re.search(r'[a-zA-Z]', pw))
    digit_count = len(re.findall(r'\d', pw))
    return has_letter and 4 <= digit_count <= 6

# 萬用讀取：解決編碼與亂碼問題
def read_csv_robust(filepath):
    if not os.path.exists(filepath): return None
    encodings = ['utf-8-sig', 'utf-8', 'cp950', 'big5'] 
    for enc in encodings:
        try:
            df = pd.read_csv(filepath, encoding=enc, dtype=str).fillna("")
            return df
        except:
            continue
    return pd.DataFrame()

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱",
            "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", "刪除原因"]
    
    df = read_csv_robust(D_FILE)
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    
    for c in cols:
        if c not in df.columns: df[c] = ""
            
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    return df[cols]

def save_data(df):
    try:
        # 強制同步寫入，確保檔案內容與系統一致
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError:
        st.error("⚠️ 警告：無法寫入檔案！請檢查 `database.csv` 是否正由 Excel 開啟中。請關閉該檔案以確保資料同步。")

def load_staff():
    default_df = pd.DataFrame({
        "name": STAFF_LIST,
        "status": ["在職"] * 5,
        "password": ["0000"] * 5
    })
    df = read_csv_robust(S_FILE)
    if df is None or df.empty or "password" not in df.columns:
        default_df.to_csv(S_FILE, index=False, encoding='utf-8-sig')
        return default_df
    
    df["name"] = df["name"].str.strip()
    df["password"] = df["password"].str.strip()
    return df

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False, encoding='utf-8-sig')

def get_b64_logo():
    try:
        for f in os.listdir(B_DIR):
            fn = f.lower()
            if any(x in fn for x in [".jpg",".png",".jpeg"]):
                if "timelab" in fn or "logo" in fn:
                    p = os.path.join(B_DIR, f); im = open(p, "rb")
                    return base64.b64encode(im.read()).decode()
    except: pass
    return ""

def clean_for_js(h_str):
    return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# 初始化 Session State
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()

if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None
# [關鍵] 用於強制清空表單的金鑰
if 'form_key' not in st.session_state: st.session_state.form_key = 0 

# --- 3. 登入識別 ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    st.info("請選取您的身分並輸入密碼")
    
    staff_df = load_staff()
    u_list = ["--- 請選擇 ---"] + staff_df["name"].tolist()
    
    with st.form("login_form"):
        sel_u = st.selectbox("我的身分：", u_list)
        input_pw = st.text_input("輸入密碼：", type="password")
        submitted = st.form_submit_button("確認進入")
        
        if submitted:
            if sel_u == "--- 請選擇 ---":
                st.warning("請選擇身分")
            else:
                user_row = staff_df[staff_df["name"] == sel_u]
                if not user_row.empty:
                    stored_pw = str(user_row.iloc[0]["password"]).strip()
                    if stored_pw.endswith(".0"): stored_pw = stored_pw[:-2]
                    input_val = str(input_pw).strip()
                    
                    if input_val == stored_pw or (input_val == "0000" and stored_pw in ["nan", ""]):
                        st.session_state.user_id = sel_u
                        st.session_state.staff_df = staff_df
                        st.rerun()
                    else:
                        st.error("❌ 密碼錯誤")
                else:
                    st.error("找不到使用者資料")
    st.stop()

curr_name = st.session_state.user_id
is_admin = (curr_name in ADMINS)

# --- 4. 側邊欄 ---
st.sidebar.markdown(f"### 👤 目前登入：{curr_name}")
with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password")
    confirm_pw = st.text_input("確認新密碼", type="password")
    if st.button("更新密碼"):
        if new_pw != confirm_pw: st.error("兩次輸入不符")
        elif not validate_password(new_pw): st.error("規則：至少一英文+數字4-6位")
        else:
            staff_df = load_staff()
            if curr_name in staff_df["name"].values:
                idx = staff_df[staff_df["name"] == curr_name].index[0]
                staff_df.at[idx, "password"] = str(new_pw)
            else:
                new_row = pd.DataFrame({"name":[curr_name], "status":["在職"], "password":[new_pw]})
                staff_df = pd.concat([staff_df, new_row], ignore_index=True)
            save_staff(staff_df)
            st.session_state.staff_df = staff_df
            st.success("成功！")

if is_admin:
    st.sidebar.success("身分：管理員 / 財務行政")
    with st.sidebar.expander("⚙️ 人員管理 (密碼重置)"):
        staff_df = st.session_state.staff_df
        for i, r in staff_df.iterrows():
            c1, c2, c3 = st.columns([1.5, 1, 1])
            c1.write(f"**{r['name']}**")
            c2.code(r["password"]) 
            if c3.button("重設", key=f"rs_{i}"):
                staff_df.at[i, "password"] = "0000"
                save_staff(staff_df)
                st.session_state.staff_df = staff_df
                st.rerun()

if st.sidebar.button("🚪 登出系統"):
    st.session_state.user_id = None; st.session_state.edit_id = None; st.rerun()

menu = st.sidebar.radio("系統導覽", ["1. 填寫申請單追蹤", "2. 專案執行長簽核", "3. 財務長簽核"])

# --- 5. 憑證渲染 HTML ---
def render_html(row):
    try: amt_val = float(row['總金額'])
    except: amt_val = 0
    fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0
    act = amt_val - fee
    b64 = get_b64_logo(); lg = '<h3>Time Lab</h3>'
    if b64: lg = f'<img src="data:image/jpeg;base64,{b64}" style="height:60px;">'
    rev_info = f"{row['初審人']} ({row['初審時間']})" if row['初審時間'] else "_________"
    cfo_info = f"{row['複審人']} ({row['複審時間']})" if row['複審時間'] else "_________"
    h = f'<div style="font-family:sans-serif;padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += f'<div style="display:flex;justify-content:space-between;align-items:center;"><div>{lg}</div><div><h3 style="margin:0;">時研國際設計股份有限公司</h3></div></div>'
    h += f'<hr style="border:1px solid #000;margin:10px 0;"><h2 style="text-align:center;letter-spacing:10px;">{row["類型"]}</h2>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += f'<tr><td bgcolor="#f2f2f2" width="18%" height="35">單號</td><td>&nbsp;{row["單號"]}</td><td bgcolor="#f2f2f2" width="18%">專案負責人</td><td>&nbsp;{row["專案執行人"]}</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="35">專案名稱</td><td>&nbsp;{row["專案名稱"]}</td><td bgcolor="#f2f2f2">專案編號</td><td>&nbsp;{row["專案編號"]}</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="35">承辦人</td><td colspan="3">&nbsp;{row["申請人"]}</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="35">廠商</td><td>&nbsp;{row["請款廠商"]}</td><td bgcolor="#f2f2f2">付款方式</td><td>&nbsp;{row["付款方式"]}</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="35">幣別</td><td>&nbsp;{row["幣別"]}</td><td bgcolor="#f2f2f2">匯款帳戶</td><td>&nbsp;{row["匯款帳戶"]}</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="80" valign="top">說明</td><td colspan="3" valign="top" style="padding:10px;">{row["請款說明"]}</td></tr>'
    h += f'<tr><td colspan="3" align="right">請款金額&nbsp;</td><td align="right">{amt_val:,.0f}&nbsp;</td></tr>'
    h += f'<tr><td colspan="3" align="right">提列手續費&nbsp;</td><td align="right">{fee}&nbsp;</td></tr>'
    h += f'<tr style="font-weight:bold;"><td colspan="3" align="right" height="40" bgcolor="#eee">實際請款&nbsp;</td><td align="right" bgcolor="#eee">{act:,.0f}&nbsp;</td></tr></table>'
    if str(row['帳戶影像Base64']) != "":
        h += '<div style="margin-top:10px;border:1px dashed #ccc;padding:10px;"><b>存摺影本：</b><br>'
        h += f'<img src="data:image/jpeg;base64,{str(row["帳戶影像Base64"])}" style="max-width:100%;max-height:220px;"></div>'
    if row["狀態"] == "已刪除":
        h += f'<div style="color:red;border:2px solid red;padding:10px;margin-top:10px;"><b>⚠️ 此單已由 {row["刪除人"]} 於 {row["刪除時間"]} 刪除</b><br>原因：{row["刪除原因"]}</div>'
    h += f'<div style="display:flex;flex-direction:column;gap:15px;margin-top:40px;font-size:11px;">'
    h += f'<div style="display:flex;justify-content:space-between;"><span>承辦人：{row["申請人"]} ({row["提交時間"]})</span><span>專案執行長簽核：{rev_info}</span></div>'
    h += f'<div style="display:flex;justify-content:space-between;"><span>財務長簽核：{cfo_info}</span><span>財務簽核：_________</span></div></div></div>'
    v = ""
    if str(row['影像Base64']) != "":
        imgs = str(row['影像Base64']).split('|')
        for i, img in enumerate(imgs):
            if i % 2 == 0: v += '<div style="width:700px;margin:auto;page-break-before:always;padding:20px;">'
            v += f'<div style="height:480px;border-bottom:1px solid #ccc;margin-bottom:10px;"><img src="data:image/jpeg;base64,{img}" style="max-width:100%;max-height:100%;"></div>'
            if i % 2 == 1 or i == len(imgs)-1: v += '</div>'
    return h + v

# --- 6. 主功能流程 ---
if menu == "1. 填寫申請單追蹤":
    st.header("時研國際設計股份有限公司 請購/請款系統")
    ed_data = None
    if st.session_state.edit_id:
        r_f = st.session_state.db[st.session_state.db["單號"]==st.session_state.edit_id]
        if not r_f.empty: ed_data = r_f.iloc[0]; st.warning(f"📝 正在修改單號：{st.session_state.edit_id}")
    
    with st.form("apply_form"):
        c1, c2 = st.columns(2)
        with c1:
            app = st.text_input("承辦人 *", value=curr_name, disabled=True) 
            # 如果是修改模式，填入舊資料；否則使用空值 (依賴 form_key 清空)
            pn = st.text_input("專案名稱 *", value=ed_data["專案名稱"] if ed_data is not None else "")
            exe = st.selectbox("專案執行人 *", STAFF_LIST, index=STAFF_LIST.index(ed_data["專案執行人"]) if (ed_data is not None and ed_data["專案執行人"] in STAFF_LIST) else 0)
        with c2:
            pi = st.text_input("專案編號 *", value=ed_data["專案編號"] if ed_data is not None else "")
            try: val_amt = int(float(ed_data["總金額"])) if ed_data is not None and str(ed_data["總金額"])!="" else 0
            except: val_amt = 0
            amt = st.number_input("總金額 *", min_value=0, value=val_amt)
            tp = st.selectbox("類型 *", ["請款單", "採購單"], index=0 if (ed_data is None or ed_data["類型"]=="請款單") else 1)
        pay = st.radio("付款方式 *", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], horizontal=True)
        vdr, acc = st.text_input("廠商", value=ed_data["請款廠商"] if ed_data is not None else ""), st.text_input("帳戶", value=ed_data["匯款帳戶"] if ed_data is not None else "")
        desc = st.text_area("說明 *", value=ed_data["請款說明"] if ed_data is not None else "")
        
        # [關鍵] 使用動態 key 來強制重置上傳元件
        uploader_key = f"uploader_{st.session_state.form_key}"
        acc_f = st.file_uploader("存摺影本", type=["jpg","png"], key=f"acc_{uploader_key}")
        ims_f = st.file_uploader("報帳憑證", type=["jpg","png"], accept_multiple_files=True, key=f"ims_{uploader_key}")
        
        c_save, c_pre, c_sub, c_prt = st.columns(4)
        do_save = c_save.form_submit_button("💾 儲存內容")
        
        if do_save:
            if not (app and pn and pi and amt > 0 and desc): st.error("❌ 必填未填齊！")
            else:
                # 重新讀取 DB
                st.session_state.db = load_data()
                new_db = st.session_state.db.copy()
                
                if st.session_state.edit_id:
                    idx = new_db[new_db["單號"]==st.session_state.edit_id].index[0]
                    new_db.at[idx,"申請人"], new_db.at[idx,"專案名稱"], new_db.at[idx,"專案執行人"], new_db.at[idx,"專案編號"] = app, pn, exe, pi
                    new_db.at[idx,"總金額"], new_db.
