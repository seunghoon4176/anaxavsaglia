#!/bin/bash
# 리눅스/맥용 서버 실행 스크립트

echo "=================================="
echo "2D 멀티플레이어 격투 게임 서버"
echo "=================================="
echo

# 포트 설정 (환경변수에서 가져오거나 기본값 사용)
PORT=${GAME_SERVER_PORT:-12345}
HOST=${GAME_SERVER_HOST:-0.0.0.0}

echo "서버 설정:"
echo "  호스트: $HOST"
echo "  포트: $PORT"
echo

# Python 가상환경 확인
if [ -d "venv" ]; then
    echo "Python 가상환경을 활성화합니다..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Python 가상환경을 활성화합니다..."
    source .venv/bin/activate
else
    echo "가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다."
fi

# 서버 시작
echo "로비 서버를 시작합니다..."
python3 standalone_lobby_server.py --host $HOST --port $PORT
