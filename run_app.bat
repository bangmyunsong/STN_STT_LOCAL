@echo off
echo ===================================
echo   AI 음성-텍스트 변환기 (발화자 구분)
echo ===================================
echo.

REM 필요한 패키지 설치
echo 🔄 필요한 패키지 설치 중...
pip install -r requirements.txt --quiet

REM config.env 파일 확인
if exist "config.env" (
    echo ✅ config.env 파일이 발견되었습니다.
    echo 환경변수가 자동으로 로드됩니다.
    echo 고급 발화자 구분 기능을 사용할 수 있습니다.
) else (
    echo ⚠️  config.env 파일이 없습니다.
    echo 기본 발화자 구분 기능만 사용 가능합니다.
    echo.
    echo config.env 파일을 생성하여 HuggingFace 토큰을 설정하세요.
)

echo.
echo WhisperX와 발화자 구분 기능을 사용합니다.
echo 웹 브라우저가 자동으로 열립니다...
echo 종료하려면 Ctrl+C를 누르세요.
echo.

streamlit run stt_app.py

pause 