@echo off
echo ========================================
echo WhisperX STT 애플리케이션 실행 (환경 수정)
echo ========================================
echo.

echo 1. 환경변수 새로고침...
echo.
set PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.1.1-full_build\bin

echo 2. FFmpeg 설치 확인...
echo.
where ffmpeg
if %ERRORLEVEL% EQU 0 (
    echo ✅ FFmpeg 경로 찾음!
    ffmpeg -version | findstr "version"
) else (
    echo ❌ FFmpeg를 찾을 수 없습니다.
    echo 수동으로 PATH에 FFmpeg 경로를 추가해주세요.
)

echo.
echo 3. WhisperX 설치 확인...
echo.
python -c "import whisperx; print('✅ WhisperX 사용 가능')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ WhisperX가 설치되지 않았습니다.
    echo setup_whisperx.bat을 먼저 실행해주세요.
    pause
    exit
)

echo.
echo 4. 발화자 구분 모듈 확인...
echo.
python -c "import pyannote.audio; print('✅ 발화자 구분 기능 사용 가능')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️ 발화자 구분 모듈이 없습니다. 기본 기능만 사용됩니다.
)

echo.
echo 5. WhisperX STT 앱 실행...
echo.
echo 웹 브라우저가 자동으로 열립니다...
echo 종료하려면 Ctrl+C를 누르세요.
echo.

python -m streamlit run stt_app.py

pause 