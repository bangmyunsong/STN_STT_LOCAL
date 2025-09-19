@echo off
echo =====================================
echo STN STT 시스템 관리자 UI 시작
echo =====================================

echo 가상환경 활성화 중...
call venv\Scripts\activate

echo 관리자 UI 시작 중...
echo UI가 시작되면 브라우저에서 자동으로 열립니다.
echo.

streamlit run admin_ui.py

pause 