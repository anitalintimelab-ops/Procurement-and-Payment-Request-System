import streamlit as st
import pandas as pd
import datetime
import os
import base64

# --- 1. 系統環境設定 ---
st.set_page_config(page_title="時研-管理系統", layout="wide")
B_DIR = os.path.dirname(os.path.abspath(__file__))
D_FILE = os.path.join(B_DIR, "database.csv")
S_FILE = os.path.join(B_DIR, "staff_v9.csv") 

# 人員順序：Anita 排在 蔡松霖 之後
MANAGERS = ["Andy 陳俊嘉", "Charles 張兆佑", "Eason 何益賢", "Sunglin 蔡松霖", "Anita 林敬芸", "Wish 宋威績"]

def load_data():
    # 確保所有必備欄位都在裡面
    cols = ["單號", "日期", "類型", "申請人", "專案執行人", "專案名稱", "專案編號", "請款說明", "總金額", "幣別", "付款方式", "請款廠商", "匯款帳戶", "帳戶影像Base64", "狀態", "影像Base64", "提交時間", "申請人信箱"]
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
            df = pd.read_csv(S_FILE, dtype={'password': str}).fillna("在職")
            return df.reset_index(drop=True)
        except: pass
    d = {"name": MANAGERS, "status": ["在職"] * len(MANAGERS), "password": ["0000"] * len(MANAGERS)}
    return pd.DataFrame(d)

def save_staff(df):
    df.reset_index(drop=True).to_csv(S_FILE, index=False)

def clean_for_js(h_str):
    return h_str.replace('\n', '').replace('\r', '').replace("'", "\\'")

# 初始化 session 狀態
if 'db' not in st.session_state: st.session_state.db = load_data()
if 'staff_df' not in st.session_state: st.session_state.staff_df = load_staff()
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'last_id' not in st.session_state: st.session_state.last_id = None
if 'view_id' not in st.session_state: st.session_state.view_id = None

# --- 2. 登入識別 (預設密碼 0000) ---
if st.session_state.user_id is None:
    st.header("🏢 時研國際 - 內部管理系統")
    active_s = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]
    u_list = ["--- 請選擇 ---"] + active_s["name"].tolist()
    sel_u = st.selectbox("我的身分：", u_list)
    if sel_u != "--- 請選擇 ---":
        input_pwd = st.text_input("輸入密碼 (預設 0000)：", type="password")
        if st.button("確認進入"):
            correct_pwd = st.session_state.staff_df[st.session_state.staff_df["name"] == sel_u]["password"].values[0]
            if input_pwd == str(correct_pwd):
                st.session_state.user_id = sel_u
                st.rerun()
            else: st.error("❌ 密碼錯誤")
    st.stop()

curr_name = st.session_state.user_id
is_admin = ("Anita" in curr_name)

# --- 3. 側邊欄：密碼與管理員 ---
st.sidebar.markdown(f"### 👤 {curr_name}")
if is_admin:
    with st.sidebar.expander("🛠️ 管理員工具"):
        target_u = st.selectbox("重置密碼", st.session_state.staff_df["name"].tolist())
        if st.button("確認恢復 0000"):
            idx = st.session_state.staff_df[st.session_state.staff_df["name"]==target_u].index[0]
            st.session_state.staff_df.at[idx, "password"] = "0000"
            save_staff(st.session_state.staff_df); st.success("已重置")
        st.divider()
        csv_data = st.session_state.db.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 database.csv 備份", csv_data, f"backup_{datetime.date.today()}.csv")

if st.sidebar.button("🚪 登出系統"):
    st.session_state.user_id = None; st.rerun()

# --- 4. HTML 列印渲染 (確保 廠商、幣別 出現) ---
def render_html(row):
    amt = float(row['總金額']); fee = 30 if row['付款方式'] == "匯款(扣30手續費)" else 0; act = amt - fee
    h = '<div style="font-family:sans-serif;padding:20px;border:2px solid #000;width:680px;margin:auto;background:#fff;color:#000;">'
    h += '<div style="display:flex;justify-content:space-between;align-items:center;"><div><h3>Time Lab</h3></div><div><h4 style="margin:0;">時研國際設計股份有限公司</h4></div></div>'
    h += '<hr style="border:1px solid #000;margin:10px 0;"><h2 style="text-align:center;letter-spacing:10px;">' + str(row["類型"]) + '</h2>'
    h += '<table style="width:100%;border-collapse:collapse;font-size:14px;" border="1">'
    h += '<tr><td bgcolor="#f2f2f2" width="18%" height="35">單號</td><td>&nbsp;' + str(row["單號"]) + '</td><td bgcolor="#f2f2f2" width="18%">專案負責人</td><td>&nbsp;蔡松霖</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">專案名稱</td><td>&nbsp;' + str(row["專案名稱"]) + '</td><td bgcolor="#f2f2f2">專案編號</td><td>&nbsp;' + str(row["專案編號"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">承辦人</td><td colspan="3">&nbsp;' + str(row["申請人"]) + '</td></tr>'
    # 這裡確保「請款廠商」和「幣別」出現
    h += '<tr><td bgcolor="#f2f2f2" height="35">請款廠商</td><td>&nbsp;' + str(row["請款廠商"]) + '</td><td bgcolor="#f2f2f2">付款方式</td><td>&nbsp;' + str(row["付款方式"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="35">幣別</td><td>&nbsp;' + str(row["幣別"]) + '</td><td bgcolor="#f2f2f2">匯款帳戶</td><td>&nbsp;' + str(row["匯款帳戶"]) + '</td></tr>'
    h += '<tr><td bgcolor="#f2f2f2" height="60" valign="top">內容說明</td><td colspan="3" valign="top" style="padding:10px;">' + str(row["請款說明"]) + '</td></tr>'
    h += '<tr><td colspan="3" align="right">總金額&nbsp;</td><td align="right">' + f"{amt:,.0f}" + '&nbsp;</td></tr>'
    h += '<tr style="font-weight:bold;background:#eee;"><td colspan="3" align="right" height="35">實際請款 (扣除手續費)&nbsp;</td><td align="right">' + f"{act:,.0f}" + '&nbsp;</td></tr></table>'
    
    # 四大簽核欄位
    h += '<div style="margin-top:40px;display:grid;grid-template-columns:1fr 1fr;gap:20px;font-size:12px;">'
    h += '<div><b>承辦人簽核：</b>' + str(row["申請人"]) + '</div><div><b>專案合夥人簽核：</b>____________________</div>'
    h += '<div><b>財務執行長簽核：</b>____________________</div><div><b>財務簽核：</b>____________________</div></div>'
    
    if str(row['帳戶影像Base64']) != "":
        h += '<div style="margin-top:20px;border:1px dashed #ccc;padding:10px;"><b>存摺影本：</b><br><img src="data:image/jpeg;base64,' + str(row["帳戶影像Base64"]) + '" style="max-width:100%;max-height:200px;"></div>'
    
    v = ""
    if str(row['影像Base64']) != "":
        imgs = str(row['影像Base64']).split('|')
        for i, img in enumerate(imgs):
            v += '<div style="page-break-before:always;padding:20px;width:680px;margin:auto;border:1px solid #eee;">'
            v += '<b>憑證照片 (' + str(i+1) + ')：</b><br><br><img src="data:image/jpeg;base64,' + img + '" style="max-width:100%;"></div>'
    return h + '</div>' + v

# --- 5. 填單流程 ---
menu = st.sidebar.radio("導覽", ["1. 填寫申請單", "2. 簽核中心"])

if menu == "1. 填寫申請單":
    st.header("時研國際設計 - 請購/請款系統")
    s_list = st.session_state.staff_df[st.session_state.staff_df["status"]=="在職"]["name"].tolist()
    
    with st.form("apply_form"):
        c1, c2 = st.columns(2)
        with c1:
            pn = st.text_input("專案名稱 *")
            exe = st.selectbox("專案執行人 *", s_list, index=s_list.index(curr_name) if curr_name in s_list else 0)
            # 確保填寫區有廠商
            vdr = st.text_input("請款廠商")
        with c2:
            pi = st.text_input("專案編號 *")
            amt = st.number_input("總金額 *", min_value=0)
            # 確保填寫區有幣別
            cur = st.selectbox("幣別", ["TWD", "USD", "HKD", "CNY", "EUR"])
        tp = st.selectbox("類型 *", ["請款單", "採購單"])
        pay = st.radio("付款方式 *", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], horizontal=True)
        acc = st.text_input("匯款帳戶 (若選匯款)")
        desc = st.text_area("內容說明 *")
        acc_f = st.file_uploader("📷 上傳存摺", type=["jpg","png"])
        ims_f = st.file_uploader("📷 上傳憑證 (多張)", type=["jpg","png"], accept_multiple_files=True)
        
        if st.form_submit_button("💾 儲存草稿"):
            if not (pn and pi and amt > 0 and desc): st.error("❌ 必填欄位未填")
            else:
                tid = datetime.date.today().strftime('%Y%m%d') + "-" + f"{len(st.session_state.db)+1:02d}"
                a_b = base64.b64encode(acc_f.getvalue()).decode() if acc_f else ""
                i_b = "|".join([base64.b64encode(f.getvalue()).decode() for f in ims_f]) if ims_f else ""
                # 確保 nr 字典有存入廠商與幣別
                nr = {"單號":tid,"日期":str(datetime.date.today()),"類型":tp,"申請人":curr_name,"專案執行人":exe,"專案名稱":pn,"專案編號":pi,"請款說明":desc,"總金額":amt,"幣別":cur,"付款方式":pay,"請款廠商":vdr,"匯款帳戶":acc,"帳戶影像Base64":a_b,"狀態":"草稿","影像Base64":i_b,"提交時間":"","申請人信箱":curr_name}
                st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nr])], ignore_index=True)
                save_data(st.session_state.db); st.session_state.last_id = tid; st.rerun()

    # 操作按鈕
    if st.session_state.last_id:
        st.info(f"🚩 已存檔！單號：{st.session_state.last_id}")
        r_now = st.session_state.db[st.session_state.db["單號"]==st.session_state.last_id].iloc[0]
        ax, ay, az = st.columns(3)
        if ax.button("🚀 提交送審"):
            idx = st.session_state.db[st.session_state.db["單號"]==st.session_state.last_id].index[0]
            st.session_state.db.at[idx, "狀態"] = "待簽核"
            st.session_state.db.at[idx, "提交時間"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            save_data(st.session_state.db); st.success("已提交！"); st.session_state.last_id = None; st.rerun()
        if ay.button("🔍 線上預覽"): st.session_state.view_id = st.session_state.last_id
        if az.button("🖨️ 線上列印"):
            js = "var w=window.open();w.document.write('" + clean_for_js(render_html(r_now)) + "');w.print();w.close();"
            st.components.v1.html(f'<script>{js}</script>', height=0)

    # 進度清單
    st.divider()
    st.subheader("📋 我的申請進度")
    disp = st.session_state.db if is_admin else st.session_state.db[st.session_state.db["申請人"]==curr_name]
    for i, r in disp.iloc[::-1].iterrows():
        rid = r['單號']; s_txt = "未送審" if r['狀態']=="草稿" else r['狀態']
        c = st.columns([3, 1, 1, 1, 1])
        c[0].write(f"{rid} - {r['專案名稱']} (${r['總金額']:,.0f})")
        c[1].write(f"狀態：{s_txt}")
        # 這裡按鈕名稱依要求修正為：修改、線上預覽、線上列印
        if c[2].button("修改", key=f"e_{rid}", disabled=(r['狀態']!="草稿")): pass
        if c[3].button("線上預覽", key=f"v_{rid}"): st.session_state.view_id = rid; st.rerun()
        if c[4].button("線上列印", key=f"p_{rid}"):
            js = "var w=window.open();w.document.write('" + clean_for_js(render_html(r)) + "');w.print();w.close();"
            st.components.v1.html(f'<script>{js}</script>', height=0)

    if st.session_state.view_id:
        st.markdown(render_html(st.session_state.db[st.session_state.db["單號"]==st.session_state.view_id].iloc[0]), unsafe_allow_html=True)
        if st.button("❌ 關閉預覽"): st.session_state.view_id = None; st.rerun()

elif menu == "2. 簽核中心":
    st.header("⚖️ 簽核中心")
    p_df = st.session_state.db[st.session_state.db["狀態"]=="待簽核"]
    if p_df.empty: st.info("無待簽項目")
    else:
        for i, r in p_df.iterrows():
            with st.expander(f"待審：{r['單號']} - {r['申請人']}"):
                st.markdown(render_html(r), unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("✅ 核准", key=f"ok_{r['單號']}"):
                    idx = st.session_state.db[st.session_state.db["單號"]==r['單號']].index[0]
                    st.session_state.db.at[idx, "狀態"] = "已核准"; save_data(st.session_state.db); st.rerun()
                if c2.button("❌ 駁回", key=f"no_{r['單號']}"):
                    idx = st.session_state.db[st.session_state.db["單號"]==r['單號']].index[0]
                    st.session_state.db.at[idx, "狀態"] = "已駁回"; save_data(st.session_state.db); st.rerun()
