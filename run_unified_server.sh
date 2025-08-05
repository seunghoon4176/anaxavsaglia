#!/bin/bash
# 통합 서버 실행 스크립트 (Linux/Mac)

echo "=================================="
echo "2D 멀티플레이어 격투 게임 통합 서버"
echo "=================================="

# Python 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "Python 가상환경 활성화 중..."
    source venv/bin/activate
fi

# 의존성 설치 확인
echo "필요한 패키지 설치 확인 중..."
pip install -q pygame PySide6

# 통합 서버 실행
echo "통합 서버를 시작합니다..."
python3 unified_server.py --host 0.0.0.0 --port 12345

echo "서버가 종료되었습니다."
