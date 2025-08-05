import sys
import json
import socket
import threading
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                              QListWidget, QTextEdit, QMessageBox,
                              QGroupBox, QGridLayout, QComboBox, QFrame)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QFont, QPixmap, QPalette, QColor
import pygame
from game_client import GameClient

class LobbyClient(QObject):
    """로비 서버와 통신하는 클라이언트"""
    room_list_updated = Signal(list)
    room_joined = Signal(dict)
    game_ready = Signal(dict)
    error_occurred = Signal(str)
    connected = Signal()
    disconnected = Signal()
    
    def __init__(self):
        super().__init__()
        self.socket = None
        self.is_connected = False
        self.running = False
        
    def connect_to_server(self, host, port):
        """서버에 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.is_connected = True
            self.running = True
            
            # 메시지 수신 스레드 시작
            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()
            
            self.connected.emit()
            return True
        except Exception as e:
            self.error_occurred.emit(f"서버 연결 실패: {e}")
            return False
    
    def receive_messages(self):
        """서버 메시지 수신"""
        while self.running and self.is_connected:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                self.handle_message(message)
                
            except Exception as e:
                if self.running:
                    self.error_occurred.emit(f"메시지 수신 오류: {e}")
                break
        
        self.is_connected = False
        self.disconnected.emit()
    
    def handle_message(self, message):
        """서버 메시지 처리"""
        msg_type = message.get('type')
        
        if msg_type == 'room_list':
            self.room_list_updated.emit(message.get('rooms', []))
        elif msg_type == 'room_created' or msg_type == 'room_joined':
            self.room_joined.emit(message.get('room_info', {}))
        elif msg_type == 'game_ready':
            self.game_ready.emit(message)
        elif msg_type == 'error':
            self.error_occurred.emit(message.get('message', '알 수 없는 오류'))
    
    def send_message(self, message):
        """서버에 메시지 전송"""
        if self.is_connected and self.socket:
            try:
                self.socket.send(json.dumps(message).encode('utf-8'))
                return True
            except Exception as e:
                self.error_occurred.emit(f"메시지 전송 오류: {e}")
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
    
    def disconnect(self):
        """연결 해제"""
        self.running = False
        self.is_connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

class GameLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D 멀티플레이어 격투 게임")
        self.setGeometry(100, 100, 1000, 700)
        self.setFixedSize(1000, 700)  # 고정 크기
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: white;
            }
            QWidget {
                background-color: #1e1e1e;
                color: white;
            }
            QPushButton {
                background-color: #3e3e3e;
                color: white;
                border: 2px solid #5e5e5e;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4e4e4e;
                border-color: #7e7e7e;
            }
            QPushButton:pressed {
                background-color: #2e2e2e;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666;
                border-color: #444;
            }
            QLineEdit {
                background-color: #2a2a2a;
                border: 2px solid #4a4a4a;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QListWidget {
                background-color: #2a2a2a;
                border: 2px solid #4a4a4a;
                border-radius: 5px;
                padding: 5px;
            }
            QTextEdit {
                background-color: #2a2a2a;
                border: 2px solid #4a4a4a;
                border-radius: 5px;
                padding: 5px;
            }
            QLabel {
                font-size: 12px;
                color: #ddd;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                margin: 10px 0;
                padding-top: 15px;
            }
            QGroupBox::title {
                color: #0078d4;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QComboBox {
                background-color: #2a2a2a;
                border: 2px solid #4a4a4a;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)
        
        # 서버 설정 (외부 서버 주소를 여기서 설정)
        self.server_host = "localhost"  # 배포시 실제 서버 IP로 변경
        self.server_port = 12345
        
        # 로비 클라이언트
        self.lobby_client = LobbyClient()
        self.current_room_list = []
        self.current_room = None
        self.player_name = ""
        self.selected_character = "anaxa"
        
        # 시그널 연결
        self.lobby_client.room_list_updated.connect(self.on_room_list_updated)
        self.lobby_client.room_joined.connect(self.on_room_joined)
        self.lobby_client.game_ready.connect(self.on_game_ready)
        self.lobby_client.error_occurred.connect(self.on_lobby_error)
        self.lobby_client.connected.connect(self.on_connected)
        self.lobby_client.disconnected.connect(self.on_disconnected)
        
        self.setup_ui()
        
        # 자동으로 서버에 연결 시도
        QTimer.singleShot(500, self.auto_connect)
        
    def setup_ui(self):
        """UI를 설정합니다"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃 (수평)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 왼쪽 패널 (플레이어 설정 & 캐릭터)
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 중앙 패널 (방 목록 & 로그)
        center_panel = self.create_center_panel()
        main_layout.addWidget(center_panel, 2)
        
        # 오른쪽 패널 (버튼들)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)
        
    def create_left_panel(self):
        """왼쪽 패널 생성"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        
        # 타이틀
        title = QLabel("2D 격투 게임")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #0078d4; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 플레이어 설정
        player_group = QGroupBox("플레이어 설정")
        player_layout = QGridLayout(player_group)
        
        player_layout.addWidget(QLabel("플레이어 이름:"), 0, 0)
        self.name_input = QLineEdit("Player1")
        player_layout.addWidget(self.name_input, 0, 1)
        
        player_layout.addWidget(QLabel("캐릭터:"), 1, 0)
        self.character_combo = QComboBox()
        self.character_combo.addItems(["anaxa", "aglia"])
        self.character_combo.currentTextChanged.connect(self.on_character_changed)
        player_layout.addWidget(self.character_combo, 1, 1)
        
        layout.addWidget(player_group)
        
        # 캐릭터 프리뷰
        preview_group = QGroupBox("캐릭터 프리뷰")
        preview_layout = QVBoxLayout(preview_group)
        
        self.character_preview = QLabel()
        self.character_preview.setAlignment(Qt.AlignCenter)
        self.character_preview.setFixedSize(150, 150)
        self.character_preview.setStyleSheet("border: 2px solid #4a4a4a; border-radius: 5px; background-color: #2a2a2a;")
        self.update_character_preview()
        preview_layout.addWidget(self.character_preview)
        
        layout.addWidget(preview_group)
        
        # 연결 상태
        self.connection_status = QLabel("연결 상태: 연결 시도 중...")
        self.connection_status.setStyleSheet("color: #ffa500; font-weight: bold;")
        layout.addWidget(self.connection_status)
        
        layout.addStretch()
        return panel
    
    def create_center_panel(self):
        """중앙 패널 생성"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        
        # 방 목록
        room_group = QGroupBox("게임 방 목록")
        room_layout = QVBoxLayout(room_group)
        
        # 새로고침 버튼
        refresh_btn = QPushButton("🔄 방 목록 새로고침")
        refresh_btn.clicked.connect(self.refresh_room_list)
        room_layout.addWidget(refresh_btn)
        
        self.room_list = QListWidget()
        self.room_list.setMinimumHeight(200)
        room_layout.addWidget(self.room_list)
        
        layout.addWidget(room_group)
        
        # 게임 로그
        log_group = QGroupBox("게임 로그")
        log_layout = QVBoxLayout(log_group)
        
        self.game_log = QTextEdit()
        self.game_log.setReadOnly(True)
        self.game_log.setMaximumHeight(200)
        log_layout.addWidget(self.game_log)
        
        layout.addWidget(log_group)
        
        return panel
    
    def create_right_panel(self):
        """오른쪽 패널 생성"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        
        # 게임 액션 버튼들
        action_group = QGroupBox("게임 액션")
        action_layout = QVBoxLayout(action_group)
        
        self.create_room_btn = QPushButton("🏠 방 만들기")
        self.create_room_btn.setMinimumHeight(50)
        self.create_room_btn.clicked.connect(self.create_room)
        action_layout.addWidget(self.create_room_btn)
        
        self.join_room_btn = QPushButton("🚪 방 참가하기")
        self.join_room_btn.setMinimumHeight(50)
        self.join_room_btn.clicked.connect(self.join_selected_room)
        action_layout.addWidget(self.join_room_btn)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #4a4a4a;")
        action_layout.addWidget(line)
        
        self.reconnect_btn = QPushButton("🔌 서버 재연결")
        self.reconnect_btn.clicked.connect(self.reconnect_to_server)
        action_layout.addWidget(self.reconnect_btn)
        
        layout.addWidget(action_group)
        
        # 서버 정보
        server_group = QGroupBox("서버 정보")
        server_layout = QVBoxLayout(server_group)
        
        self.server_info = QLabel(f"서버: {self.server_host}:{self.server_port}")
        self.server_info.setStyleSheet("color: #0078d4;")
        server_layout.addWidget(self.server_info)
        
        layout.addWidget(server_group)
        
        # 게임 규칙
        rules_group = QGroupBox("게임 규칙")
        rules_layout = QVBoxLayout(rules_group)
        
        rules = [
            "• 체력: 100",
            "• 공격 데미지: 20",
            "• 제한 시간: 3분",
            "• 조작: WASD, SPACE"
        ]
        
        for rule in rules:
            rule_label = QLabel(rule)
            rule_label.setStyleSheet("color: #ccc; font-size: 11px;")
            rules_layout.addWidget(rule_label)
        
        layout.addWidget(rules_group)
        
        layout.addStretch()
        return panel
    
    def auto_connect(self):
        """자동 서버 연결"""
        self.log_message("서버에 연결을 시도합니다...")
        if not self.lobby_client.connect_to_server(self.server_host, self.server_port):
            self.log_message("서버 연결 실패. 수동으로 재연결해주세요.")
    
    def reconnect_to_server(self):
        """서버 재연결"""
        self.lobby_client.disconnect()
        time.sleep(0.5)
        self.auto_connect()
    
    def on_character_changed(self, character):
        """캐릭터 선택이 변경되었을 때"""
        self.selected_character = character
        self.update_character_preview()
    
    def update_character_preview(self):
        """캐릭터 프리뷰를 업데이트합니다"""
        try:
            image_path = f"{self.selected_character}/1.png"
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(130, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.character_preview.setPixmap(scaled_pixmap)
            else:
                self.character_preview.setText(f"{self.selected_character}\n(이미지 없음)")
        except Exception as e:
            self.character_preview.setText(f"{self.selected_character}\n(로딩 실패)")
    
    def create_room(self):
        """새 방을 만듭니다"""
        self.player_name = self.name_input.text().strip()
        if not self.player_name:
            QMessageBox.warning(self, "경고", "플레이어 이름을 입력해주세요.")
            return
        
        if not self.lobby_client.is_connected:
            QMessageBox.warning(self, "경고", "서버에 연결되지 않았습니다.")
            return
        
        # 플레이어 정보 설정
        self.lobby_client.set_player_info(self.player_name, self.selected_character)
        
        # 방 생성
        room_name = f"{self.player_name}의 방"
        if self.lobby_client.create_room(room_name):
            self.log_message(f"방 '{room_name}' 생성 요청을 보냈습니다.")
        else:
            QMessageBox.critical(self, "오류", "방 생성 요청 실패")
    
    def join_selected_room(self):
        """선택된 방에 참가합니다"""
        current_item = self.room_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "경고", "참가할 방을 선택해주세요.")
            return
        
        self.player_name = self.name_input.text().strip()
        if not self.player_name:
            QMessageBox.warning(self, "경고", "플레이어 이름을 입력해주세요.")
            return
        
        if not self.lobby_client.is_connected:
            QMessageBox.warning(self, "경고", "서버에 연결되지 않았습니다.")
            return
        
        # 방 ID 추출
        room_index = self.room_list.row(current_item)
        if room_index < len(self.current_room_list):
            room_id = self.current_room_list[room_index]['room_id']
            
            # 플레이어 정보 설정
            self.lobby_client.set_player_info(self.player_name, self.selected_character)
            
            if self.lobby_client.join_room(room_id):
                self.log_message(f"방 참가 요청을 보냈습니다.")
            else:
                QMessageBox.critical(self, "오류", "방 참가 요청 실패")
        else:
            QMessageBox.warning(self, "경고", "방 정보를 찾을 수 없습니다.")
    
    def refresh_room_list(self):
        """방 목록을 새로고침합니다"""
        if self.lobby_client.is_connected:
            self.lobby_client.get_room_list()
            self.log_message("방 목록을 요청했습니다.")
        else:
            QMessageBox.warning(self, "경고", "서버에 연결되지 않았습니다.")
    
    def log_message(self, message):
        """게임 로그에 메시지를 추가합니다"""
        timestamp = time.strftime("%H:%M:%S")
        self.game_log.append(f"[{timestamp}] {message}")
    
    def on_connected(self):
        """서버에 연결되었을 때"""
        self.connection_status.setText("연결 상태: 연결됨 ✅")
        self.connection_status.setStyleSheet("color: #00ff00; font-weight: bold;")
        self.log_message("서버에 연결되었습니다.")
        self.refresh_room_list()
    
    def on_disconnected(self):
        """서버 연결이 끊어졌을 때"""
        self.connection_status.setText("연결 상태: 연결 끊어짐 ❌")
        self.connection_status.setStyleSheet("color: #ff0000; font-weight: bold;")
        self.log_message("서버 연결이 끊어졌습니다.")
    
    def on_room_list_updated(self, rooms):
        """방 목록이 업데이트되었을 때"""
        self.current_room_list = rooms
        self.room_list.clear()
        
        for room in rooms:
            room_text = f"🏠 {room['name']} ({room['players']}/{room['max_players']})"
            self.room_list.addItem(room_text)
        
        self.log_message(f"방 목록 업데이트: {len(rooms)}개의 방")
    
    def on_room_joined(self, room_info):
        """방에 참가했을 때"""
        self.current_room = room_info
        room_name = room_info.get('name', '알 수 없는 방')
        players = room_info.get('players', 0)
        max_players = room_info.get('max_players', 2)
        
        self.log_message(f"방 '{room_name}'에 참가했습니다. ({players}/{max_players})")
        
        if players >= max_players:
            QMessageBox.information(self, "게임 시작", "모든 플레이어가 모였습니다!\n게임이 곧 시작됩니다.")
    
    def on_game_ready(self, game_info):
        """게임이 준비되었을 때"""
        game_server_info = game_info.get('game_server', {})
        host = game_server_info.get('host', self.server_host)
        port = game_server_info.get('port', 13000)
        
        self.log_message(f"게임 서버 준비 완료: {host}:{port}")
        QMessageBox.information(self, "게임 시작", f"게임이 시작됩니다!\n서버: {host}:{port}")
        
        # 게임 시작
        self.start_game(host, port)
    
    def on_lobby_error(self, error_message):
        """로비 에러가 발생했을 때"""
        self.log_message(f"오류: {error_message}")
        QMessageBox.warning(self, "오류", error_message)
    
    def start_game(self, host=None, port=13000):
        """게임을 시작합니다"""
        try:
            if not host:
                host = self.server_host
                
            self.hide()  # UI 숨기기
            
            # Pygame 초기화
            pygame.init()
            
            # 화면 설정
            SCREEN_WIDTH = 1200
            SCREEN_HEIGHT = 800
            screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("2D 멀티플레이어 격투 게임")
            
            # 게임 클라이언트 생성
            client = GameClient(screen, SCREEN_WIDTH, SCREEN_HEIGHT)
            client.player_name = self.player_name
            client.selected_character = self.selected_character
            
            # 게임 서버에 연결
            if client.connect_to_server(host, port):
                # 게임 실행
                client.run()
            else:
                QMessageBox.critical(self, "오류", f"게임 서버({host}:{port})에 연결할 수 없습니다.")
            
            # 게임 종료 후 UI 다시 표시
            pygame.quit()
            self.show()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"게임 실행 실패: {e}")
            self.log_message(f"게임 실행 실패: {e}")
            self.show()
    
    def closeEvent(self, event):
        """창이 닫힐 때"""
        # 로비 클라이언트 연결 해제
        if self.lobby_client:
            self.lobby_client.disconnect()
        
        event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 다크 테마 설정
    app.setStyle('Fusion')
    
    launcher = GameLauncher()
    launcher.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
