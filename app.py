import streamlit as st
import pandas as pd
import datetime
import os
import base64
import re
import time

# --- 1. 系統環境與權限定義 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v2.csv")

# 定義核心角色
ADMINS = ["Anita"]
CFO_NAME = "Charles"
STAFF_LIST = ["Andy", "Charles", "Eason", "Sunglin", "Anita"]

# --- 2. 自動救援資料 ---
def init_rescue_data():
    if not os.path.exists(D_FILE):
        data = {
            "單號": ["20260121-01", "20260121-02", "20260129-03", "20260129-04", "20260129-05", "20260129-06"],
            "日期": ["2026-01-21", "2026-01-21", "2026-01-29", "2026-01-29", "2026-01-29", "2026-01-29"],
            "類型": ["請款單", "請款單", "請款單", "請款單", "請款單", "請款單"],
            "申請人": ["Anita", "Andy", "Charles", "Sunglin", "Eason", "Anita"],
            "專案負責人": ["Andy", "Andy", "Andy", "Andy", "Andy", "Andy"],
            "專案名稱": ["20260120ST001", "10111111", "10111111", "10111111", "10111111", "元大方圓"],
            "專案編號": ["豪哥", "Test02", "2022222", "2022222", "2022222", "YUAN01"],
            "請款說明": ["測試說明1", "測試說明2", "2168", "2168", "2168", "工程款"],
            "總金額": ["5555", "555555", "555555", "555555", "555555", "500000"],
            "幣別": ["TWD"]*6,
            "付款方式": ["匯款(扣30手續費)"]*6,
            "請款廠商": ["廠商A", "廠商B", "20260", "20260", "20260", "元大"],
            "匯款帳戶": [""]*6, "帳戶影像Base64": [""]*6,
            "狀態": ["待初審", "已核准", "草稿", "草稿", "草稿", "待初審"],
            "影像Base64": [""]*6, 
            "提交時間": ["2026-01-21 10:00", "2026-01-21 11:00", "", "", "", "2026-01-29 15:57"],
            "申請人信箱": ["Anita", "Andy", "Charles", "Sunglin", "Eason", "Anita"],
            "初審人": ["", "Charles", "", "", "", ""],
            "初審時間": ["", "2026-01-21 14:00", "", "", "", ""],
            "複審人": ["", "Charles", "", "", "", ""],
            "複審時間": ["", "2026-01-21 15:00", "", "", "", ""],
            "刪除人": [""]*6, "刪除時間": [""]*6, "刪除原因": [""]*6
        }
        df = pd.DataFrame(data).astype(str)
        df.to_csv(D_FILE, index=False, encoding='utf-8-sig')

init_rescue_data()

# --- 3. 核心功能函式 ---
def validate_password(pw):
    has_letter = bool(re.search(r'[a-zA-Z]', pw))
    digit_count = len(re.findall(r'\d', pw))
    return has_letter and 4 <= digit_count <= 6

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
    cols = ["單號", "日期", "類型", "申請人", "專案負責人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱",
            "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", "刪除原因"]
    
    df = read_csv_robust(D_FILE)
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    
    if "專案執行人" in df.columns:
        df = df.rename(columns={"專案執行人": "專案負責人"})
    
    for c in cols:
        if c not in df.columns: df[c] = ""
            
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    return df[cols]

def save_data(df):
    try:
        df.reset_index(drop=True).to_csv(D_FILE, index=False, encoding='utf-8-sig')
    except PermissionError:
        st.error("⚠️ 嚴重警告：無法寫入檔案！請檢查 `database.csv` 是否正由 Excel 開啟中。")
        st.stop()

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
if 'form_key' not in st.session_state: st.session_state.form_key = 0 

# --- 4. 登入識別 ---
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

# --- 5. 側邊欄 ---
st.sidebar.markdown(f"### 👤 目前登入：{curr_name}")
with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password")
    confirm_pw = st.text_input("確認新密碼", type="password")
    if st.button("更新密碼"):
        if new_pw != confirm_pw: st.error("兩次輸入不符")
        elif not validate_password(new_pw): st.error("規則：至少一英文+數字4-6位")
        else:
            staff_df = load_staff()
            idx = staff_df[staff_df["name"] == curr_name].index[0]
            staff_df.at[idx, "password"] = str(new_pw)
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

menu = st.sidebar.radio("系統導覽", ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核"])

# --- 6. 憑證渲染 HTML ---
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
    h += f'<tr><td bgcolor="#f2f2f2" width="18%" height="35">單號</td><td>&nbsp;{row["單號"]}</td><td bgcolor="#f2f2f2" width="18%">專案負責人</td><td>&nbsp;{row["專案負責人"]}</td></tr>'
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

# --- 7. 主功能流程 ---
if menu == "1. 填寫申請單":
    st.header("時研國際設計股份有限公司 請購/請款系統")
    ed_data = None
    if st.session_state.edit_id:
        r_f = st.session_state.db[st.session_state.db["單號"]==st.session_state.edit_id]
        if not r_f.empty: ed_data = r_f.iloc[0]; st.warning(f"📝 正在修改單號：{st.session_state.edit_id}")
    
    with st.form("apply_form"):
        fk = st.session_state.form_key
        # [關鍵修正]：Key 加入 edit_id 資訊。
        # 如果是新增(edit_id=None)，key 會是 pn_0_new
        # 如果是修改(edit_id=20260202-02)，key 會是 pn_0_20260202-02
        # 這樣 Streamlit 就會知道這是不同的輸入框，強制從 value 參數讀取資料，解決空白問題。
        mode_suffix = st.session_state.edit_id if st.session_state.edit_id else "new"
        
        c1, c2 = st.columns(2)
        with c1:
            app = st.text_input("承辦人 *", value=curr_name, disabled=True) 
            val_pn = ed_data["專案名稱"] if ed_data is not None else ""
            pn = st.text_input("專案名稱 *", value=val_pn, key=f"pn_{fk}_{mode_suffix}")
            
            val_exe = ed_data["專案負責人"] if ed_data is not None and "專案負責人" in ed_data else STAFF_LIST[0]
            idx_exe = STAFF_LIST.index(val_exe) if val_exe in STAFF_LIST else 0
            exe = st.selectbox("專案負責人 *", STAFF_LIST, index=idx_exe, key=f"exe_{fk}_{mode_suffix}")
            
        with c2:
            val_pi = ed_data["專案編號"] if ed_data is not None else ""
            pi = st.text_input("專案編號 *", value=val_pi, key=f"pi_{fk}_{mode_suffix}")
            
            try: val_amt = int(float(ed_data["總金額"])) if ed_data is not None and str(ed_data["總金額"])!="" else 0
            except: val_amt = 0
            amt = st.number_input("總金額 *", min_value=0, value=val_amt, key=f"amt_{fk}_{mode_suffix}")
            
            idx_tp = ["請款單", "採購單"].index(ed_data["類型"]) if (ed_data is not None and ed_data["類型"] in ["請款單", "採購單"]) else 0
            tp = st.selectbox("類型 *", ["請款單", "採購單"], index=idx_tp, key=f"tp_{fk}_{mode_suffix}")
            
        pay_ops = ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"]
        idx_pay = pay_ops.index(ed_data["付款方式"]) if (ed_data is not None and ed_data["付款方式"] in pay_ops) else 0
        pay = st.radio("付款方式 *", pay_ops, index=idx_pay, horizontal=True, key=f"pay_{fk}_{mode_suffix}")
        
        val_vdr = ed_data["請款廠商"] if ed_data is not None else ""
        vdr = st.text_input("廠商", value=val_vdr, key=f"vdr_{fk}_{mode_suffix}")
        
        val_acc = ed_data["匯款帳戶"] if ed_data is not None else ""
        acc = st.text_input("帳戶", value=val_acc, key=f"acc_{fk}_{mode_suffix}")
        
        val_desc = ed_data["請款說明"] if ed_data is not None else ""
        desc = st.text_area("說明 *", value=val_desc, key=f"desc_{fk}_{mode_suffix}")
        
        acc_f = st.file_uploader("存摺影本", type=["jpg","png"], key=f"acc_f_{fk}_{mode_suffix}")
        ims_f = st.file_uploader("報帳憑證", type=["jpg","png"], accept_multiple_files=True, key=f"ims_f_{fk}_{mode_suffix}")
        
        c_save, c_pre, c_sub, c_prt = st.columns(4)
        do_save = c_save.form_submit_button("💾 儲存內容")
        
        if do_save:
            if not (app and pn and pi and amt > 0 and desc): 
                st.error("❌ 必填未填齊！")
            else:
                current_db = load_data()
                
                if st.session_state.edit_id:
                    idx = current_db[current_db["單號"]==st.session_state.edit_id].index[0]
                    current_db.at[idx,"申請人"] = app
                    current_db.at[idx,"專案名稱"] = pn
                    current_db.at[idx,"專案負責人"] = exe
                    current_db.at[idx,"專案編號"] = pi
                    current_db.at[idx,"總金額"] = amt
                    current_db.at[idx,"請款說明"] = desc
                    current_db.at[idx,"類型"] = tp
                    current_db.at[idx,"付款方式"] = pay
                    current_db.at[idx,"請款廠商"] = vdr
                    current_db.at[idx,"匯款帳戶"] = acc
                    current_db.at[idx,"狀態"] = "已儲存" 
                    current_db.at[idx,"申請人信箱"] = curr_name 
                    
                    if acc_f: current_db.at[idx,"帳戶影像Base64"] = base64.b64encode(acc_f.getvalue()).decode()
                    if ims_f: current_db.at[idx,"影像Base64"] = "|".join([base64.b64encode(f.getvalue()).decode() for f in ims_f])
                    
                    st.session_state.last_id = st.session_state.edit_id
                    st.session_state.edit_id = None
                else:
                    today_str = datetime.date.today().strftime('%Y%m%d')
                    today_ids = [str(x) for x in current_db["單號"] if str(x).startswith(today_str)]
                    if today_ids:
                        suffixes = []
                        for x in today_ids:
                            try: suffixes.append(int(x.split('-')[-1]))
                            except: pass
                        next_seq = max(suffixes) + 1 if suffixes else 1
                    else:
                        next_seq = 1
                    tid = f"{today_str}-{next_seq:02d}"
                    
                    a_b = base64.b64encode(acc_f.getvalue()).decode() if acc_f else ""
                    i_b = "|".join([base64.b64encode(f.getvalue()).decode() for f in ims_f]) if ims_f else ""
                    
                    nr = {
                        "單號":tid, "日期":str(datetime.date.today()), "類型":tp, 
                        "申請人":app, "專案負責人":exe, "專案名稱":pn, "專案編號":pi, 
                        "請款說明":desc, "總金額":amt, "幣別":"TWD", "付款方式":pay, 
                        "請款廠商":vdr, "匯款帳戶":acc, "帳戶影像Base64":a_b, 
                        "狀態":"已儲存", "影像Base64":i_b, "提交時間":"", 
                        "申請人信箱":curr_name, "初審人":"", "初審時間":"", 
                        "複審人":"", "複審時間":"", "刪除人":"", "刪除時間":"", "刪除原因":""
                    }
                    current_db = pd.concat([current_db, pd.DataFrame([nr])], ignore_index=True)
                    st.session_state.last_id = tid
                    
                    st.session_state.form_key += 1
                
                save_data(current_db)
                st.session_state.db = current_db
                st.success("資料已成功寫入！")
                st.rerun()

    if st.session_state.last_id:
        st.info(f"📍 案件已儲存：{st.session_state.last_id}")
        temp_db = load_data()
        
        target_rows = temp_db[temp_db["單號"]==st.session_state.last_id]
        if not target_rows.empty:
            l_rec = target_rows.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("🔍 線上預覽", key="v_fast"): st.session_state.view_id = st.session_state.last_id; st.rerun()
            if c2.button("🚀 提交送審", key="s_fast"):
                idx = temp_db[temp_db["單號"]==st.session_state.last_id].index[0]
                temp_db.at[idx, "狀態"] = "待初審"
                temp_db.at[idx, "提交時間"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(temp_db)
                st.success("已提交！")
                st.session_state.last_id = None; st.rerun()
            if c3.button("🖨️ 線上列印", key="p_fast"):
                js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(l_rec)) + "');w.print();w.close();"
                st.components.v1.html('<script>' + js_p + '</script>', height=0)
            if c4.button("🆕 填下一筆", key="n_fast"): st.session_state.last_id = None; st.rerun()
        else:
            st.warning("⚠️ 找不到該筆資料，可能已被刪除。")

    st.divider(); st.subheader("📋 申請追蹤清單")
    
    disp_db = load_data()
    if is_admin: 
        final_db = disp_db 
    else: 
        c_n = curr_name.strip()
        mask = (disp_db["申請人"].str.contains(c_n, case=False, na=False)) | \
               (disp_db["申請人信箱"].str.contains(c_n, case=False, na=False))
        final_db = disp_db[mask]
    
    if final_db.empty: st.info("目前尚無紀錄")
    else:
        h_cols = st.columns([1.2, 1.8, 1, 1.2, 1, 0.6, 0.6, 0.6, 0.6, 0.6])
        h_cols[0].write("**單號**"); h_cols[1].write("**專案名稱**"); h_cols[2].write("**申請人**"); h_cols[3].write("**金額**"); h_cols[4].write("**狀態**")
        for i, r in final_db.iterrows():
            rid = r["單號"]; stt = r["狀態"]; owner = r["申請人"]
            
            color = "blue" if stt in ["已儲存", "草稿"] else "orange" if stt in ["待初審", "待複審"] else "green" if stt == "已核准" else "red" if stt == "已駁回" else "gray"
            cols = st.columns([1.2, 1.8, 1, 1.2, 1, 0.6, 0.6, 0.6, 0.6, 0.6])
            cols[0].write(rid); cols[1].write(r["專案名稱"]); cols[2].write(owner)
            fee_tag = " :red[(已扣30)]" if r["付款方式"] == "匯款(扣30手續費)" else ""
            try: f_amt = float(r['總金額'])
            except: f_amt = 0
            cols[3].markdown(f"${f_amt:,.0f}{fee_tag}"); cols[4].markdown(f":{color}[{stt}]")
            
            is_editable_status = (stt in ["已儲存", "草稿", "已駁回"])
            is_own = (curr_name.strip() == str(owner).strip())
            enable_action = (is_own and is_editable_status)
            
            if cols[5].button("修改", key=f"e_{rid}_{i}", disabled=not enable_action): st.session_state.edit_id = rid; st.rerun()
            if cols[6].button("提交", key=f"s_{rid}_{i}", disabled=not enable_action):
                idx = disp_db[disp_db["單號"]==rid].index[0]
                disp_db.at[idx, "狀態"] = "待初審"; disp_db.at[idx, "提交時間"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(disp_db); st.rerun()
            if cols[7].button("預覽", key=f"v_{rid}_{i}"): st.session_state.view_id = rid; st.rerun()
            if cols[8].button("列印", key=f"p_{rid}_{i}"):
                js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                st.components.v1.html('<script>' + js_p + '</script>', height=0)
            with cols[9]:
                with st.popover("刪除", disabled=not enable_action):
                    reason = st.text_input("刪除原因", key=f"re_{rid}_{i}")
                    if st.button("確認", key=f"conf_{rid}_{i}"):
                        if reason:
                            idx = disp_db[disp_db["單號"]==rid].index[0]
                            disp_db.at[idx, "狀態"] = "已刪除"; disp_db.at[idx, "刪除人"] = curr_name; disp_db.at[idx, "刪除時間"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M"); disp_db.at[idx, "刪除原因"] = reason
                            save_data(disp_db); st.rerun()

    if st.session_state.view_id:
        target_rows = st.session_state.db[st.session_state.db["單號"] == st.session_state.view_id]
        if not target_rows.empty:
            st.markdown(render_html(target_rows.iloc[0]), unsafe_allow_html=True)
            if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()
        else:
            st.error("找不到該單據，可能已被刪除。")
            if st.button("關閉"): st.session_state.view_id = None; st.rerun()

elif menu == "2. 專案執行長簽核":
    st.header("🔍 專案執行長簽核中心")
    if is_admin: p_df = st.session_state.db[st.session_state.db["狀態"]=="待初審"]
    else: p_df = st.session_state.db[(st.session_state.db["狀態"]=="待初審") & (st.session_state.db["專案負責人"].str.strip() == curr_name.strip())]
    
    if not p_df.empty:
        st.write("#### 待處理單據清單")
        st.dataframe(p_df[["單號", "專案名稱", "申請人", "總金額", "提交時間"]], use_container_width=True)
    else:
        st.info("目前無待初審單據")

    for i, r in p_df.iterrows():
        rid = r["單號"]
        with st.expander(f"待初審：{rid} - {r['專案名稱']} (負責人：{r['專案負責人']})"):
            st.markdown(render_html(r), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            can_sign = (curr_name.strip() == r["專案負責人"].strip()) and not is_admin
            if c1.button("✅ 核准", key=f"ok_ceo_{rid}_{i}", disabled=not can_sign):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "待複審"; st.session_state.db.at[idx, "初審人"], st.session_state.db.at[idx, "初審時間"] = curr_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(st.session_state.db); st.rerun()
            if c2.button("❌ 駁回", key=f"no_ceo_{rid}_{i}", disabled=not can_sign):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "已駁回"; save_data(st.session_state.db); st.rerun()
    
    st.divider(); st.subheader("📜 已簽核歷史紀錄")
    h_df = st.session_state.db[st.session_state.db["初審人"].str.contains(curr_name, na=False)]
    if h_df.empty: st.info("尚無紀錄")
    else: st.dataframe(h_df[["單號", "專案名稱", "申請人", "總金額", "初審時間", "狀態"]], use_container_width=True)

elif menu == "3. 財務長簽核":
    st.header("🏁 財務長簽核中心")
    p_df = st.session_state.db[st.session_state.db["狀態"]=="待複審"]
    
    if not p_df.empty:
        st.write("#### 待處理單據清單")
        st.dataframe(p_df[["單號", "專案名稱", "申請人", "總金額", "初審人"]], use_container_width=True)
    else:
        st.info("目前無待複審單據")

    for i, r in p_df.iterrows():
        rid = r["單號"]
        with st.expander(f"待複審：{rid} - {r['專案名稱']}"):
            st.markdown(render_html(r), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            is_cfo = (curr_name.strip() == CFO_NAME) and not is_admin
            if c1.button("👑 最終核准", key=f"ok_cfo_{rid}_{i}", disabled=not is_cfo):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "已核准"; st.session_state.db.at[idx, "複審人"], st.session_state.db.at[idx, "複審時間"] = curr_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(st.session_state.db); st.rerun()
            if c2.button("❌ 財務長駁回", key=f"no_cfo_{rid}_{i}", disabled=not is_cfo):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "已駁回"; save_data(st.session_state.db); st.rerun()

    st.divider(); st.subheader("📜 已簽核歷史紀錄")
    f_df = st.session_state.db[st.session_state.db["複審人"].str.contains(curr_name, na=False)]
    if f_df.empty: st.info("尚無紀錄")
    else: st.dataframe(f_df[["單號", "專案名稱", "申請人", "總金額", "複審時間", "狀態"]], use_container_width=True)
