import socket
import threading
import json
import time
from game_state import GameState

class GameServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.clients = {}  # 클라이언트 소켓 -> 플레이어 ID
        self.game_state = GameState()
        self.running = True
        self.next_player_id = 1
        
        # 색상 정의
        self.PLAYER_COLORS = [(255, 0, 0), (0, 0, 255)]  # 빨강, 파랑
        
    def start(self):
        """서버를 시작합니다"""
        self.socket.bind((self.host, self.port))
        self.socket.listen(2)  # 최대 2명의 플레이어
        print(f"게임 서버가 {self.host}:{self.port}에서 시작되었습니다...")
        print("플레이어 연결을 기다리는 중...")
        
        # 게임 상태 업데이트 스레드 시작
        update_thread = threading.Thread(target=self.game_loop)
        update_thread.daemon = True
        update_thread.start()
        
        try:
            while self.running and len(self.clients) < 2:
                client_socket, address = self.socket.accept()
                print(f"새 클라이언트 연결: {address}")
                
                # 플레이어 ID 할당
                player_id = self.next_player_id
                self.next_player_id += 1
                
                self.clients[client_socket] = player_id
                
                # 플레이어를 게임에 추가
                if player_id == 1:
                    self.game_state.add_player(player_id, 200, 600, self.PLAYER_COLORS[0], "Player 1")
                else:
                    self.game_state.add_player(player_id, 1000, 600, self.PLAYER_COLORS[1], "Player 2")
                
                # 클라이언트에게 플레이어 ID 전송
                welcome_message = {
                    'type': 'welcome',
                    'player_id': player_id
                }
                client_socket.send(json.dumps(welcome_message).encode())
                
                # 클라이언트 처리 스레드 시작
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.daemon = True
                client_thread.start()
            
            print("모든 플레이어가 연결되었습니다. 게임 시작!")
            
            # 메인 루프
            while self.running:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("서버를 종료합니다...")
        finally:
            self.shutdown()
    
    def handle_client(self, client_socket):
        """클라이언트의 메시지를 처리합니다"""
        player_id = self.clients.get(client_socket)
        
        try:
            while self.running:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                
                try:
                    message = json.loads(data)
                    self.process_client_message(message)
                except json.JSONDecodeError:
                    print("잘못된 JSON 메시지 수신")
                
        except ConnectionResetError:
            print(f"플레이어 {player_id} 연결이 끊어졌습니다")
        except Exception as e:
            print(f"클라이언트 처리 오류: {e}")
        finally:
            self.disconnect_client(client_socket)
    
    def process_client_message(self, message):
        """클라이언트 메시지를 처리합니다"""
        if message['type'] == 'player_input':
            player_id = message['player_id']
            action = message['action']
            data = message.get('data')
            
            self.game_state.update_player(player_id, action, data)
    
    def disconnect_client(self, client_socket):
        """클라이언트 연결을 해제합니다"""
        if client_socket in self.clients:
            player_id = self.clients[client_socket]
            print(f"플레이어 {player_id}가 게임을 떠났습니다")
            
            # 게임 상태에서 플레이어 제거
            self.game_state.remove_player(player_id)
            
            # 클라이언트 목록에서 제거
            del self.clients[client_socket]
            
            # 다른 클라이언트들에게 알림
            disconnect_message = {
                'type': 'player_disconnect',
                'player_id': player_id
            }
            self.broadcast_message(disconnect_message, exclude_socket=client_socket)
        
        try:
            client_socket.close()
        except:
            pass
    
    def broadcast_message(self, message, exclude_socket=None):
        """모든 클라이언트에게 메시지를 브로드캐스트합니다"""
        message_str = json.dumps(message)
        disconnected_clients = []
        
        for client_socket in list(self.clients.keys()):
            if client_socket == exclude_socket:
                continue
            
            try:
                client_socket.send(message_str.encode())
            except:
                disconnected_clients.append(client_socket)
        
        # 연결이 끊어진 클라이언트 정리
        for client_socket in disconnected_clients:
            self.disconnect_client(client_socket)
    
    def game_loop(self):
        """게임 상태 업데이트 루프"""
        last_broadcast = time.time()
        broadcast_interval = 1.0 / 60  # 60 FPS
        
        while self.running:
            current_time = time.time()
            
            # 게임 상태 업데이트
            self.game_state.update()
            
            # 주기적으로 게임 상태를 모든 클라이언트에게 전송
            if current_time - last_broadcast >= broadcast_interval:
                game_state_message = {
                    'type': 'game_state',
                    'data': self.game_state.to_dict()
                }
                self.broadcast_message(game_state_message)
                last_broadcast = current_time
            
            # 게임 종료 체크
            if self.game_state.game_over:
                game_over_message = {
                    'type': 'game_over',
                    'winner': self.game_state.winner
                }
                self.broadcast_message(game_over_message)
                print(f"게임 종료! 승자: 플레이어 {self.game_state.winner}")
                
                # 5초 후 서버 종료
                time.sleep(5)
                self.running = False
            
            time.sleep(0.016)  # ~60 FPS
    
    def shutdown(self):
        """서버를 종료합니다"""
        self.running = False
        
        # 모든 클라이언트 연결 해제
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.close()
            except:
                pass
        
        self.clients.clear()
        
        # 서버 소켓 닫기
        try:
            self.socket.close()
        except:
            pass
        
        print("서버가 종료되었습니다.")

def main():
    """서버 메인 함수"""
    print("=== 2D 멀티플레이어 격투 게임 서버 ===")
    print("Ctrl+C를 눌러서 서버를 종료할 수 있습니다.")
    print()
    
    server = GameServer()
    server.start()

if __name__ == "__main__":
    main()
