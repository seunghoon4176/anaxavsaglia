@echo off
REM Windows용 서버 실행 스크립트

echo ==================================
echo 2D 멀티플레이어 격투 게임 서버
echo ==================================
echo.

REM 포트 설정 (환경변수에서 가져오거나 기본값 사용)
if "%GAME_SERVER_PORT%"=="" set GAME_SERVER_PORT=12345
if "%GAME_SERVER_HOST%"=="" set GAME_SERVER_HOST=0.0.0.0

echo 서버 설정:
echo   호스트: %GAME_SERVER_HOST%
echo   포트: %GAME_SERVER_PORT%
echo.

cd /d "%~dp0"

REM Python 가상환경 확인
if exist "venv\Scripts\activate.bat" (
    echo Python 가상환경을 활성화합니다...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo Python 가상환경을 활성화합니다...
    call .venv\Scripts\activate.bat
) else (
    echo 가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다.
)

REM 서버 시작
echo 로비 서버를 시작합니다...
python standalone_lobby_server.py --host %GAME_SERVER_HOST% --port %GAME_SERVER_PORT%

pause
