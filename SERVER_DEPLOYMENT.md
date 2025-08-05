# 서버 배포 가이드

## 📋 필요한 파일들

서버 배포시 다음 파일들만 필요합니다:

```
서버 디렉토리/
├── standalone_lobby_server.py    # 로비 서버
├── standalone_game_server.py     # 게임 서버
├── run_server.sh                 # 리눅스/맥 실행 스크립트
└── run_server.bat               # Windows 실행 스크립트
```

## 🚀 서버 실행 방법

### Windows
```bash
run_server.bat
```

### Linux/Mac
```bash
chmod +x run_server.sh
./run_server.sh
```

### 수동 실행
```bash
python3 standalone_lobby_server.py --host 0.0.0.0 --port 12345
```

## ⚙️ 서버 설정

### 환경 변수
```bash
# 서버 호스트 설정 (기본값: 0.0.0.0)
export GAME_SERVER_HOST=0.0.0.0

# 서버 포트 설정 (기본값: 12345)
export GAME_SERVER_PORT=12345
```

### 커맨드라인 옵션
```bash
python3 standalone_lobby_server.py --help
```

## 🔧 클라이언트 설정

클라이언트에서 서버 주소를 변경하려면 `new_launcher.py` 파일을 수정하세요:

```python
# new_launcher.py 파일의 GameLauncher 클래스 __init__ 메서드에서
self.server_host = "YOUR_SERVER_IP"  # 실제 서버 IP로 변경
self.server_port = 12345
```

## 📡 방화벽 설정

서버에서 다음 포트들을 열어야 합니다:
- **12345**: 로비 서버 포트
- **13000-14000**: 게임 서버 포트 범위

### Ubuntu/Debian
```bash
sudo ufw allow 12345
sudo ufw allow 13000:14000/tcp
```

### CentOS/RHEL
```bash
sudo firewall-cmd --permanent --add-port=12345/tcp
sudo firewall-cmd --permanent --add-port=13000-14000/tcp
sudo firewall-cmd --reload
```

## 🐳 Docker 배포 (옵션)

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY standalone_lobby_server.py .
COPY standalone_game_server.py .

EXPOSE 12345
EXPOSE 13000-14000

CMD ["python", "standalone_lobby_server.py", "--host", "0.0.0.0", "--port", "12345"]
```

### Docker 실행
```bash
# 이미지 빌드
docker build -t game-server .

# 컨테이너 실행
docker run -d -p 12345:12345 -p 13000-14000:13000-14000 game-server
```

## 📊 서버 모니터링

서버는 다음과 같은 로그를 출력합니다:
- `[INFO]`: 일반 정보
- `[WARNING]`: 경고
- `[ERROR]`: 오류
- `[STATUS]`: 상태 정보

### 로그 예시
```
[INFO] ======================================
[INFO] 2D 멀티플레이어 격투 게임 로비 서버
[INFO] 서버 주소: 0.0.0.0:12345
[INFO] 서버가 시작되었습니다...
[INFO] ======================================
[INFO] 새 클라이언트 연결: ('192.168.1.100', 54321)
[INFO] 플레이어 정보 설정: Player1 (anaxa)
[INFO] 방 생성: Player1의 방 (ID: abc12345) by Player1
[STATUS] 연결된 클라이언트: 2, 활성 방: 1
```

## 🔒 보안 고려사항

1. **방화벽 설정**: 필요한 포트만 열기
2. **접근 제한**: 필요시 특정 IP만 허용
3. **모니터링**: 서버 로그 정기적으로 확인
4. **업데이트**: 보안 패치 정기적으로 적용

## 🚨 문제 해결

### 포트가 이미 사용 중인 경우
```bash
# 포트 사용 확인
netstat -tlnp | grep 12345

# 프로세스 종료
kill -9 <PID>
```

### 서버가 시작되지 않는 경우
1. Python 버전 확인 (3.7+ 필요)
2. 포트 권한 확인
3. 방화벽 설정 확인
4. 로그 메시지 확인

### 클라이언트가 연결되지 않는 경우
1. 서버 IP 주소 확인
2. 포트 번호 확인
3. 네트워크 연결 상태 확인
4. 방화벽 설정 확인

## 📈 성능 최적화

### 서버 성능
- CPU: 최소 1코어, 권장 2코어+
- RAM: 최소 512MB, 권장 1GB+
- 네트워크: 안정적인 인터넷 연결

### 동시 접속자
- 현재 구조: 방당 최대 2명
- 확장 가능: 여러 방 동시 운영

## 📞 지원

문제가 발생하면 서버 로그를 확인하고 GitHub Issues에 제보해주세요.
