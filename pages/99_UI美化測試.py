import streamlit as st

st.set_page_config(page_title="UI 測試預覽", layout="wide")

# 這裡就是我們預計要加入的現代化美化 CSS
st.markdown("""
<style>
.stApp { background-color: #f4f7f6; } 

/* 卡片特效 */
[data-testid="stForm"] {
    background-color: #ffffff;
    border-radius: 16px;
    padding: 30px;
    box-shadow: 0 8px 24px rgba(149, 157, 165, 0.15);
    border: 1px solid #e1e4e8;
}

/* 輸入框質感 */
.stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stNumberInput input {
    border-radius: 10px !important;
    border: 1px solid #d1d5da !important;
    background-color: #fafbfc !important;
    transition: all 0.2s ease-in-out;
}
.stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: #0366d6 !important;
    box-shadow: 0 0 0 3px rgba(3, 102, 214, 0.3) !important;
    background-color: #ffffff !important;
}

/* 動態立體按鈕 */
.stButton>button, .stFormSubmitButton>button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    border: 1px solid #e1e4e8 !important;
    background-color: #ffffff !important;
    color: #24292e !important;
    transition: all 0.2s ease-in-out !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04) !important;
}
.stButton>button:hover, .stFormSubmitButton>button:hover {
    background-color: #f3f4f6 !important;
    border-color: #cdd3d8 !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.1) !important;
}
</style>
""", unsafe_allow_html=True)

st.title("✨ 現代化 UI 視覺預覽 (測試頁面)")
st.write("這是一個沒有連結任何資料庫的假頁面，請隨意點擊體驗輸入框跟按鈕的視覺回饋。")

with st.form("test_form"):
    st.subheader("📝 假裝這是填寫請款申請單的區塊")
    
    c1, c2, c3 = st.columns(3)
    c1.selectbox("假下拉選單", ["選項A", "選項B"])
    c2.text_input("假輸入框", placeholder="點擊我看看光暈效果...")
    c3.number_input("假數字框", value=1000)
    
    st.text_area("假說明框", placeholder="滑鼠移到下方的按鈕看看浮動效果...")
    
    bc1, bc2, bc3 = st.columns(3)
    bc1.form_submit_button("💾 假裝存檔", use_container_width=True)
    bc2.form_submit_button("🚀 假裝提交", use_container_width=True)
    bc3.form_submit_button("❌ 假裝不存檔", use_container_width=True)
