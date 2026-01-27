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

MANAGERS = ["Anita", "Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖"]

# --- 密碼驗證邏輯 ---
def validate_password(pw):
    # 規則：至少一個英文，且數字需為 4-6 位
    has_letter = bool(re.search(r'[a-zA-Z]', pw))
    digit_count = len(re.findall(r'\d', pw))
    return has_letter and 4 <= digit_count <= 6

def load_data():
    cols = ["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", 
            "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", 
            "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"]
    if os.path.exists(D_FILE):
        try:
            df = pd.read_csv(D_FILE).fillna("")
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: pass
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.reset_index(drop=True).to_csv(D_FILE, index=False)

def load_staff():
    if os.path.exists(S_FILE):
        try:
            df = pd.read_csv(S_FILE).fillna("在職")
            # 如果舊資料沒有密碼欄位，自動補上預設值 0000
            if "password" not in df.columns:
                df["password"] = "0000"
            return df.reset_index(drop=True)
        except: pass
    d = {"name": ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita"],
         "status": ["在職", "在職", "在職", "在職", "在職"],
         "password": ["0000", "0000", "0000", "0000", "0000"]}
    return pd.DataFrame(d)

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
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入識別畫面 ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    st.info("請選取您的身分並輸入密碼")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    sel_u = st.selectbox("我的身分：", u_list)
    input_pw = st.text_input("輸入密碼：", type="password")
    
    if st.button("確認進入"):
        if sel_u != "--- 請選擇 ---":
            # 驗證密碼
            target_pw = st.session_state.staff_df[st.session_state.staff_df["name"] == sel_u]["password"].values[0]
            if input_pw == str(target_pw):
                st.session_state.user_id = sel_u
                st.rerun()
            else:
                st.error("❌ 密碼錯誤，請重新輸入。")
    st.stop()

curr_name = st.session_state.user_id
is_admin = (curr_name == "Anita")
is_manager = (curr_name in MANAGERS)

# --- 3. 側邊欄工具與選單過濾 ---
st.sidebar.markdown(f"### 👤 目前登入：{curr_name}")

# --- 個人設定：修改密碼 ---
with st.sidebar.expander("🔐 修改我的密碼"):
    new_pw = st.text_input("新密碼", type="password", help="需包含至少一個英文字母且數字為 4-6 位")
    confirm_pw = st.text_input("確認新密碼", type="password")
    if st.button("更新密碼"):
        if new_pw != confirm_pw:
            st.error("兩次輸入不符")
        elif not validate_password(new_pw):
            st.error("不符合規則：至少一英文+數字4-6位")
        else:
            idx = st.session_state.staff_df[st.session_state.staff_df["name"] == curr_name].index[0]
            st.session_state.staff_df.at[idx, "password"] = new_pw
            save_staff(st.session_state.staff_df)
            st.success("密碼修改成功！")

if is_admin:
    st.sidebar.success("身分：管理員")
    with st.sidebar.expander("⚙️ 管理員工具"):
        new_p = st.text_input("1. 新增同事姓名")
        if st.button("➕ 確認新增"):
            if not new_p: st.sidebar.warning("請輸入姓名")
            elif new_p in st.session_state.staff_df["name"].tolist():
                st.sidebar.error("該員已重複新增")
            else:
                new_row = pd.DataFrame({"name": [new_p], "status": ["在職"], "password": ["0000"]})
                st.session_state.staff_df = pd.concat([st.session_state.staff_df, new_row], ignore_index=True)
                save_staff(st.session_state.staff_df)
                st.sidebar.success("該員新增完成 (預設密碼 0000)")
                st.rerun()
        st.divider()
        st.write("2. 人員與密碼管理")
        for i, r in st.session_state.staff_df.iterrows():
            if r["name"] == "Anita" and not is_admin: continue 
            with st.container():
                c1, c2, c3 = st.columns([1.5, 1.5, 1])
                c1.write(f"**{r['name']}**")
                # 管理員可見密碼
                c2.code(r["password"])
                if c3.button("重設", key=f"reset_pw_{i}", help="恢復為 0000"):
                    st.session_state.staff_df.at[i, "password"] = "0000"
                    save_staff(st.session_state.staff_df)
                    st.toast(f"{r['name']} 密碼已重設")
                    st.rerun()
                
                # 離職復職控制
                c4, c5 = st.columns([2, 1])
                if r["name"] != "Anita":
                    if r["status"] == "在職":
                        if c5.button("離職", key="res_"+str(i)):
                            st.session_state.staff_df.at[i,"status"]="離職"; save_staff(st.session_state.staff_df); st.rerun()
                    else:
                        if c5.button("復職", key="act_"+str(i)):
                            st.session_state.staff_df.at[i,"status"]="在職"; save_staff(st.session_state.staff_df); st.rerun()
                st.divider()
elif is_manager:
    st.sidebar.info("身分：審核主管")
else:
    st.sidebar.info("身分：申請人")

if st.sidebar.button("🚪 登出系統"):
    st.session_state.user_id = None; st.session_state.last_id = None; st.rerun()

# --- 4. HTML 排版 (略，同原始代碼) ---
def render_html(row):
    amt = float(row['總金額']); fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0; act = amt - fee
    b64 = get_b64_logo(); lg = '<h3>Time Lab</h3>'
    if b64: lg = '<img src="data:image/jpeg;base64,' + b64 + '" style="height:60px;">'
    h = '<div style="font-family:sans-serif;padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += '<div style="display:flex;justify-content:space-between;align-items:center;"><div>' + lg + '</div><div><h3 style="margin:0;">時研國際設計股份有限公司</h3></div></div>'
    h += '<hr style="border:1px solid #000;margin:10px 0;"><h2 style="text-align:center;letter-spacing:10px;">' + str(row["類型"]) + '</h2>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += '<tr><td bgcolor="#f2f2f2" width="18%" height="35">單號</td>'
    h += '<td>&nbsp;' + str(row["單號"]) + '</td>'
    h += '<td bgcolor="#f2f2f2" width="18%">專案負責人</td><td>&nbsp;蔡松霖</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">專案名稱</td><td>&nbsp;' + str(row["專案名稱"]) + '</td>'
    h += '<td bgcolor="#f2f2f2">專案編號</td><td>&nbsp;' + str(row["專案編號"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">承辦人</td><td colspan="3">&nbsp;' + str(row["申請人"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">廠商</td><td>&nbsp;' + str(row["請款廠商"]) + '</td>'
    h += '<td bgcolor="#f2f2f2">付款方式</td><td>&nbsp;' + str(row["付款方式"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">幣別</td><td>&nbsp;' + str(row["幣別"]) + '</td>'
    h += '<td bgcolor="#f2f2f2">匯款帳戶</td><td>&nbsp;' + str(row["匯款帳戶"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="80" valign="top">說明</td>'
    h += '<td colspan="3" valign="top" style="padding:10px;">' + str(row["請款說明"]) + '</td></tr>'
    h += '<tr><td colspan="3" align="right">請款金額&nbsp;</td><td align="right">' + f"{amt:,.0f}" + '&nbsp;</td></tr>'
    h += '<tr><td colspan="3" align="right">提列手續費&nbsp;</td><td align="right">' + str(fee) + '&nbsp;</td></tr>'
    h += '<tr style="font-weight:bold;"><td colspan="3" align="right" height="40" bgcolor="#eee">實際請款&nbsp;</td>'
    h += '<td align="right" bgcolor="#eee">' + f"{act:,.0f}" + '&nbsp;</td></tr></table>'
    if str(row['帳戶影像Base64']) != "":
        h += '<div style="margin-top:10px;border:1px dashed #ccc;padding:10px;"><b>存摺影本：</b><br>'
        h += '<img src="data:image/jpeg;base64,' + str(row["帳戶影像Base64"]) + '" style="max-width:100%;max-height:220px;"></div>'
    h += '<div style="display:flex;flex-direction:column;gap:15px;margin-top:40px;font-size:11px;">'
    h += '<div style="display:flex;justify-content:space-between;"><span>承辦人簽核：' + str(row["申請人"]) 
    if str(row["提交時間"]) != "": h += ' (' + str(row["提交時間"]) + ')'
    h += '</span><span>專案合夥人簽核：_________</span></div>'
    h += '<div style="display:flex;justify-content:space-between;"><span>財務執行長簽核：_________</span><span>財務簽核：_________</span></div></div></div>'
    v = ""
    if str(row['影像Base64']) != "":
        imgs = str(row['影像Base64']).split('|')
        for i, img in enumerate(imgs):
            if i % 2 == 0: v += '<div style="width:700px;margin:auto;page-break-before:always;padding:20px;">'
            if i == 0: v += '<b style="font-size:16px;">憑證：</b><br><br>'
            v += '<div style="height:480px;border-bottom:1px solid #ccc;margin-bottom:10px;"><img src="data:image/jpeg;base64,' + img + '" style="max-width:100%;max-height:100%;"></div>'
            if i % 2 == 1 or i == len(imgs)-1: v += '</div>'
    return h + v

# --- 5. 主功能流程 (略，同原始代碼) ---
m_opts = ["1. 填寫申請單"]
if is_manager:
    m_opts.append("2. 簽核中心")
menu = st.sidebar.radio("系統導覽", m_opts)

# (後續程式碼邏輯與原版一致，僅在載入資料時會自動處理密碼欄位)
# ... [省略後續填寫與簽核邏輯，與您提供的內容相同] ...
if menu == "1. 填寫申請單":
    st.header("時研國際設計股份有限公司 請購/請款系統")
    ed_data = None
    if st.session_state.edit_id:
        r_f = st.session_state.db[st.session_state.db["單號"]==st.session_state.edit_id]
        if not r_f.empty:
            ed_data = r_f.iloc[0]; st.warning("📝 正在修改單號：" + str(st.session_state.edit_id))
    current_staff = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]["name"].tolist()
    with st.form("apply_form"):
        c1, c2 = st.columns(2)
        with c1:
            app = st.text_input("承辦人 *", value=curr_name if ed_data is None else ed_data["申請人"]) 
            pn = st.text_input("專案名稱 *", value=ed_data["專案名稱"] if ed_data is not None else "")
            exe = st.selectbox("專案執行人 *", current_staff, index=current_staff.index(ed_data["專案執行人"]) if (ed_data is not None and ed_data["專案執行人"] in current_staff) else 0)
        with c2:
            pi = st.text_input("專案編號 *", value=ed_data["專案編號"] if ed_data is not None else "")
            amt = st.number_input("總金額 *", min_value=0, value=int(ed_data["總金額"]) if ed_data is not None else 0)
            tp = st.selectbox("類型 *", ["請款單", "採購單"])
        p_list = ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"]
        pay = st.radio("付款方式 *", p_list, horizontal=True)
        vdr, acc = st.text_input("廠商", value=ed_data["請款廠商"] if ed_data is not None else ""), st.text_input("帳戶", value=ed_data["匯款帳戶"] if ed_data is not None else "")
        desc = st.text_area("說明 *", value=ed_data["請款說明"] if ed_data is not None else "")
        st.divider(); st.subheader("📷 影像管理")
        del_b, del_v = False, []
        if ed_data is not None:
            if str(ed_data["帳戶影像Base64"]) != "":
                st.image("data:image/jpeg;base64," + str(ed_data['帳戶影像Base64']), width=150); del_b = st.checkbox("🗑️ 刪除目前存摺")
            if str(ed_data["影像Base64"]) != "":
                v_ims = str(ed_data["影像Base64"]).split('|'); v_cs = st.columns(4)
                for idx, v_im in enumerate(v_ims):
                    with v_cs[idx % 4]:
                        st.image("data:image/jpeg;base64," + str(v_im), use_container_width=True)
                        if st.checkbox("刪除影像 " + str(idx+1), key="dv_"+str(idx)): del_v.append(idx)
        acc_f = st.file_uploader("上傳新存摺", type=["jpg","png"])
        ims_f = st.file_uploader("上傳新憑證", type=["jpg","png"], accept_multiple_files=True)
        if st.form_submit_button("💾 儲存草稿內容"):
            if not (app and pn and pi and amt > 0 and desc): st.error("❌ 必填未填齊！")
            else:
                new_db = st.session_state.db.copy()
                if st.session_state.edit_id:
                    idx = new_db[new_db["單號"]==st.session_state.edit_id].index[0]
                    new_db.at[idx,"申請人"], new_db.at[idx,"專案名稱"] = app, pn
                    new_db.at[idx,"總金額"], new_db.at[idx,"請款說明"], new_db.at[idx,"狀態"] = amt, desc, "草稿"
                    if del_b: new_db.at[idx,"帳戶影像Base64"] = ""
                    if acc_f: new_db.at[idx,"帳戶影像Base64"] = base64.b64encode(acc_f.getvalue()).decode()
                    old_v = str(ed_data["影像Base64"]).split('|') if str(ed_data["影像Base64"]) != "" else []
                    new_db.at[idx,"影像Base64"] = "|".join([img for i, img in enumerate(old_v) if i not in del_v] + [base64.b64encode(f.getvalue()).decode() for f in ims_f])
                    tid = st.session_state.edit_id; st.session_state.edit_id = None
                else:
                    tid = datetime.date.today().strftime('%Y%m%d') + "-" + f"{len(new_db)+1:02d}"
                    a_b, i_b = base64.b64encode(acc_f.getvalue()).decode() if acc_f else "", "|".join([base64.b64encode(f.getvalue()).decode() for f in ims_f]) if ims_f else ""
                    nr = {"單號":tid,"日期":str(datetime.date.today()),"類型":tp,"申請人":app,"專案執行人":exe,"專案名稱":pn,"專案編號":pi,"請款說明":desc,"總金額":amt,"幣別":"TWD","付款方式":pay,"請款廠商":vdr,"匯款帳戶":acc,"帳戶影像Base64":a_b,"狀態":"草稿","影像Base64":i_b,"提交時間":"","申請人信箱":curr_name}
                    new_db = pd.concat([new_db, pd.DataFrame([nr])], ignore_index=True)
                st.session_state.db = new_db; save_data(new_db); st.session_state.last_id = tid; st.rerun()

    if st.session_state.last_id:
        st.divider(); st.subheader("🏁 存檔成功！後續作業引導")
        curr_rec = st.session_state.db[st.session_state.db["單號"]==st.session_state.last_id].iloc[0]
        if curr_rec["狀態"] in ["草稿", "已駁回"]:
            st.info("📍 目前編輯案件：" + str(st.session_state.last_id))
            px, py, pz, pw = st.columns([2, 2, 2, 3])
            if px.button("🔍 線上預覽", key="v_gui"): st.session_state.view_id = st.session_state.last_id
            if py.button("🚀 提交送審", key="s_gui"):
                idx_s = st.session_state.db[st.session_state.db["單號"]==st.session_state.last_id].index[0]
                st.session_state.db.at[idx_s, "狀態"] = "待簽核"
                st.session_state.db.at[idx_s, "提交時間"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(st.session_state.db); st.success("✅ 已送交簽核中心！"); st.session_state.last_id = None; st.rerun()
            if pz.button("🖨️ 線上列印", key="i_gui"):
                js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(curr_rec)) + "');w.print();w.close();"
                st.components.v1.html('<script>' + js_p + '</script>', height=0)
            if pw.button("🆕 填寫下一筆", key="n_gui"): st.session_state.last_id = None; st.rerun()
    if st.session_state.view_id:
        st.markdown(render_html(st.session_state.db[st.session_state.db["單號"]==st.session_state.view_id].iloc[0]), unsafe_allow_html=True)
        if st.button("❌ 關閉預覽畫面"): st.session_state.view_id = None; st.rerun()
    st.divider(); st.subheader("📋 申請追蹤清單")
    disp_db = st.session_state.db if is_admin else st.session_state.db[st.session_state.db["申請人信箱"] == curr_name]
    if disp_db.empty: st.info("目前尚無紀錄")
    else:
        cols_h = st.columns([1.5, 2, 1.2, 1.2, 1.2, 0.8, 0.8, 0.8, 0.8])
        cols_h[0].write("**單號**"); cols_h[1].write("**專案名稱**"); cols_h[2].write("**申請人**")
        cols_h[3].write("**金額**"); cols_h[4].write("**狀態**")
        for i, r in disp_db.reset_index(drop=True).iterrows():
            rid = r["單號"]; lock = r["狀態"] in ["待簽核", "已核准"]
            cols = st.columns([1.5, 2, 1.2, 1.2, 1.2, 0.8, 0.8, 0.8, 0.8])
            cols[0].write(rid); cols[1].write(r["專案名稱"]); cols[2].write(r["申請人"])
            cols[3].write(f"${r['總金額']:,.0f}"); cols[4].markdown(":" + ('green' if r['狀態']=='已核准' else 'red' if r['狀態']=='聯駁回' else 'blue' if r['狀態']=='草稿' else 'orange') + "[" + r['狀態'] + "]")
            if cols[5].button("修改", key="e_"+rid, disabled=lock): st.session_state.edit_id = rid; st.rerun()
            if cols[6].button("刪除", key="d_"+rid, disabled=lock): 
                st.session_state.db = st.session_state.db[st.session_state.db["單號"]!=rid]; save_data(st.session_state.db); st.rerun()
            if cols[7].button("預覽", key="v_"+rid): st.session_state.view_id = rid; st.rerun()
            if cols[8].button("列印", key="p_"+rid):
                js_p = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
                st.components.v1.html('<script>' + js_p + '</script>', height=0)
elif menu == "2. 簽核中心":
    st.header("⚖️ 主管簽核中心")
    p_df = st.session_state.db[st.session_state.db["狀態"]=="待簽核"]
    if p_df.empty: st.info("目前無待簽核單據")
    for i, r in p_df.iterrows():
        rid = r["單號"]
        with st.expander("待審：" + rid + " - " + r['專案名稱']):
            st.markdown(render_html(r), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✅ 核准", key="ok_"+rid):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "已核准"; save_data(st.session_state.db); st.rerun()
            if c2.button("❌ 駁回", key="no_"+rid):
                idx = st.session_state.db[st.session_state.db["單號"]==rid].index[0]
                st.session_state.db.at[idx, "狀態"] = "已駁回"; save_data(st.session_state.db); st.rerun()
