#!/usr/bin/env python3
"""
통합 서버용 클라이언트 런처
"""

import sys
import json
import socket
import threading
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QListWidget, 
                             QLineEdit, QLabel, QComboBox, QTextEdit,
                             QMessageBox, QListWidgetItem, QGroupBox,
                             QProgressBar)
from PySide6.QtCore import QTimer, QThread, Signal
from PySide6.QtGui import QFont

class LobbyClient(QThread):
    """로비 서버와 통신하는 클라이언트"""
    
    # 시그널 정의
    connected = Signal()
    disconnected = Signal()
    room_list_updated = Signal(list)
    room_created = Signal(dict)
    room_joined = Signal(dict)
    game_ready = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, host='localhost', port=12345):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = None
        self.running = True
        
    def run(self):
        """클라이언트 스레드 실행"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected.emit()
            
            while self.running:
                try:
                    data = self.socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                        
                    message = json.loads(data)
                    self.handle_message(message)
                    
                except json.JSONDecodeError:
                    continue
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"메시지 수신 오류: {e}")
                    break
                    
        except Exception as e:
            self.error_occurred.emit(f"서버 연결 실패: {e}")
        finally:
            self.cleanup()
    
    def handle_message(self, message):
        """서버로부터 받은 메시지 처리"""
        msg_type = message.get('type')
        
        if msg_type == 'room_list':
            self.room_list_updated.emit(message.get('rooms', []))
        elif msg_type == 'room_created':
            self.room_created.emit(message)
        elif msg_type == 'room_joined':
            self.room_joined.emit(message)
        elif msg_type == 'game_ready':
            self.game_ready.emit(message)
        elif msg_type == 'error':
            self.error_occurred.emit(message.get('message', '알 수 없는 오류'))
    
    def send_message(self, message):
        """서버에 메시지 전송"""
        if self.socket:
            try:
                self.socket.send(json.dumps(message).encode('utf-8'))
                return True
            except Exception as e:
                print(f"메시지 전송 오류: {e}")
                return False
        return False
    
    def set_player_info(self, name, character):
        """플레이어 정보 설정"""
        return self.send_message({
            'type': 'set_player_info',
            'name': name,
            'character': character
        })
    
    def create_room(self, room_name):
        """방 생성"""
        return self.send_message({
            'type': 'create_room',
            'room_name': room_name
        })
    
    def join_room(self, room_id):
        """방 참가"""
        return self.send_message({
            'type': 'join_room',
            'room_id': room_id
        })
    
    def get_room_list(self):
        """방 목록 요청"""
        return self.send_message({
            'type': 'get_room_list'
        })
    
    def stop(self):
        """클라이언트 중지"""
        self.running = False
    
    def cleanup(self):
        """리소스 정리"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.disconnected.emit()

class UnifiedGameLauncher(QMainWindow):
    """통합 게임 런처 (하나의 서버용)"""
    
    def __init__(self):
        super().__init__()
        self.lobby_client = None
        self.current_room_id = None
        self.player_id = None
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("2D 격투 게임 런처 (통합 서버)")
        self.setFixedSize(900, 600)
        
        # 다크 테마 스타일 설정
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 10px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 2px solid #666666;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border-color: #888888;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
                border-color: #444444;
            }
            QLineEdit, QComboBox {
                background-color: #3a3a3a;
                border: 2px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #777777;
            }
            QListWidget {
                background-color: #3a3a3a;
                border: 2px solid #555555;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #555555;
            }
            QListWidget::item:hover {
                background-color: #4a4a4a;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 2px solid #555555;
                border-radius: 5px;
                font-family: 'Consolas', monospace;
            }
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        
        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 전체 수직 레이아웃
        main_container_layout = QVBoxLayout(main_widget)
        
        # 상단: 수평 레이아웃 (좌측, 중앙, 우측)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        
        # 좌측: 플레이어 설정
        left_group = QGroupBox("플레이어 설정")
        left_group.setMaximumWidth(280)
        left_layout = QVBoxLayout(left_group)
        
        # 서버 연결 설정
        server_group = QGroupBox("서버 설정")
        server_layout = QVBoxLayout(server_group)
        
        self.server_host_input = QLineEdit("localhost")
        self.server_port_input = QLineEdit("12345")
        
        server_layout.addWidget(QLabel("서버 주소:"))
        server_layout.addWidget(self.server_host_input)
        server_layout.addWidget(QLabel("포트:"))
        server_layout.addWidget(self.server_port_input)
        
        left_layout.addWidget(server_group)
        
        # 플레이어 정보 설정
        player_group = QGroupBox("플레이어 정보")
        player_layout = QVBoxLayout(player_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("플레이어 이름을 입력하세요")
        
        self.character_combo = QComboBox()
        self.character_combo.addItems(["anaxa", "aglia"])
        
        player_layout.addWidget(QLabel("이름:"))
        player_layout.addWidget(self.name_input)
        player_layout.addWidget(QLabel("캐릭터:"))
        player_layout.addWidget(self.character_combo)
        
        left_layout.addWidget(player_group)
        
        # 연결 상태
        status_group = QGroupBox("연결 상태")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("연결되지 않음")
        self.status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        
        self.connect_btn = QPushButton("서버 연결")
        self.disconnect_btn = QPushButton("연결 해제")
        self.disconnect_btn.setEnabled(False)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.connect_btn)
        status_layout.addWidget(self.disconnect_btn)
        
        left_layout.addWidget(status_group)
        left_layout.addStretch()
        
        top_layout.addWidget(left_group)
        
        # 중앙: 방 목록
        center_group = QGroupBox("방 목록")
        center_layout = QVBoxLayout(center_group)
        
        self.room_list = QListWidget()
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.setEnabled(False)
        
        center_layout.addWidget(self.room_list)
        center_layout.addWidget(self.refresh_btn)
        
        top_layout.addWidget(center_group)
        
        # 우측: 방 관리
        right_group = QGroupBox("방 관리")
        right_group.setMaximumWidth(280)
        right_layout = QVBoxLayout(right_group)
        
        # 방 생성
        create_group = QGroupBox("방 생성")
        create_layout = QVBoxLayout(create_group)
        
        self.room_name_input = QLineEdit()
        self.room_name_input.setPlaceholderText("방 이름을 입력하세요")
        
        self.create_room_btn = QPushButton("방 생성")
        self.create_room_btn.setEnabled(False)
        
        create_layout.addWidget(QLabel("방 이름:"))
        create_layout.addWidget(self.room_name_input)
        create_layout.addWidget(self.create_room_btn)
        
        right_layout.addWidget(create_group)
        
        # 방 참가
        join_group = QGroupBox("방 참가")
        join_layout = QVBoxLayout(join_group)
        
        self.join_room_btn = QPushButton("선택한 방 참가")
        self.join_room_btn.setEnabled(False)
        
        join_layout.addWidget(self.join_room_btn)
        
        right_layout.addWidget(join_group)
        
        # 게임 시작
        game_group = QGroupBox("게임")
        game_layout = QVBoxLayout(game_group)
        
        self.current_room_label = QLabel("참가한 방: 없음")
        self.start_game_btn = QPushButton("게임 시작")
        self.start_game_btn.setEnabled(False)
        
        game_layout.addWidget(self.current_room_label)
        game_layout.addWidget(self.start_game_btn)
        
        right_layout.addWidget(game_group)
        right_layout.addStretch()
        
        top_layout.addWidget(right_group)
        
        # 상단 레이아웃을 메인 컨테이너에 추가
        main_container_layout.addLayout(top_layout)
        
        # 하단: 로그
        log_group = QGroupBox("로그")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        main_container_layout.addWidget(log_group)
        
        # 타이머 설정 (방 목록 자동 새로고침)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh_rooms)
        
    def setup_connections(self):
        """시그널-슬롯 연결 설정"""
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.disconnect_btn.clicked.connect(self.disconnect_from_server)
        self.refresh_btn.clicked.connect(self.refresh_room_list)
        self.create_room_btn.clicked.connect(self.create_room)
        self.join_room_btn.clicked.connect(self.join_room)
        self.start_game_btn.clicked.connect(self.start_game)
        
        # 엔터 키 처리
        self.name_input.returnPressed.connect(self.connect_to_server)
        self.room_name_input.returnPressed.connect(self.create_room)
        
    def log_message(self, message):
        """로그 메시지 출력"""
        try:
            if hasattr(self, 'log_text') and self.log_text:
                self.log_text.append(f"[{self.get_current_time()}] {message}")
            else:
                print(f"[{self.get_current_time()}] {message}")
        except RuntimeError:
            # QTextEdit이 이미 삭제된 경우
            print(f"[{self.get_current_time()}] {message}")
        
    def get_current_time(self):
        """현재 시간 반환"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
        
    def connect_to_server(self):
        """서버에 연결"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "경고", "플레이어 이름을 입력해주세요!")
            return
        
        host = self.server_host_input.text().strip() or "localhost"
        try:
            port = int(self.server_port_input.text().strip() or "12345")
        except ValueError:
            QMessageBox.warning(self, "경고", "올바른 포트 번호를 입력해주세요!")
            return
        
        self.log_message(f"서버 연결 시도: {host}:{port}")
        
        # 로비 클라이언트 생성 및 연결
        self.lobby_client = LobbyClient(host, port)
        self.lobby_client.connected.connect(self.on_connected)
        self.lobby_client.disconnected.connect(self.on_disconnected)
        self.lobby_client.room_list_updated.connect(self.update_room_list)
        self.lobby_client.room_created.connect(self.on_room_created)
        self.lobby_client.room_joined.connect(self.on_room_joined)
        self.lobby_client.game_ready.connect(self.on_game_ready)
        self.lobby_client.error_occurred.connect(self.on_error)
        
        self.lobby_client.start()
        
    def disconnect_from_server(self):
        """서버 연결 해제"""
        if self.lobby_client:
            self.lobby_client.stop()
            self.lobby_client.wait()
            self.lobby_client = None
        
    def on_connected(self):
        """서버 연결 성공"""
        self.status_label.setText("연결됨")
        self.status_label.setStyleSheet("color: #44ff44; font-weight: bold;")
        
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.create_room_btn.setEnabled(True)
        self.join_room_btn.setEnabled(True)
        
        self.log_message("서버에 연결되었습니다!")
        
        # 플레이어 정보 전송
        name = self.name_input.text().strip()
        character = self.character_combo.currentText()
        self.lobby_client.set_player_info(name, character)
        
        # 방 목록 요청
        self.refresh_room_list()
        
        # 자동 새로고침 시작
        self.refresh_timer.start(5000)  # 5초마다
        
    def on_disconnected(self):
        """서버 연결 해제"""
        self.status_label.setText("연결되지 않음")
        self.status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.create_room_btn.setEnabled(False)
        self.join_room_btn.setEnabled(False)
        self.start_game_btn.setEnabled(False)
        
        self.current_room_id = None
        self.player_id = None
        self.current_room_label.setText("참가한 방: 없음")
        
        self.refresh_timer.stop()
        self.log_message("서버 연결이 해제되었습니다")
        
    def refresh_room_list(self):
        """방 목록 새로고침"""
        if self.lobby_client:
            self.lobby_client.get_room_list()
            
    def auto_refresh_rooms(self):
        """자동 방 목록 새로고침"""
        if self.lobby_client and not self.current_room_id:
            self.refresh_room_list()
            
    def update_room_list(self, rooms):
        """방 목록 업데이트"""
        self.room_list.clear()
        
        for room in rooms:
            item_text = f"{room['name']} ({room['players']}/{room['max_players']}) - {room['status']}"
            item = QListWidgetItem(item_text)
            item.setData(1, room['room_id'])  # room_id 저장
            self.room_list.addItem(item)
            
    def create_room(self):
        """방 생성"""
        room_name = self.room_name_input.text().strip()
        if not room_name:
            QMessageBox.warning(self, "경고", "방 이름을 입력해주세요!")
            return
            
        if self.lobby_client:
            self.lobby_client.create_room(room_name)
            self.log_message(f"방 생성 요청: {room_name}")
            
    def join_room(self):
        """방 참가"""
        current_item = self.room_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "경고", "참가할 방을 선택해주세요!")
            return
            
        room_id = current_item.data(1)
        if self.lobby_client:
            self.lobby_client.join_room(room_id)
            self.log_message(f"방 참가 요청: {room_id}")
            
    def on_room_created(self, data):
        """방 생성 성공"""
        self.current_room_id = data['room_id']
        self.player_id = data['player_id']
        room_info = data['room_info']
        
        self.current_room_label.setText(f"참가한 방: {room_info['name']} (방장)")
        self.room_name_input.clear()
        
        self.log_message(f"방을 생성했습니다: {room_info['name']}")
        self.refresh_room_list()
        
    def on_room_joined(self, data):
        """방 참가 성공"""
        self.current_room_id = data['room_id']
        self.player_id = data['player_id']
        room_info = data['room_info']
        
        self.current_room_label.setText(f"참가한 방: {room_info['name']}")
        
        self.log_message(f"방에 참가했습니다: {room_info['name']}")
        self.refresh_room_list()
        
    def on_game_ready(self, data):
        """게임 준비 완료"""
        self.current_room_id = data.get('room_id', self.current_room_id)
        self.player_id = data['player_id']
        room_info = data['room_info']
        
        self.current_room_label.setText(f"게임 중: {room_info['name']}")
        self.start_game_btn.setEnabled(True)
        
        self.log_message("게임이 시작됩니다! 게임 시작 버튼을 클릭하세요.")
        
        # 자동으로 게임 시작
        QTimer.singleShot(1000, self.start_game)
        
    def start_game(self):
        """게임 클라이언트 실행"""
        if not self.current_room_id or not self.player_id:
            QMessageBox.warning(self, "경고", "게임을 시작할 수 없습니다!")
            return
        
        try:
            # 통합 서버 주소 사용
            server_host = self.server_host_input.text().strip() or "localhost"
            server_port = int(self.server_port_input.text().strip() or "12345")
            
            # 게임 클라이언트 실행
            subprocess.Popen([
                sys.executable, "game_client.py",
                "--server-host", server_host,
                "--server-port", str(server_port),
                "--player-id", str(self.player_id),
                "--player-name", self.name_input.text().strip(),
                "--character", self.character_combo.currentText()
            ])
            
            self.log_message("게임 클라이언트를 실행했습니다!")
            
        except Exception as e:
            self.log_message(f"게임 실행 오류: {e}")
            QMessageBox.critical(self, "오류", f"게임을 실행할 수 없습니다:\n{e}")
            
    def on_error(self, error_message):
        """오류 처리"""
        self.log_message(f"오류: {error_message}")
        QMessageBox.warning(self, "오류", error_message)
        
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        if self.lobby_client:
            self.lobby_client.stop()
            self.lobby_client.wait()
        event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 모던한 스타일 사용
    
    launcher = UnifiedGameLauncher()
    launcher.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
