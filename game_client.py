import pygame
import socket
import threading
import json
from player import Player
from game_state import GameState

class GameClient:
    def __init__(self, screen, width, height):
        self.screen = screen
        self.width = width
        self.height = height
        self.clock = pygame.time.Clock()
        self.running = True
        
        # 네트워크 설정
        self.socket = None
        self.connected = False
        self.player_id = None
        
        # 플레이어 설정
        self.player_name = "Player"
        self.selected_character = "anaxa"
        
        # 게임 상태
        self.game_state = GameState()
        self.local_player = None
        
        # 색상 정의
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 0, 255)
        self.GREEN = (0, 255, 0)
        
        # 폰트
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
    def connect_to_server(self, host='localhost', port=12345):
        """서버에 연결합니다."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            
            # 서버로부터 플레이어 ID 받기
            data = self.socket.recv(1024).decode()
            response = json.loads(data)
            self.player_id = response['player_id']
            
            # 로컬 플레이어 생성
            if self.player_id == 1:
                self.local_player = Player(200, self.height - 200, self.RED, 
                                         self.player_name, self.selected_character)
            else:
                self.local_player = Player(self.width - 200, self.height - 200, self.BLUE, 
                                         self.player_name, self.selected_character)
            
            # 서버로부터 메시지 수신 스레드 시작
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            print(f"서버에 연결됨. 플레이어 ID: {self.player_id}")
            return True
            
        except Exception as e:
            print(f"서버 연결 실패: {e}")
            return False
    
    def receive_messages(self):
        """서버로부터 메시지를 수신합니다."""
        while self.connected:
            try:
                data = self.socket.recv(1024).decode()
                if data:
                    message = json.loads(data)
                    self.handle_server_message(message)
            except Exception as e:
                print(f"메시지 수신 오류: {e}")
                self.connected = False
                break
    
    def handle_server_message(self, message):
        """서버 메시지를 처리합니다."""
        if message['type'] == 'game_state':
            self.game_state.update_from_dict(message['data'])
        elif message['type'] == 'player_disconnect':
            print("상대방이 연결을 끊었습니다.")
    
    def send_player_input(self, action, data=None):
        """플레이어 입력을 서버로 전송합니다."""
        if self.connected and self.socket:
            try:
                message = {
                    'type': 'player_input',
                    'player_id': self.player_id,
                    'action': action,
                    'data': data
                }
                self.socket.send(json.dumps(message).encode())
            except Exception as e:
                print(f"메시지 전송 오류: {e}")
    
    def handle_input(self):
        """사용자 입력을 처리합니다."""
        keys = pygame.key.get_pressed()
        
        if not self.local_player:
            return
        
        # 이동 입력
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.local_player.move_left()
            self.send_player_input('move', {'direction': 'left'})
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.local_player.move_right(self.width)
            self.send_player_input('move', {'direction': 'right'})
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            if self.local_player.on_ground:
                self.local_player.jump()
                self.send_player_input('jump')
        
        # 공격 입력 (이벤트 기반)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.local_player.attack()
                    self.send_player_input('attack')
    
    def update_game(self):
        """게임 상태를 업데이트합니다."""
        if self.local_player:
            self.local_player.update(self.height)
    
    def draw(self):
        """화면을 그립니다."""
        self.screen.fill(self.WHITE)
        
        if not self.connected:
            # 연결 대기 화면
            text = self.font.render("서버에 연결 중...", True, self.BLACK)
            text_rect = text.get_rect(center=(self.width//2, self.height//2))
            self.screen.blit(text, text_rect)
            
            instruction = self.small_font.render("서버를 먼저 실행해주세요 (server.py)", True, self.BLACK)
            instruction_rect = instruction.get_rect(center=(self.width//2, self.height//2 + 50))
            self.screen.blit(instruction, instruction_rect)
        else:
            # 게임 화면
            
            # 지면 그리기
            ground_y = self.height - 100
            pygame.draw.rect(self.screen, self.GREEN, (0, ground_y, self.width, 100))
            
            # 플레이어들 그리기
            if self.local_player:
                self.local_player.draw(self.screen)
            
            # 다른 플레이어들 그리기 (서버에서 받은 데이터)
            for player_data in self.game_state.players.values():
                if player_data['id'] != self.player_id:
                    # 상대방 플레이어 그리기
                    color = self.BLUE if player_data['id'] == 2 else self.RED
                    pygame.draw.rect(self.screen, color, 
                                   (player_data['x'], player_data['y'], 50, 80))
                    
                    # 체력바
                    health_ratio = player_data['health'] / 100
                    pygame.draw.rect(self.screen, self.RED, 
                                   (player_data['x'], player_data['y'] - 20, 50, 10))
                    pygame.draw.rect(self.screen, self.GREEN, 
                                   (player_data['x'], player_data['y'] - 20, 50 * health_ratio, 10))
            
            # UI 정보
            if self.local_player:
                health_text = self.small_font.render(f"체력: {self.local_player.health}", True, self.BLACK)
                self.screen.blit(health_text, (10, 10))
                
                player_text = self.small_font.render(f"플레이어: {self.local_player.name}", True, self.BLACK)
                self.screen.blit(player_text, (10, 35))
            
            # 조작법 안내
            controls = [
                "조작법:",
                "이동: A/D 또는 ←/→",
                "점프: W 또는 ↑",
                "공격: SPACE"
            ]
            
            for i, control in enumerate(controls):
                text = self.small_font.render(control, True, self.BLACK)
                self.screen.blit(text, (self.width - 200, 10 + i * 25))
        
        pygame.display.flip()
    
    def run(self):
        """게임 메인 루프를 실행합니다."""
        # 서버 연결 시도
        if not self.connect_to_server():
            print("서버에 연결할 수 없습니다. 서버를 먼저 실행해주세요.")
        
        while self.running:
            self.handle_input()
            self.update_game()
            self.draw()
            self.clock.tick(60)  # 60 FPS
        
        # 정리
        if self.connected and self.socket:
            self.socket.close()
