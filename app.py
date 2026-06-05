import streamlit as st
import pandas as pd
import os

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="時研-管理系統入口", layout="centered", page_icon="🏢")

# --- 2. 雙開門環境選擇 (下拉選單) ---
st.write("") 
env_choice = st.selectbox("系統環境切換", ["🔵 進入正式系統", "🟠 進入體驗測試版"], label_visibility="collapsed")
is_demo = "體驗" in env_choice

# 依照您的需求：紅字提醒放在下拉選單下方
if is_demo:
    st.markdown("<p style='color:#E53935; font-size:14px; font-weight:bold; margin-top:-10px; margin-bottom:15px;'>※ 如登入測試區，請先點選測試系統，再點選人名及密碼</p>", unsafe_allow_html=True)

# ==========================================
# 🎨 核心 CSS 魔法：動態切換背景顏色
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

# --- 3. 顯示 Logo 與動態副標題 ---
sys_title = "體驗會專屬系統入口 (測試區)" if is_demo else "管理系統入口"
title_color = "#E65100" if is_demo else "#2C3E50"

st.markdown(f"""
    <div class='global-logo-container'>
        <span class='global-logo-en'>T<span style='color: #C19A6B;'>i</span>me Lab</span><br>
        <span class='global-logo-tw'>🏢 時研國際設計股份有限公司<br><span style='color: {title_color};'>{sys_title}</span></span>
    </div>
""", unsafe_allow_html=True)

# --- 4. 雙開門資料庫讀取 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ★ 正式版讀 staff_v2，體驗版讀 demo_staff ★
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
    # 預設名單 (如果 demo_staff.csv 還沒建立，就會先套用這份預設名單)
    return pd.DataFrame({
        "name": ["Andy", "Charles", "Eason", "Sunglin", "Anita", "WISH"], 
        "status": ["在職", "在職", "在職", "在職", "在職", "離職"], 
        "password": ["0000"]*6
    })

staff_df = load_staff(is_demo)
staff_list = staff_df["name"].tolist() if not staff_df.empty else ["尚無人員資料"]

# 動態抓取 pages 資料夾內的系統選項
sys_options = []
pages_dir = os.path.join(CURRENT_DIR, "pages")
if os.path.exists(pages_dir):
    all_pages = sorted([f.replace(".py", "") for f in os.listdir(pages_dir) if f.endswith(".py")])
    # ★ 徹底隔離路徑：正式版只能去正式頁面，體驗版只能去 99_ 測試頁面 ★
    if is_demo:
        sys_options = [p for p in all_pages if "99_" in p or "測試" in p]
    else:
        sys_options = [p for p in all_pages if "99_" not in p and "測試" not in p]

if not sys_options: 
    sys_options = ["⚠️ 尚未建立對應系統頁面"] 

# --- 5. 登入表單 (維持 人員 > 密碼 > 進入系統) ---
with st.container():
    selected_user = st.selectbox("登入身分", staff_list)

    # 檢查是否為離職人員
    is_resigned = False
    if not staff_df.empty and selected_user in staff_list:
        user_row = staff_df[staff_df["name"] == selected_user].iloc[0]
        if user_row.get("status") == "離職":
            is_resigned = True

    # 離職員工的防呆封鎖畫面
    if is_resigned:
        st.markdown("<p style='color:#E53935; font-size:15px; font-weight:bold; margin-top:-10px; margin-bottom:10px;'>🚫 目前帳號已停權/離職，無法登入</p>", unsafe_allow_html=True)
        password = st.text_input("登入密碼", type="password", disabled=True, placeholder="此帳號已停用")
        sys_choice = st.selectbox("進入系統", sys_options, disabled=True)
        st.button("登入系統", disabled=True, use_container_width=True)

    # 正常在職人員登入畫面
    else:
        password = st.text_input("登入密碼", type="password")
        sys_choice = st.selectbox("進入系統", sys_options)

        if st.button("🚀 登入系統", use_container_width=True):
            if "尚未" in sys_choice:
                st.error("❌ 找不到對應的系統，請確認 pages/ 資料夾內的檔案設定。")
            elif not staff_df.empty:
                user_row = staff_df[staff_df["name"] == selected_user].iloc[0]
                
                # 驗證密碼
                if str(user_row["password"]) == str(password):
                    # 將登入資訊寫入暫存記憶體
                    st.session_state.user_id = selected_user
                    st.session_state.user_status = "在職"
                    st.session_state.sys_choice = sys_choice
                    st.session_state.is_demo_mode = is_demo # 紀錄目前是哪種模式
                    
                    # 跳轉到對應頁面
                    st.switch_page(f"pages/{sys_choice}.py")
                else:
                    st.error("❌ 密碼錯誤，請重新輸入。")
