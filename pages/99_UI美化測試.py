import streamlit as st
import pandas as pd

# 設定頁面滿版
st.set_page_config(page_title="UI 測試預覽", layout="wide", page_icon="🎨")

# ==========================================
# 🎨 核心 CSS 魔法：全版面美化設計
# ==========================================
st.markdown("""
<style>
/* 1. 整個網頁的背景色 (柔和的灰藍色，讓白色卡片凸顯出來) */
.stApp { 
    background-color: #f0f4f8; 
} 

/* 2. 標題與文字顏色微調，增加現代感 */
h1, h2, h3 {
    color: #1e293b;
    font-weight: 700 !important;
}

/* 3. 填寫表單區塊 (變成純白立體圓角卡片) */
[data-testid="stForm"], div.stExpander > div[role="button"] {
    background-color: #ffffff;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    border: 1px solid #e2e8f0;
}

/* 4. 輸入框質感升級 (圓角、灰底、點擊發光) */
.stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stNumberInput input {
    border-radius: 10px !important;
    border: 1px solid #cbd5e1 !important;
    background-color: #f8fafc !important;
    transition: all 0.3s ease;
}
/* 當滑鼠點擊輸入框時的「藍色光暈」特效 */
.stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
    background-color: #ffffff !important;
}

/* 5. 動態立體按鈕 (圓角、陰影、懸浮微動) */
.stButton>button, .stFormSubmitButton>button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    border: 1px solid #e2e8f0 !important;
    background-color: #ffffff !important;
    color: #334155 !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
}
/* 滑鼠移過按鈕時的「浮起」特效 */
.stButton>button:hover, .stFormSubmitButton>button:hover {
    background-color: #f1f5f9 !important;
    border-color: #cbd5e1 !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
    color: #0f172a !important;
}

/* 6. 下方資料表格圓角與陰影美化 */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    border: 1px solid #e2e8f0;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 📺 以下為模擬畫面的排版 (不連接真實資料)
# ==========================================

st.title("🎨 時研系統 - 全新 UI 版面預覽")
st.info("💡 這是一個【完全獨立、沒有連接資料庫】的測試網頁。請盡情點擊體驗輸入框跟按鈕的視覺回饋！")

with st.expander("➕ 新增專案 / 廠商至資料庫 (點擊看卡片質感)"):
    st.write("這是一個展開的純白圓角卡片展示。")
    st.text_input("假輸入框 1")
    st.button("假儲存按鈕")

st.subheader("📝 填寫請款申請單 (立體表單預覽)")

with st.form("test_form"):
    st.markdown("**第一排：專案資訊**")
    c1, c2, c3, c4 = st.columns(4)
    c1.selectbox("申請人", ["Anita", "Andy", "Sunglin"])
    c2.selectbox("負責執行長", ["Sunglin", "Eason", "Charles"])
    c3.selectbox("專案名稱", ["士林金格工程", "文大多功能講桌", "永和郭宅工程"])
    c4.text_input("專案編號", value="20260325001")
    
    st.markdown("**第二排：金額與幣別**")
    cx1, cx2, cx3, cx4 = st.columns(4)
    cx1.selectbox("幣別", ["TWD", "USD"])
    cx2.number_input("金額 (未稅)", value=15000)
    cx3.number_input("稅額", value=750)
    cx4.text_input("總計金額 (未稅+稅額)", value="15,750", disabled=True)
    
    st.markdown("**第三排：廠商與匯款資訊**")
    cv1, cv2, cv3 = st.columns(3)
    cv1.selectbox("請款廠商", ["測試建材行", "時研合作廠商"])
    cv2.text_input("匯款帳戶", value="808-1234567890")
    cv3.text_input("發票號碼或憑證", placeholder="請點擊此處體驗藍色光暈...")
    
    st.markdown("**第四排：說明與附件**")
    st.radio("付款方式", ["零用金", "現金", "匯款(扣30手續費)", "匯款(不扣30手續費)"], horizontal=True)
    st.text_area("請款說明", placeholder="請輸入說明文字...")
    st.file_uploader("上傳存摺/匯款資料 (圖/Excel)", type=["png", "jpg", "xlsx"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    bc1, bc2, bc3, bc4, bc5, bc6 = st.columns(6)
    bc1.form_submit_button("💾 存檔", use_container_width=True)
    bc2.form_submit_button("🚀 提交", use_container_width=True)
    bc3.form_submit_button("🔍 預覽", use_container_width=True)
    bc4.form_submit_button("🖨️ 列印", use_container_width=True)
    bc5.form_submit_button("🆕 下一筆", use_container_width=True)
    bc6.form_submit_button("❌ 不存檔", use_container_width=True)

st.divider()
st.subheader("📋 申請追蹤清單 (表格美化預覽)")

# 模擬一個假表格，讓您看外觀
dummy_data = pd.DataFrame({
    "單號": ["20260326-01", "20260326-02"],
    "專案名稱": ["士林金格工程", "永和郭宅工程"],
    "負責執行長": ["Sunglin", "Sunglin"],
    "申請人": ["Sunglin", "Sunglin"],
    "請款金額": ["$15,970", "$68,804"],
    "操作": ["✅", "✅"]
})
st.dataframe(dummy_data, hide_index=True, use_container_width=True)
