#!/usr/bin/env python3
"""
독립 배포용 게임 서버
"""

import socket
import threading
import json
import time
import signal
import sys

class Player:
    def __init__(self, x, y, color, name, character="anaxa"):
        self.x = x
        self.y = y
        self.width = 50
        self.height = 80
        self.color = color
        self.name = name
        self.character = character
        
        # 게임 속성
        self.health = 100
        self.max_health = 100
        self.speed = 5
        self.jump_power = 15
        
        # 물리
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
        self.gravity = 0.8
        
        # 공격
        self.attacking = False
        self.attack_cooldown = 0.5
        self.last_attack_time = 0
        self.attack_range = 80
        self.attack_damage = 20
        
        # 애니메이션
        self.facing_right = True

class GameState:
    def __init__(self):
        self.players = {}
        self.game_started = False
        self.game_over = False
        self.winner = None
        self.last_update = time.time()
        
        # 게임 설정
        self.max_players = 2
        self.round_time = 180  # 3분
        self.round_start_time = None
        
    def add_player(self, player_id, x, y, color, name):
        """새 플레이어를 추가합니다"""
        player = Player(x, y, color, name)
        player.id = player_id
        self.players[player_id] = self.player_to_dict(player)
        
        # 두 명이 모이면 게임 시작
        if len(self.players) >= self.max_players and not self.game_started:
            self.start_game()
        
        return player
    
    def remove_player(self, player_id):
        """플레이어를 제거합니다"""
        if player_id in self.players:
            del self.players[player_id]
        
        # 플레이어가 나가면 게임 종료
        if len(self.players) < 2:
            self.game_over = True
    
    def start_game(self):
        """게임을 시작합니다"""
        self.game_started = True
        self.round_start_time = time.time()
        print("[INFO] 게임이 시작되었습니다!")
    
    def update_player(self, player_id, action, data=None):
        """플레이어 액션을 처리합니다"""
        if player_id not in self.players:
            return
        
        player_data = self.players[player_id]
        
        if action == 'move':
            direction = data.get('direction')
            speed = 5
            
            if direction == 'left':
                player_data['x'] = max(0, player_data['x'] - speed)
                player_data['facing_right'] = False
            elif direction == 'right':
                player_data['x'] = min(1150, player_data['x'] + speed)
                player_data['facing_right'] = True
        
        elif action == 'jump':
            # 점프는 클라이언트에서 처리하고 서버는 동기화만
            pass
        
        elif action == 'attack':
            player_data['attacking'] = True
            self.handle_attack(player_id)
    
    def handle_attack(self, attacker_id):
        """공격 처리"""
        if attacker_id not in self.players:
            return
        
        attacker = self.players[attacker_id]
        attack_range = 80
        damage = 20
        
        # 공격 범위 계산
        if attacker['facing_right']:
            attack_x = attacker['x'] + 50
            attack_rect = (attack_x, attacker['y'], attack_range, 80)
        else:
            attack_x = attacker['x'] - attack_range
            attack_rect = (attack_x, attacker['y'], attack_range, 80)
        
        # 다른 플레이어들과 충돌 검사
        for player_id, player_data in self.players.items():
            if player_id == attacker_id:
                continue
            
            player_rect = (player_data['x'], player_data['y'], 50, 80)
            
            # 사각형 충돌 검사
            if self.rect_collision(attack_rect, player_rect):
                # 데미지 적용
                player_data['health'] = max(0, player_data['health'] - damage)
                print(f"[INFO] 플레이어 {player_id}가 {damage} 데미지를 받았습니다! (체력: {player_data['health']})")
                
                # 죽음 처리
                if player_data['health'] <= 0:
                    self.game_over = True
                    self.winner = attacker_id
                    print(f"[INFO] 플레이어 {attacker_id}가 승리했습니다!")
    
    def rect_collision(self, rect1, rect2):
        """두 사각형의 충돌을 검사합니다"""
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2
        
        return (x1 < x2 + w2 and
                x1 + w1 > x2 and
                y1 < y2 + h2 and
                y1 + h1 > y2)
    
    def update(self):
        """게임 상태를 업데이트합니다"""
        current_time = time.time()
        
        # 공격 상태 해제
        for player_data in self.players.values():
            if player_data.get('attacking', False):
                player_data['attacking'] = False
        
        # 라운드 시간 체크
        if (self.game_started and 
            self.round_start_time and 
            current_time - self.round_start_time >= self.round_time):
            
            # 시간 종료 - 체력이 높은 플레이어 승리
            max_health = -1
            winner = None
            
            for player_id, player_data in self.players.items():
                if player_data['health'] > max_health:
                    max_health = player_data['health']
                    winner = player_id
            
            self.game_over = True
            self.winner = winner
            print(f"[INFO] 시간 종료! 플레이어 {winner}가 승리했습니다!")
        
        self.last_update = current_time
    
    def get_remaining_time(self):
        """남은 시간을 반환합니다"""
        if not self.game_started or not self.round_start_time:
            return self.round_time
        
        elapsed = time.time() - self.round_start_time
        return max(0, self.round_time - elapsed)
    
    def player_to_dict(self, player):
        """플레이어를 딕셔너리로 변환"""
        return {
            'id': getattr(player, 'id', 0),
            'x': player.x,
            'y': player.y,
            'health': player.health,
            'facing_right': player.facing_right,
            'attacking': player.attacking,
            'name': player.name
        }
    
    def to_dict(self):
        """게임 상태를 딕셔너리로 변환합니다"""
        return {
            'players': self.players,
            'game_started': self.game_started,
            'game_over': self.game_over,
            'winner': self.winner,
            'remaining_time': self.get_remaining_time()
        }
    
    def update_from_dict(self, data):
        """딕셔너리에서 게임 상태를 업데이트합니다"""
        self.players = data.get('players', {})
        self.game_started = data.get('game_started', False)
        self.game_over = data.get('game_over', False)
        self.winner = data.get('winner', None)

class StandaloneGameServer:
    def __init__(self, host='0.0.0.0', port=13000):
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
        
        # 신호 핸들러 설정
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """시스템 신호 처리"""
        print(f"\n[INFO] 신호 {signum} 수신. 게임 서버를 종료합니다...")
        self.shutdown()
        sys.exit(0)
        
    def start(self):
        """서버를 시작합니다"""
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(2)  # 최대 2명의 플레이어
            print(f"[INFO] 게임 서버가 {self.host}:{self.port}에서 시작되었습니다...")
            print(f"[INFO] 플레이어 연결을 기다리는 중...")
            
            # 게임 상태 업데이트 스레드 시작
            update_thread = threading.Thread(target=self.game_loop, daemon=True)
            update_thread.start()
            
            while self.running and len(self.clients) < 2:
                try:
                    client_socket, address = self.socket.accept()
                    print(f"[INFO] 새 클라이언트 연결: {address}")
                    
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
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True)
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"[ERROR] 클라이언트 연결 수락 오류: {e}")
                    break
            
            if len(self.clients) >= 2:
                print("[INFO] 모든 플레이어가 연결되었습니다. 게임 시작!")
            
            # 메인 루프
            while self.running:
                time.sleep(0.1)
                
        except Exception as e:
            print(f"[ERROR] 게임 서버 오류: {e}")
        finally:
            self.cleanup()
    
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
                    print(f"[WARNING] 잘못된 JSON 메시지 수신")
                
        except ConnectionResetError:
            print(f"[INFO] 플레이어 {player_id} 연결이 끊어졌습니다")
        except Exception as e:
            print(f"[ERROR] 클라이언트 처리 오류: {e}")
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
            print(f"[INFO] 플레이어 {player_id}가 게임을 떠났습니다")
            
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
                print(f"[INFO] 게임 종료! 승자: 플레이어 {self.game_state.winner}")
                
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
        
        print("[INFO] 게임 서버가 종료되었습니다.")
    
    def cleanup(self):
        """정리 작업을 수행합니다"""
        self.shutdown()

def main():
    """서버 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='2D 멀티플레이어 격투 게임 서버')
    parser.add_argument('--host', default='0.0.0.0', help='서버 바인드 주소 (기본값: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=13000, help='서버 포트 (기본값: 13000)')
    
    args = parser.parse_args()
    
    print("=== 2D 멀티플레이어 격투 게임 서버 ===")
    print("Ctrl+C를 눌러서 서버를 종료할 수 있습니다.")
    print()
    
    server = StandaloneGameServer(args.host, args.port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[INFO] Ctrl+C 감지. 서버를 종료합니다...")
    finally:
        server.shutdown()

if __name__ == "__main__":
    main()
