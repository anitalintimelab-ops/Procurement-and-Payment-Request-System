@echo off
:: 強制切換到檔案所在的資料夾
cd /d "%~dp0"

echo ==================================================
echo   時研國際設計 - 系統啟動中
echo ==================================================

:: 1. 啟動 Streamlit (直接執行，不使用背景模式以方便觀察錯誤)
:: 如果這行出錯，黑視窗會顯示錯誤訊息
echo 正在啟動伺服器...
start /b py -m streamlit run app.py --server.headless=true

:: 2. 等待 5 秒讓伺服器熱身
timeout /t 5

:: 3. 嘗試用三種不同的方式開啟 Chrome
echo 正在開啟 Google Chrome...

:: 嘗試路徑 A (64位元 Chrome)
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8501"
    goto end
)

:: 嘗試路徑 B (32位元 Chrome)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" "http://localhost:8501"
    goto end
)

:: 嘗試路徑 C (直接叫指令)
start chrome "http://localhost:8501"

:end
echo.
echo --------------------------------------------------
echo 如果 Chrome 沒有自動跳出，請手動開啟 Chrome
echo 並在網址列輸入: http://localhost:8501
echo --------------------------------------------------
echo [請不要關閉此視窗，縮小即可]
pause