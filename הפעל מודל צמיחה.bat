@echo off
chcp 65001 >nul
title מודל צמיחה – איכילוב

echo.
echo  ==========================================
echo    מודל צמיחה – בית חולים איכילוב
echo  ==========================================
echo.
echo  מפעיל את האפליקציה, אנא המתן...
echo.

cd /d "%~dp0Growth Model"

"%LOCALAPPDATA%\Programs\Python\Python313\Scripts\streamlit.exe" run app.py --server.headless false --browser.gatherUsageStats false

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [שגיאה] לא ניתן להפעיל את האפליקציה.
    echo  ודא ש-Streamlit מותקן: pip install streamlit
    echo.
    pause
)
