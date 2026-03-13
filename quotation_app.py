import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 獨立資料庫定義 ---
QUOTE_MAIN = 'quote_main.csv'
QUOTE_DETAIL = 'quote_detail.csv'

# 初始化 CSV 檔案 (如果不存在)
for db, cols in {
    QUOTE_MAIN: ['quote_id', 'date', 'project', 'client', 'total', 'status'],
    QUOTE_DETAIL: ['quote_id', 'item', 'spec', 'qty', 'unit', 'price', 'subtotal']
}.items():
    if not os.path.exists(db):
        pd.DataFrame(columns=cols).to_csv(db, index=False)

st.set_page_config(page_title="時研設計-報價系統", layout="wide")

# --- 側邊欄：功能切換 ---
mode = st.sidebar.radio("系統選單", ["建立報價單", "報價單紀錄", "執行長核准頁面"])

# 1. 建立報價單
if mode == "建立報價單":
    st.header("📝 建立新報價單")
    with st.form("new_quote"):
        col1, col2 = st.columns(2)
        project = col1.text_input("工程名稱", placeholder="例如：元大方圓")
        client = col2.text_input("客戶名稱")
        q_id = f"Q{datetime.now().strftime('%Y%m%d%H%M')}"
        
        st.write("--- 工項明細 ---")
        # 提供 5 欄位填寫，多填可再增加
        items_data = []
        for i in range(5):
            c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 2])
            item = c1.text_input(f"品名/規格 {i+1}", key=f"it{i}")
            qty = c3.number_input(f"數量", min_value=0.0, key=f"qt{i}")
            unit = c4.text_input(f"單位", key=f"un{i}")
            price = c5.number_input(f"單價", min_value=0, key=f"pr{i}")
            if item:
                items_data.append([q_id, item, "", qty, unit, price, qty*price])
        
        if st.form_submit_button("儲存並產生審核連結"):
            if project and items_data:
                total_sum = sum(row[6] for row in items_data)
                # 存入主表
                main_df = pd.DataFrame([[q_id, datetime.now().strftime('%Y-%m-%d'), project, client, total_sum, "待審核"]], columns=pd.read_csv(QUOTE_MAIN).columns)
                main_df.to_csv(QUOTE_MAIN, mode='a', header=False, index=False)
                # 存入明細
                pd.DataFrame(items_data, columns=pd.read_csv(QUOTE_DETAIL).columns).to_csv(QUOTE_DETAIL, mode='a', header=False, index=False)
                
                st.success(f"✅ 報價單 {q_id} 已建立！")
                st.info(f"🔗 請複製此網址傳給執行長：\n https://your-app-url.streamlit.app/?id={q_id}")
            else:
                st.warning("請填寫必要資訊")

# 2. 報價單紀錄
elif mode == "報價單紀錄":
    st.header("📁 報價歷史紀錄")
    st.dataframe(pd.read_csv(QUOTE_MAIN))

# 3. 執行長核准頁面 (模擬傳網址後的畫面)
elif mode == "執行長核准頁面":
    st.header("📑 報價單審核 (執行長專用)")
    # 此處邏輯可改為從 URL params 抓取 ID
    search_id = st.text_input("請輸入報價單號進行審核")
    if search_id:
        detail_df = pd.read_csv(QUOTE_DETAIL)
        this_quote = detail_df[detail_df['quote_id'] == search_id]
        if not this_quote.empty:
            st.table(this_quote)
            if st.button("✅ 核准此報價單"):
                st.success("報價單已核准！")
