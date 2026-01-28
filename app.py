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

ADMINS = ["Anita"]
CFO_NAME = "Charles 張兆佑"

# --- 2. 核心功能函式 ---
def validate_password(pw):
    has_letter = bool(re.search(r'[a-zA-Z]', pw))
    digit_count = len(re.findall(r'\d', pw))
    return has_letter and 4 <= digit_count <= 6

def load_data():
    # 增加審計欄位：刪除人、刪除時間、刪除原因
    cols = ["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱",
            "初審人", "初審時間", "複審人", "複審時間", "刪除人", "刪除時間", "刪除原因"]
    if os.path.exists(D_FILE):
        try:
            df = pd.read_csv(D_FILE).fillna("")
            for c in cols:
                if c not in df.columns: df[c] = ""
            # 強制清理所有字串欄位空格以救援紀錄
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            return df[cols]
        except: pass
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.reset_index(drop=True).to_csv(D_FILE, index=False)

def load_staff():
    if os.path.exists(S_FILE):
        try:
            df = pd.read_csv(S_FILE).fillna("在職")
            if "password" not in df.columns: df["password"] = "0000"
            return df.reset_index(drop=True)
        except: pass
    # 設定 Andy 初始密碼為 a0000
    d = {"name": ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita"],
         "status": ["在職", "在職", "在職", "在職", "在職"],
         "password": ["a0000", "0000", "0000", "0000", "0000"]}
    df_n = pd.DataFrame(d)
    df_n.to_csv(S_FILE, index=False)
    return df_n

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False)

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

if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 3. 登入識別 ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    st.info("請選取身分並輸入密碼")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    sel_u = st.selectbox("我的身分：", u_list)
    input_pw = st.text_input("輸入密碼：", type="password")
    if st.button("確認進入"):
        if sel_u != "--- 請選擇 ---":
            target_pw = st.session_state.staff_df[st.session_state.staff_df["name"] == sel_u]["password"].values[0]
            if str(input_pw).strip() == str(target_pw).strip():
                st.session_state.user_id = sel_u.strip()
                st.rerun()
            else: st.error("❌ 密碼錯誤")
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
            idx = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].index[0]
            st.session_state.staff_df.at[idx, "password"] = new_pw
            save_staff(st.session_state.staff_df); st.success("密碼更新成功！")

if is_admin:
    st.sidebar.success("身分：管理員 / 財務行政")
    with st.sidebar.expander("⚙️ 人員與密碼管理"):
        for i, r in st.session_state.staff_df.iterrows():
            c1, c2, c3 = st.columns([1.5, 1, 1])
            c1.write(f"**{r['name']}**")
            c2.code(r["password"]) 
            if c3.button("重設", key=f"rs_{i}"):
                st.session_state.staff_df.at[i, "password"] = "0000"
                save_staff(st.session_state.staff_df); st.rerun()

if st.sidebar.button("🚪 登出系統"):
    st.session_state.user_id = None; st.rerun()

menu = st.sidebar.radio("系統導覽", ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核"])

# --- 5. 憑證渲染 HTML ---
def render_html(row):
    amt = float(row['總金額']); fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0; act = amt - fee
    b64 = get_b64_logo(); lg = '<h3>Time Lab</h3>'
    if b64: lg = f'<img src="data:image/jpeg;base64,{b64}" style="height:60px;">'
    rev_info = f"{row['初審人']} ({row['初審時間']})" if row['初審時間'] else "_________"
    cfo_info = f"{row['複審人']} ({row['複審時間']})" if row['複審時間'] else "_________"
    
    h = f'<div style="font-family:sans-serif;padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += f'<div style="display:flex;justify-content:space-between;align-items:center;"><div>{lg}</div><div><h3 style="margin:0;">時研國際設計股份有限公司</h3></div></div>'
    h += f'<hr style="border:1px solid #000;margin:10px 0;"><h2 style="text-align:center;letter-spacing:10px;">{row["類型"]}</h2>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += f'<tr><td bgcolor="#f2f2f2" width="18%" height="35">單號</td><td>&nbsp;{row["單號"]}</td><td bgcolor="#f2f2f2" width="18%">專案負責人</td><td>&nbsp;蔡松霖</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="35">專案名稱</td><td>&nbsp;{row["專案名稱"]}</td><td bgcolor="#f2f2f2">專案編號</td><td>&nbsp;{row["專案編號"]}</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="35">承辦人</td><td colspan="3">&nbsp;{row["申請人"]}</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="35">廠商</td><td>&nbsp;{row["請款廠商"]}</td><td bgcolor="#f2f2f2">付款方式</td><td>&nbsp;{row["付款方式"]}</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="35">幣別</td><td>&nbsp;{row["幣別"]}</td><td bgcolor="#f2f2f2">匯款帳戶</td><td>&nbsp;{row["匯款帳戶"]}</td></tr>'
    h += f'<tr><td bgcolor="#f2f2f2" height="80" valign="top">說明</td><td colspan="3" valign="top" style="padding:10px;">{row["請款說明"]}</td></tr>'
    h += f'<tr><td colspan="3" align="right">請款金額&nbsp;</td><td align="right">{amt:,.0f}&nbsp;</td></tr>'
    h += f'<tr><td colspan="3" align="right">提列手續費&nbsp;</td><td align="right">{fee}&nbsp;</td></tr>'
    h += f'<tr style="font-weight:bold;"><td colspan="3" align="right" height="40" bgcolor="#eee">實際請款&nbsp;</td><td align="right" bgcolor="#eee">{act:,.0f}&nbsp;</td></tr></table>'
    
    if str(row['帳戶影像Base64']) != "":
        h += '<div style="margin-top:10px;border:1px dashed #ccc;padding:10px;"><b>存摺影本：</b><br>'
        h += f'<img src="data:image/jpeg;base64,{str(row["帳戶影像Base64"])}" style="max-width:100%;max-height:220px;"></div>'
    
    if row["狀態"] == "已刪除":
        h += f'<div style="color:red;border:2px solid red;padding:10px;margin-top:10px;"><b>⚠️ 此單已於 {row["刪除時間"]} 由 {row["刪除人"]} 刪除</b><br>原因：{row["刪除原因"]}</div>'

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
if menu == "1. 填寫申請單":
    st.header("時研國際設計股份有限公司 請購/請款系統")
    ed_data = None
    if st.session_state.edit_id:
        r_f = st.session_state.db[st.session_state.db["單號"]==st.session_state.edit_id]
        if not r_f.empty: ed_data = r_f.iloc[0]; st.warning(f"📝 正在修改：{st.session_state.edit_id}")
    
    current_staff = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]["name"].tolist()
    with st.form("apply_form"):
        c1, c2 = st.columns(2)
        with c1:
            app = st.text_input("承辦人 *", value=curr_name, disabled=True) 
            pn = st.text_input("專案名稱 *", value=ed_data["專案名稱"] if ed_data is not None else "")
            exe = st.selectbox("專案執行人 *", current_staff, index=current_staff.index(ed_data["專案執行人"]) if (ed_data is not None and ed_data["專案執行人"] in current_staff) else 0)
        with c2:
            pi = st.text_input("專案編號 *", value=ed_data["專案編號"] if ed_data is not None else "")
            amt = st.number_input("總金額 *", min_value=0, value=int(ed_data["總金額"]) if ed_data is not None else 0)
            tp = st.selectbox("類型 *", ["請款單", "採購單"], index=0 if (ed_data is None or ed_data["類型"]=="請款單") else 1)
        pay = st.radio("付款方式 *", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], horizontal=True)
        vdr, acc = st.text_input("廠商", value=ed_data["請款廠商"] if ed_data is not None else ""), st.text_input("帳戶", value=ed_data["匯款帳戶"] if ed_data is not None else "")
        desc = st.text_area("說明 *", value=ed_data["請款說明"] if ed_data is not None else "")
        acc_f = st.file_uploader("上傳存摺影本", type=["jpg","png"]); ims_f = st.file_uploader("上傳報帳憑證", type=["jpg","png"], accept_multiple_files=True)
        
        if st.form_submit_button("💾 儲存內容"):
            if not (app and pn and pi and amt > 0 and desc): st.error("❌ 必填未齊！")
            else:
                new_db = st.session_state.db.copy()
                if st.session_state.edit_id:
                    idx = new_db[new_db["單號"]==st.session_state.edit_id].index[0]
                    new_db.at[idx,"申請人"], new_db.at[idx,"專案名稱"], new_db.at[idx,"專案執行人"], new_db.at[idx,"專案編號"] = app, pn, exe, pi
                    new_db.at[idx,"總金額"], new_db.at[idx,"請款說明"], new_db.at[idx,"狀態"] = amt, desc, "草稿"
                    new_db.at[idx,"申請人信箱"] = curr_name 
                    if acc_f: new_db.at[idx,"帳戶影像Base64"] = base64.b64encode(acc_f.getvalue()).decode()
                    if ims_f: new_db.at[idx,"影像Base64"] = "|".join([base64.b64encode(f.getvalue()).decode() for f in ims_f])
                    st.session_state.edit_id = None
                else:
                    tid = datetime.date.today().strftime('%Y%m%d') + "-" + f"{len(new_db)+1:02d}"
                    a_b = base64.b64encode(acc_f.getvalue()).decode() if acc_f else ""
                    i_b = "|".join([base64.b64encode(f.getvalue()).decode() for f in ims_f]) if ims_f else ""
                    nr = {"單號":tid,"日期":str(datetime.date.today()),"類型":tp,"申請人":app,"專案執行人":exe,"專案名稱":pn,"專案編號":pi,"請款說明":desc,"總金額":amt,"幣別":"TWD","付款方式":pay,"請款廠商":vdr,"匯款帳戶":acc,"帳戶影像Base64":a_b,"狀態":"草稿","影像Base64":i_b,"提交時間":"","申請人信箱":curr_name,"初審人":"","初審時間":"","複審人":"","複審時間":"","刪除人":"","刪除時間":"","刪除原因":""}
                    new_db = pd.concat([new_db, pd.DataFrame([nr])], ignore_index=True)
                st.session_state.db = new_db; save_data(new_db); st.rerun()

    st.divider(); st.subheader("📋 申請追蹤清單")
    # Anita 看全能，其他人看自己（含姓名或信箱比對）
    if is_admin: 
        disp_db = st.session_state.db
    else: 
        c_n = curr_name.strip()
        disp_db = st.session_state.db[(st.session_state.db["申請人"].str.strip() == c_n) | (st.session_state.db["申請人信箱"].str.strip() == c_n)]
    
    if disp_db.empty: st.info("目前尚無紀錄")
    else:
        # 表頭
        h_cols = st.columns([1.2, 1.8, 1, 1.5, 1, 0.6, 0.6, 0.6, 0.6, 0.6])
        h_cols[0].write("**單號**"); h_cols[1].write("**專案名稱**"); h_cols[2].write("**申請人**"); h_cols[3].write("**申請金額**"); h_cols[4].write("**狀態**")
        
        for i, r in disp_db.iterrows():
            rid = r["單號"]; stt = r["狀態"]; color = "green" if stt == "已核准" else "blue" if stt == "待複審" else "orange" if stt == "待初審" else "red" if stt == "已駁回" else "gray" if stt == "已刪除" else "black"
            cols = st.columns([1.2, 1.8, 1, 1.5, 1, 0.6, 0.6, 0.6, 0.6, 0.6])
            cols[0].write(rid); cols[1].write(r["專案名稱"]); cols[2].write(r["申請人"])
            
            # 手續費標註
            fee_tag = " :red[(已扣30)]" if r["付款方式"] == "匯款(扣30手續費)" else ""
            cols[3].markdown(f"${float(r['總金額']):,.0f}{fee_tag}")
            cols[4].markdown(f":{color}[{stt}]")
            
            # 權限邏輯：提交後 (非草稿/非駁回) 刪除與修改反灰
            is_locked = (stt not in ["草稿", "已駁回"])
            
            # 1. 修改
            if cols[5].button("修改", key=f"e_{rid}", disabled=is_locked):
                st.session_state.edit_id = rid; st.rerun()
            
            # 2. 提交
            if cols[6].button("提交", key=f"s_{rid}", disabled=is_locked):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "待初審"; st.session_state.db.at[idx, "提交時間"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M"); save_data(st.session_state.db); st.rerun()
            
            # 3. 預覽
            if cols[7].button("預覽", key=f"v_{rid}"): st.session_state.view_id = rid; st.rerun()
            
            # 4. 列印
            if cols[8].button("列印", key=f"p_{rid}"):
                js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                st.components.v1.html('<script>' + js_p + '</script>', height=0)

            # 5. 刪除 (帶原因輸入)
            with cols[9]:
                with st.popover("刪除", disabled=is_locked):
                    reason = st.text_input("請輸入刪除原因", key=f"re_{rid}")
                    if st.button("確認刪除", key=f"conf_{rid}"):
                        if not reason: st.error("原因必填")
                        else:
                            idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                            st.session_state.db.at[idx, "狀態"] = "已刪除"
                            st.session_state.db.at[idx, "刪除人"] = curr_name
                            st.session_state.db.at[idx, "刪除時間"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            st.session_state.db.at[idx, "刪除原因"] = reason
                            save_data(st.session_state.db); st.rerun()

    if st.session_state.view_id:
        st.markdown(render_html(st.session_state.db[st.session_state.db["單號"]==st.session_state.view_id].iloc[0]), unsafe_allow_html=True)
        if st.button("❌ 關閉預覽畫面"): st.session_state.view_id = None; st.rerun()

elif menu == "2. 專案執行長簽核":
    st.header("🔍 專案執行長簽核中心")
    if is_admin: p_df = st.session_state.db[st.session_state.db["狀態"]=="待初審"]
    else: p_df = st.session_state.db[(st.session_state.db["狀態"]=="待初審") & (st.session_state.db["專案執行人"].str.strip() == curr_name.strip())]
    if p_df.empty: st.info("目前無待初審單據")
    for i, r in p_df.iterrows():
        rid = r["單號"]
        with st.expander(f"待初審：{rid} - {r['專案名稱']} (執行人：{r['專案執行人']})"):
            st.markdown(render_html(r), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            can_sign = (curr_name.strip() == r["專案執行人"].strip()) and not is_admin
            if c1.button("✅ 執行長核准", key=f"ok_ceo_{rid}", disabled=not can_sign):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "待複審"
                st.session_state.db.at[idx, "初審人"], st.session_state.db.at[idx, "初審時間"] = curr_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(st.session_state.db); st.rerun()
            if c2.button("❌ 執行長駁回", key=f"no_ceo_{rid}", disabled=not can_sign):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "已駁回"; save_data(st.session_state.db); st.rerun()

elif menu == "3. 財務長簽核":
    st.header("🏁 財務長簽核中心")
    p_df = st.session_state.db[st.session_state.db["狀態"]=="待複審"]
    if p_df.empty: st.info("目前無待複審單據")
    for i, r in p_df.iterrows():
        rid = r["單號"]
        with st.expander(f"待複審：{rid} - {r['專案名稱']}"):
            st.markdown(render_html(r), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            is_cfo = (curr_name.strip() == CFO_NAME.strip())
            if c1.button("👑 財務長最終核准", key=f"ok_cfo_{rid}", disabled=not is_cfo):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "已核准"
                st.session_state.db.at[idx, "複審人"], st.session_state.db.at[idx, "複審時間"] = curr_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(st.session_state.db); st.rerun()
            if c2.button("❌ 財務長複審駁回", key=f"no_cfo_{rid}", disabled=not is_cfo):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "已駁回"; save_data(st.session_state.db); st.rerun()
