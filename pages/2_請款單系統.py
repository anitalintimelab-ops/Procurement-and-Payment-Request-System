import streamlit as st
import pandas as pd
import os

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="時研-管理系統入口", layout="centered", page_icon="🏢")

# --- 動態讀取系統選項 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
pages_dir = os.path.join(CURRENT_DIR, "pages")
sys_options = []
if os.path.exists(pages_dir):
    sys_options = sorted([f.replace(".py", "") for f in os.listdir(pages_dir) if f.endswith(".py")])
if not sys_options: 
    sys_options = ["1_採購單系統", "2_請款單系統", "3_報價單系統", "99_UI美化測試"]

# --- 核心邏輯：判斷目前下拉選單是否選到測試區 ---
if 'login_sys_choice' not in st.session_state:
    st.session_state.login_sys_choice = sys_options[0]

is_demo = "99" in st.session_state.login_sys_choice or "測試" in st.session_state.login_sys_choice

# ==========================================
# 🎨 核心 CSS 魔法：根據下拉選單動態變色
# ==========================================
# 正式版：冷色系水藍色 / 體驗版：暖色系亮橘色
bg_gradient = "linear-gradient(180deg, #FFF3E0 0%, #FFE0B2 100%)" if is_demo else "linear-gradient(180deg, #F1F5F9 0%, #E2E8F0 100%)"

st.markdown(f"""
<style>
    /* 隱藏左側導覽列 (登入前不給看) */
    [data-testid="collapsedControl"] {{ display: none; }}
    [data-testid="stSidebar"] {{ display: none; }}
    
    /* 整體背景漸變動態切換 */
    .stApp {{
        background: {bg_gradient} !important;
        transition: background 0.5s ease;
    }}
    
    /* 登入卡片美化 */
    div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] {{
        background-color: rgba(255, 255, 255, 0.95);
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
    }}
    
    /* Logo 設定 */
    .global-logo-container {{ 
        width: 100%; text-align: center; margin-bottom: 20px; margin-top: 10px; 
    }}
    .global-logo-en {{ 
        font-size: 42px; font-weight: 500; font-family: "Times New Roman", Times, serif; color: #3E3024; 
    }}
    .global-logo-tw {{ 
        font-size: 24px; font-weight: 900; color: #2C3E50; letter-spacing: 2px; line-height: 1.5;
    }}
    
    /* 按鈕美化 */
    .stButton>button {{
        border-radius: 8px !important;
        font-weight: bold !important;
        border: 1px solid #c0c4cc !important;
        background-color: #ffffff !important;
        color: #333333 !important; 
        transition: all 0.2s ease !important;
        height: 42px !important;
        margin-top: 10px;
    }}
    .stButton>button:hover:not(:disabled) {{
        border-color: #3b82f6 !important;
        color: #3b82f6 !important;
        box-shadow: 0 2px 8px rgba(59,130,246,0.1) !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- 顯示 Logo 與動態副標題 ---
sys_title = "體驗會專屬系統入口 (測試區)" if is_demo else "管理系統入口"
title_color = "#E65100" if is_demo else "#2C3E50"

st.markdown(f"""
    <div class='global-logo-container'>
        <span class='global-logo-en'>T<span style='color: #C19A6B;'>i</span>me Lab</span><br>
        <span class='global-logo-tw'>🏢 時研國際設計股份有限公司<br><span style='color: {title_color};'>{sys_title}</span></span>
    </div>
""", unsafe_allow_html=True)

# --- 讀取對應的資料庫 ---
S_FILE_PROD = os.path.join(CURRENT_DIR, "staff_v2.csv")
S_FILE_DEMO = os.path.join(CURRENT_DIR, "demo_staff.csv")

def load_staff(is_demo_mode):
    target_file = S_FILE_DEMO if is_demo_mode else S_FILE_PROD
    if os.path.exists(target_file):
        for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
            try:
                return pd.read_csv(target_file, encoding=enc, dtype=str).fillna("")
            except:
                continue
    return pd.DataFrame({
        "name": ["Andy", "Charles", "Eason", "Sunglin", "Anita", "WISH"], 
        "status": ["在職", "在職", "在職", "在職", "在職", "離職"], 
        "password": ["0000"]*6
    })

staff_df = load_staff(is_demo)
staff_list = staff_df["name"].tolist() if not staff_df.empty else ["尚無人員資料"]

# --- 登入表單 ---
with st.container():
    if is_demo:
        st.warning("🟠 **目前位於體驗測試環境！** 在此處的所有操作皆為獨立檔案，不會影響正式系統。")
        
    selected_user = st.selectbox("登入身分", staff_list)

    # 檢查是否為離職人員
    is_resigned = False
    if not staff_df.empty and selected_user in staff_list:
        user_row = staff_df[staff_df["name"] == selected_user].iloc[0]
        if user_row.get("status") == "離職":
            is_resigned = True

    if is_resigned:
        st.markdown("<p style='color:#E53935; font-size:15px; font-weight:bold; margin-top:-10px; margin-bottom:10px;'>🚫 目前帳號已停權/離職，無法登入</p>", unsafe_allow_html=True)
        password = st.text_input("登入密碼", type="password", disabled=True, placeholder="此帳號已停用")
        st.selectbox("進入系統", sys_options, key="login_sys_choice", disabled=True)
        st.button("登入系統", disabled=True, use_container_width=True)
    else:
        password = st.text_input("登入密碼", type="password")
        # 下拉選單連動 key，只要變更就會立刻重整改變上面的顏色與資料庫
        st.selectbox("進入系統", sys_options, key="login_sys_choice")

        if st.button("登入系統", use_container_width=True):
            if not staff_df.empty:
                user_row = staff_df[staff_df["name"] == selected_user].iloc[0]
                if str(user_row["password"]) == str(password):
                    st.session_state.user_id = selected_user
                    st.session_state.user_status = "在職"
                    st.session_state.sys_choice = st.session_state.login_sys_choice
                    st.session_state.is_demo_mode = is_demo 
                    st.switch_page(f"pages/{st.session_state.login_sys_choice}.py")
                else:
                    st.error("❌ 密碼錯誤，請重新輸入。")
