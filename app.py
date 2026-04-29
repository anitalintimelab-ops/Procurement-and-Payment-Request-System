import streamlit as st
import pandas as pd
import os

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="時研-管理系統入口", layout="centered", page_icon="🏢")

# ==========================================
# 🎨 核心 CSS 魔法：美化登入介面
# ==========================================
st.markdown("""
<style>
    /* 隱藏左側導覽列 (登入前不給看) */
    [data-testid="collapsedControl"] { display: none; }
    [data-testid="stSidebar"] { display: none; }
    
    /* 登入卡片美化 */
    div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
    }
    
    /* Logo 設定 */
    .global-logo-container { 
        width: 100%; text-align: center; margin-bottom: 20px; margin-top: 20px; 
    }
    .global-logo-en { 
        font-size: 42px; font-weight: 500; font-family: "Times New Roman", Times, serif; color: #3E3024; 
    }
    .global-logo-tw { 
        font-size: 24px; font-weight: 900; color: #2C3E50; letter-spacing: 2px; line-height: 1.5;
    }
    
    /* 按鈕美化 */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: bold !important;
        border: 1px solid #c0c4cc !important;
        background-color: #ffffff !important;
        color: #333333 !important; 
        transition: all 0.2s ease !important;
        height: 42px !important;
        margin-top: 10px;
    }
    .stButton>button:hover:not(:disabled) {
        border-color: #3b82f6 !important;
        color: #3b82f6 !important;
        box-shadow: 0 2px 8px rgba(59,130,246,0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 顯示 Logo ---
st.markdown("""
    <div class='global-logo-container'>
        <span class='global-logo-en'>T<span style='color: #C19A6B;'>i</span>me Lab</span><br>
        <span class='global-logo-tw'>🏢 時研國際設計股份有限公司<br>管理系統入口</span>
    </div>
""", unsafe_allow_html=True)

# --- 3. 讀取人員資料庫 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
S_FILE = os.path.join(CURRENT_DIR, "staff_v2.csv")

def load_staff():
    if os.path.exists(S_FILE):
        for enc in ['utf-8-sig', 'utf-8', 'cp950', 'big5']:
            try:
                return pd.read_csv(S_FILE, encoding=enc, dtype=str).fillna("")
            except:
                continue
    # 預設名單
    return pd.DataFrame({
        "name": ["Andy", "Charles", "Eason", "Sunglin", "Anita", "WISH"], 
        "status": ["在職", "在職", "在職", "在職", "在職", "離職"], 
        "password": ["0000"]*6
    })

staff_df = load_staff()
staff_list = staff_df["name"].tolist() if not staff_df.empty else ["尚無人員資料"]

# 動態抓取 pages 資料夾內的系統選項
sys_options = []
pages_dir = os.path.join(CURRENT_DIR, "pages")
if os.path.exists(pages_dir):
    sys_options = sorted([f.replace(".py", "") for f in os.listdir(pages_dir) if f.endswith(".py")])
if not sys_options: 
    sys_options = ["1_採購單系統", "2_請款單系統"] # 防呆預設

# --- 4. 登入表單 ---
with st.container():
    st.write("") # 留一點空間
    selected_user = st.selectbox("身分", staff_list)

    # 檢查是否為離職人員
    is_resigned = False
    if not staff_df.empty and selected_user in staff_list:
        user_row = staff_df[staff_df["name"] == selected_user].iloc[0]
        if user_row.get("status") == "離職":
            is_resigned = True

    # ★ 核心需求：離職員工的防呆封鎖畫面
    if is_resigned:
        # 紅字顯示警告，並強制鎖死密碼與進入按鈕
        st.markdown("<p style='color:#E53935; font-size:15px; font-weight:bold; margin-top:-10px; margin-bottom:10px;'>目前已離職，無法登入畫面</p>", unsafe_allow_html=True)
        password = st.text_input("密碼", type="password", disabled=True, placeholder="此帳號已停用")
        sys_choice = st.selectbox("進入系統", sys_options, disabled=True)
        st.button("登入系統", disabled=True, use_container_width=True)

    # 正常在職人員登入畫面
    else:
        password = st.text_input("密碼", type="password")
        sys_choice = st.selectbox("進入系統", sys_options)

        if st.button("登入系統", use_container_width=True):
            if not staff_df.empty:
                user_row = staff_df[staff_df["name"] == selected_user].iloc[0]
                
                # 驗證密碼
                if str(user_row["password"]) == str(password):
                    # 將登入資訊寫入暫存記憶體
                    st.session_state.user_id = selected_user
                    st.session_state.user_status = "在職"
                    st.session_state.sys_choice = sys_choice
                    
                    # 跳轉到對應頁面
                    st.switch_page(f"pages/{sys_choice}.py")
                else:
                    st.error("❌ 密碼錯誤，請重新輸入。")
