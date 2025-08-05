@echo off
echo ===================================
echo 2D 멀티플레이어 격투 게임 런처
echo ===================================
echo.
echo 가상환경을 활성화하고 게임을 시작합니다...
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    python main.py
) else (
    echo 가상환경을 찾을 수 없습니다. Python을 직접 실행합니다...
    python main.py
)

pause
