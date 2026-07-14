# (接續您提供的程式結構，僅修改選單與新增 8. 表單資料庫功能)

# --- 1. 修改選單顯示邏輯 (請置換您原本的 menu_options 設定) ---
if is_admin:
    menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽", "5. 產出本期支出報表", "6. 請款狀態/系統設定", "7. 專案 / 廠商資料庫", "8. 表單資料庫"]
elif curr_name == CFO_NAME:
    menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽", "5. 產出本期支出報表", "6. 請款狀態/系統設定", "8. 表單資料庫"]
else:
    menu_options = ["1. 填寫申請單", "2. 專案執行長簽核", "3. 財務長簽核", "4. 表單狀態總覽"]

# --- 2. 新增 8. 表單資料庫功能 (請貼在 menu 判斷式的最後面) ---
    elif menu == "8. 表單資料庫":
        st.subheader("🧹 表單資料庫管理 (僅限管理員/財務長)")
        st.info("💡 請勾選您要刪除的「已核准」單據，刪除後將無法復原，並可有效縮減資料庫大小。")
        
        f_db = load_data()
        # 僅篩選出「已核准」的單據供管理員選取刪除
        clean_df = f_db[f_db["狀態"] == "已核准"].copy()
        
        if clean_df.empty:
            st.warning("目前沒有已核准的單據可進行清理。")
        else:
            clean_df.insert(0, "勾選刪除", False)
            edited_clean = st.data_editor(
                clean_df[["勾選刪除", "單號", "專案名稱", "總金額", "申請人", "提交時間"]],
                hide_index=True,
                use_container_width=True
            )
            
            if st.button("🔥 執行永久刪除已勾選單據"):
                selected_to_del = edited_clean[edited_clean["勾選刪除"] == True]["單號"].tolist()
                if selected_to_del:
                    # 從主資料庫移除
                    new_db = f_db[~f_db["單號"].isin(selected_to_del)]
                    save_data(new_db)
                    st.success(f"已成功刪除 {len(selected_to_del)} 筆單據！檔案已縮減並同步至 GitHub。")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("請先勾選要刪除的單據！")

# --- 其他部分保持原樣 ---
