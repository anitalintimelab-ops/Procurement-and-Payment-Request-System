import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 設定網頁標題
st.set_page_config(page_title="時研設計-報價系統", layout="wide")

# 定義報價單專屬資料庫
QUOTE_MAIN = 'quotes_main.csv'
QUOTE_DETAIL = 'quotes_detail.csv'

# 自動初始化資料庫
for db, cols in {QUOTE_MAIN: ['id', 'date', 'project', 'client', 'total', 'status'], 
                 QUOTE_DETAIL: ['id', 'item', 'spec', 'qty', 'unit', 'price', 'subtotal']}.items():
    if not os.path.exists(db):
        pd.DataFrame(columns=cols).to_csv(db, index=False)

st.title("📋 獨立報價單管理系統")
st.info("本系統與請款/採購單完全分開，獨立運行。")

# --- 介面設計 ---
tab1, tab2 = st.tabs(["🆕 建立報價單", "📁 歷史紀錄"])

with tab1:
    with st.form("new_quote"):
        p_name = st.text_input("專案名稱 (例如：元大方圓)")
        c_name = st.text_input("業主名稱")
        q_id = f"Q{datetime.now().strftime('%Y%m%d%H%M')}"
        
        st.write("--- 工項明細 ---")
        # 範例：預設提供 5 列供填寫 (之後可優化為動態增加)
        items_list = []
        for i in range(5):
            c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 2])
            item = c1.text_input(f"品名 {i+1}", key=f"i{i}")
            spec = c2.text_input(f"規格", key=f"s{i}")
            qty = c3.number_input(f"數量", min_value=0.0, key=f"q{i}")
            unit = c4.text_input(f"單位", key=f"u{i}")
            price = c5.number_input(f"單價", min_value=0, key=f"p{i}")
            if item:
                items_list.append([q_id, item, spec, qty, unit, price, qty*price])
        
        if st.form_submit_button("儲存報價單並產生連結"):
            if p_name and items_list:
                total_amount = sum(row[6] for row in items_list)
                # 存入主表
                main_df = pd.DataFrame([[q_id, datetime.now().strftime('%Y-%m-%d'), p_name, c_name, total_amount, "待審核"]], columns=pd.read_csv(QUOTE_MAIN).columns)
                main_df.to_csv(QUOTE_MAIN, mode='a', header=False, index=False)
                # 存入明細
                detail_df = pd.DataFrame(items_list, columns=pd.read_csv(QUOTE_DETAIL).columns)
                detail_df.to_csv(QUOTE_DETAIL, mode='a', header=False, index=False)
                
                st.success(f"✅ 報價單 {q_id} 已建立！總金額：{total_amount}")
                st.code(f"請複製網址傳給執行長：\n https://your-app-url.streamlit.app/?id={q_id}")
            else:
                st.error("請填寫專案名稱與至少一項工項")

with tab2:
    st.subheader("報價單總覽")
    if os.path.exists(QUOTE_MAIN):
        st.dataframe(pd.read_csv(QUOTE_MAIN))
