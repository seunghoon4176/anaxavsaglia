import sys
import json
import socket
import threading
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                              QListWidget, QTextEdit, QTabWidget, QMessageBox,
                              QGroupBox, QGridLayout, QSpinBox, QComboBox)
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
    
    def __init__(self):
        super().__init__()
        self.socket = None
        self.connected = False
        self.running = False
        
    def connect_to_lobby(self, host='localhost', port=12345):
        """로비 서버에 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            self.running = True
            
            # 메시지 수신 스레드 시작
            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()
            
            return True
        except Exception as e:
            self.error_occurred.emit(f"로비 서버 연결 실패: {e}")
            return False
    
    def receive_messages(self):
        """서버 메시지 수신"""
        while self.running and self.connected:
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
        if self.connected and self.socket:
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
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

class GameLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D 멀티플레이어 격투 게임")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: white;
            }
            QWidget {
                background-color: #2b2b2b;
                color: white;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: 2px solid #6a6a6a;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QLineEdit {
                background-color: #3a3a3a;
                border: 2px solid #5a5a5a;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
            }
            QListWidget {
                background-color: #3a3a3a;
                border: 2px solid #5a5a5a;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #3a3a3a;
                border: 2px solid #5a5a5a;
                border-radius: 3px;
            }
            QLabel {
                font-size: 12px;
            }
            QTabWidget::pane {
                border: 2px solid #5a5a5a;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #4a4a4a;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #6a6a6a;
            }
        """)
        
        # 로비 서버 관련
        self.lobby_server = None
        self.lobby_client = LobbyClient()
        self.lobby_connected = False
        
        # 게임 관련
        self.rooms = {}  # 방 ID -> 방 정보
        self.current_room = None
        self.player_name = ""
        self.selected_character = "anaxa"
        
        # 로비 클라이언트 시그널 연결
        self.lobby_client.room_list_updated.connect(self.on_room_list_updated)
        self.lobby_client.room_joined.connect(self.on_room_joined)
        self.lobby_client.game_ready.connect(self.on_game_ready)
        self.lobby_client.error_occurred.connect(self.on_lobby_error)
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI를 설정합니다"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 타이틀
        title = QLabel("2D 멀티플레이어 격투 게임")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 24, QFont.Bold))
        layout.addWidget(title)
        
        # 탭 위젯
        tab_widget = QTabWidget()
        
        # 메인 메뉴 탭
        main_tab = self.create_main_tab()
        tab_widget.addTab(main_tab, "메인 메뉴")
        
        # 방 목록 탭
        room_tab = self.create_room_tab()
        tab_widget.addTab(room_tab, "방 목록")
        
        # 서버 관리 탭
        server_tab = self.create_server_tab()
        tab_widget.addTab(server_tab, "서버 관리")
        
        layout.addWidget(tab_widget)
        
    def create_main_tab(self):
        """메인 메뉴 탭을 생성합니다"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 플레이어 설정
        player_group = QGroupBox("플레이어 설정")
        player_layout = QGridLayout(player_group)
        
        player_layout.addWidget(QLabel("플레이어 이름:"), 0, 0)
        self.name_input = QLineEdit("Player1")
        player_layout.addWidget(self.name_input, 0, 1)
        
        player_layout.addWidget(QLabel("캐릭터 선택:"), 1, 0)
        self.character_combo = QComboBox()
        self.character_combo.addItems(["anaxa", "aglia"])
        self.character_combo.currentTextChanged.connect(self.on_character_changed)
        player_layout.addWidget(self.character_combo, 1, 1)
        
        layout.addWidget(player_group)
        
        # 캐릭터 프리뷰
        self.character_preview = QLabel()
        self.character_preview.setAlignment(Qt.AlignCenter)
        self.character_preview.setFixedSize(200, 200)
        self.character_preview.setStyleSheet("border: 2px solid #5a5a5a; border-radius: 5px;")
        self.update_character_preview()
        layout.addWidget(self.character_preview)
        
        # 버튼들
        button_layout = QVBoxLayout()
        
        self.create_room_btn = QPushButton("방 만들기")
        self.create_room_btn.clicked.connect(self.create_room)
        button_layout.addWidget(self.create_room_btn)
        
        self.join_room_btn = QPushButton("방 참가하기")
        self.join_room_btn.clicked.connect(self.show_room_list)
        button_layout.addWidget(self.join_room_btn)
        
        self.start_server_btn = QPushButton("서버 시작")
        self.start_server_btn.clicked.connect(self.start_server)
        button_layout.addWidget(self.start_server_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        return widget
    
    def create_room_tab(self):
        """방 목록 탭을 생성합니다"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 방 목록
        layout.addWidget(QLabel("사용 가능한 방:"))
        self.room_list = QListWidget()
        layout.addWidget(self.room_list)
        
        # 방 정보
        self.room_info = QTextEdit()
        self.room_info.setMaximumHeight(100)
        layout.addWidget(self.room_info)
        
        # 버튼들
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.clicked.connect(self.refresh_room_list)
        button_layout.addWidget(self.refresh_btn)
        
        self.join_selected_btn = QPushButton("방 참가")
        self.join_selected_btn.clicked.connect(self.join_selected_room)
        button_layout.addWidget(self.join_selected_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def create_server_tab(self):
        """서버 관리 탭을 생성합니다"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 서버 설정
        server_group = QGroupBox("서버 설정")
        server_layout = QGridLayout(server_group)
        
        server_layout.addWidget(QLabel("포트:"), 0, 0)
        self.port_input = QSpinBox()
        self.port_input.setRange(1000, 65535)
        self.port_input.setValue(12345)
        server_layout.addWidget(self.port_input, 0, 1)
        
        layout.addWidget(server_group)
        
        # 서버 상태
        self.server_status = QLabel("서버 상태: 중지됨")
        layout.addWidget(self.server_status)
        
        # 서버 로그
        layout.addWidget(QLabel("서버 로그:"))
        self.server_log = QTextEdit()
        self.server_log.setReadOnly(True)
        layout.addWidget(self.server_log)
        
        # 서버 제어 버튼
        button_layout = QHBoxLayout()
        
        self.start_server_btn2 = QPushButton("서버 시작")
        self.start_server_btn2.clicked.connect(self.start_server)
        button_layout.addWidget(self.start_server_btn2)
        
        self.stop_server_btn = QPushButton("서버 중지")
        self.stop_server_btn.clicked.connect(self.stop_server)
        self.stop_server_btn.setEnabled(False)
        button_layout.addWidget(self.stop_server_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def on_character_changed(self, character):
        """캐릭터 선택이 변경되었을 때"""
        self.selected_character = character
        self.update_character_preview()
    
    def update_character_preview(self):
        """캐릭터 프리뷰를 업데이트합니다"""
        try:
            # 첫 번째 이미지를 프리뷰로 사용
            image_path = f"{self.selected_character}/1.png"
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.character_preview.setPixmap(scaled_pixmap)
            else:
                self.character_preview.setText(f"{self.selected_character}\n(이미지 없음)")
        except Exception as e:
            self.character_preview.setText(f"{self.selected_character}\n(이미지 로딩 실패)")
    
    def create_room(self):
        """새 방을 만듭니다"""
        self.player_name = self.name_input.text().strip()
        if not self.player_name:
            QMessageBox.warning(self, "경고", "플레이어 이름을 입력해주세요.")
            return
        
        # 로비 서버에 연결되어 있지 않으면 연결 시도
        if not self.lobby_connected:
            if not self.connect_to_lobby():
                return
        
        # 플레이어 정보 설정
        self.lobby_client.set_player_info(self.player_name, self.selected_character)
        
        # 방 생성
        room_name = f"{self.player_name}의 방"
        if self.lobby_client.create_room(room_name):
            self.log_message(f"방 '{room_name}' 생성 요청을 보냈습니다.")
        else:
            QMessageBox.critical(self, "오류", "방 생성 요청 실패")
    
    def connect_to_lobby(self):
        """로비 서버에 연결"""
        if self.lobby_client.connect_to_lobby():
            self.lobby_connected = True
            self.log_message("로비 서버에 연결되었습니다.")
            return True
        else:
            QMessageBox.critical(self, "오류", "로비 서버에 연결할 수 없습니다.\n서버를 먼저 시작해주세요.")
            return False
    
    def show_room_list(self):
        """방 목록을 보여줍니다"""
        # 방 목록 탭으로 전환
        tab_widget = self.centralWidget().findChild(QTabWidget)
        tab_widget.setCurrentIndex(1)
        
        # 로비 서버에 연결되어 있지 않으면 연결 시도
        if not self.lobby_connected:
            if not self.connect_to_lobby():
                return
        
        self.refresh_room_list()
    
    def refresh_room_list(self):
        """방 목록을 새로고침합니다"""
        if self.lobby_connected:
            self.lobby_client.get_room_list()
            self.log_message("방 목록을 요청했습니다.")
        else:
            QMessageBox.warning(self, "경고", "로비 서버에 연결되지 않았습니다.")
    
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
        
        # 방 ID 추출 (아이템 텍스트에서)
        room_text = current_item.text()
        # 방 ID는 임시로 인덱스 사용 (실제로는 서버에서 받아야 함)
        room_index = self.room_list.row(current_item)
        
        if not self.lobby_connected:
            if not self.connect_to_lobby():
                return
        
        # 플레이어 정보 설정
        self.lobby_client.set_player_info(self.player_name, self.selected_character)
        
        # 방 참가 (임시로 room_index 사용)
        if hasattr(self, 'current_room_list') and room_index < len(self.current_room_list):
            room_id = self.current_room_list[room_index]['room_id']
            if self.lobby_client.join_room(room_id):
                self.log_message(f"방 참가 요청을 보냈습니다.")
            else:
                QMessageBox.critical(self, "오류", "방 참가 요청 실패")
        else:
            QMessageBox.warning(self, "경고", "방 정보를 찾을 수 없습니다.")
    
    def start_server(self):
        """서버를 시작합니다"""
        try:
            from lobby_server import LobbyServer
            port = self.port_input.value()
            
            # 이미 서버가 실행 중이면 중지
            if hasattr(self, 'lobby_server') and self.lobby_server:
                self.stop_server()
            
            self.lobby_server = LobbyServer('localhost', port)
            
            # 서버를 별도 스레드에서 실행
            self.server_thread = threading.Thread(target=self.lobby_server.start, daemon=True)
            self.server_thread.start()
            
            self.server_status.setText(f"서버 상태: 실행 중 (포트 {port})")
            self.start_server_btn.setEnabled(False)
            self.start_server_btn2.setEnabled(False)
            self.stop_server_btn.setEnabled(True)
            
            self.log_message(f"로비 서버가 포트 {port}에서 시작되었습니다.")
            
            # 잠시 후 로비 서버에 연결
            QTimer.singleShot(1000, self.connect_to_lobby)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"서버 시작 실패: {e}")
            self.log_message(f"서버 시작 실패: {e}")
    
    def stop_server(self):
        """서버를 중지합니다"""
        try:
            if hasattr(self, 'lobby_server'):
                self.lobby_server.shutdown()
            
            self.server_status.setText("서버 상태: 중지됨")
            self.start_server_btn.setEnabled(True)
            self.start_server_btn2.setEnabled(True)
            self.stop_server_btn.setEnabled(False)
            
            self.log_message("서버가 중지되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"서버 중지 실패: {e}")
    
    def log_message(self, message):
        """서버 로그에 메시지를 추가합니다"""
        if hasattr(self, 'server_log'):
            timestamp = time.strftime("%H:%M:%S")
            self.server_log.append(f"[{timestamp}] {message}")
    
    def on_room_list_updated(self, rooms):
        """방 목록이 업데이트되었을 때"""
        self.current_room_list = rooms
        self.room_list.clear()
        
        for room in rooms:
            room_text = f"{room['name']} ({room['players']}/{room['max_players']})"
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
        host = game_server_info.get('host', 'localhost')
        port = game_server_info.get('port', 13000)
        
        self.log_message(f"게임 서버 준비 완료: {host}:{port}")
        QMessageBox.information(self, "게임 시작", f"게임이 시작됩니다!\n서버: {host}:{port}")
        
        # 게임 시작
        self.start_game(host, port)
    
    def on_lobby_error(self, error_message):
        """로비 에러가 발생했을 때"""
        self.log_message(f"로비 오류: {error_message}")
        QMessageBox.warning(self, "로비 오류", error_message)
    
    def start_game(self, host='localhost', port=13000):
        """게임을 시작합니다"""
        try:
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
        
        # 서버 중지
        if hasattr(self, 'lobby_server') and self.lobby_server:
            self.stop_server()
        
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
