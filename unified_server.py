#!/usr/bin/env python3
"""
통합 게임 서버 - 로비와 게임 기능을 하나로 합친 서버
"""

import socket
import threading
import json
import time
import uuid
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

class Room:
    def __init__(self, room_id, name, max_players=2):
        self.room_id = room_id
        self.name = name
        self.max_players = max_players
        self.players = {}  # player_id -> player_info
        self.status = "waiting"  # waiting, playing, finished
        self.created_time = time.time()
        
        # 게임 상태
        self.game_players = {}  # 실제 게임 플레이어 객체들
        self.game_started = False
        self.game_over = False
        self.winner = None
        self.round_time = 180  # 3분
        self.round_start_time = None
    
    def add_player(self, player_id, player_info):
        """플레이어를 방에 추가합니다"""
        if len(self.players) >= self.max_players:
            return False
        
        self.players[player_id] = player_info
        
        # 방이 가득 차면 게임 시작
        if len(self.players) >= self.max_players:
            self.start_game()
        
        return True
    
    def remove_player(self, player_id):
        """플레이어를 방에서 제거합니다"""
        if player_id in self.players:
            del self.players[player_id]
        
        if player_id in self.game_players:
            del self.game_players[player_id]
        
        # 게임 중이었다면 게임 종료
        if self.status == "playing":
            self.game_over = True
    
    def start_game(self):
        """게임을 시작합니다"""
        self.status = "playing"
        self.game_started = True
        self.round_start_time = time.time()
        
        # 게임 플레이어 객체 생성
        colors = [(255, 0, 0), (0, 0, 255)]  # 빨강, 파랑
        positions = [(200, 600), (1000, 600)]
        
        for i, (player_id, player_info) in enumerate(self.players.items()):
            x, y = positions[i]
            color = colors[i]
            
            player = Player(x, y, color, player_info['name'], player_info['character'])
            player.id = player_id
            self.game_players[player_id] = player
        
        print(f"[INFO] 방 {self.room_id}에서 게임이 시작되었습니다")
        return True
    
    def update_player(self, player_id, action, data=None):
        """플레이어 액션을 처리합니다"""
        if player_id not in self.game_players:
            return
        
        player = self.game_players[player_id]
        
        if action == 'move':
            direction = data.get('direction')
            
            if direction == 'left':
                player.x = max(0, player.x - player.speed)
                player.facing_right = False
            elif direction == 'right':
                player.x = min(1150, player.x + player.speed)
                player.facing_right = True
        
        elif action == 'attack':
            player.attacking = True
            self.handle_attack(player_id)
    
    def handle_attack(self, attacker_id):
        """공격 처리"""
        if attacker_id not in self.game_players:
            return
        
        attacker = self.game_players[attacker_id]
        
        # 공격 범위 계산
        if attacker.facing_right:
            attack_x = attacker.x + 50
            attack_rect = (attack_x, attacker.y, attacker.attack_range, 80)
        else:
            attack_x = attacker.x - attacker.attack_range
            attack_rect = (attack_x, attacker.y, attacker.attack_range, 80)
        
        # 다른 플레이어들과 충돌 검사
        for player_id, player in self.game_players.items():
            if player_id == attacker_id:
                continue
            
            player_rect = (player.x, player.y, 50, 80)
            
            # 사각형 충돌 검사
            if self.rect_collision(attack_rect, player_rect):
                # 데미지 적용
                player.health = max(0, player.health - attacker.attack_damage)
                print(f"[INFO] 플레이어 {player_id}가 {attacker.attack_damage} 데미지를 받았습니다! (체력: {player.health})")
                
                # 죽음 처리
                if player.health <= 0:
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
    
    def update_game(self):
        """게임 상태를 업데이트합니다"""
        if not self.game_started:
            return
        
        current_time = time.time()
        
        # 공격 상태 해제
        for player in self.game_players.values():
            if player.attacking:
                player.attacking = False
        
        # 라운드 시간 체크
        if (self.round_start_time and 
            current_time - self.round_start_time >= self.round_time):
            
            # 시간 종료 - 체력이 높은 플레이어 승리
            max_health = -1
            winner = None
            
            for player_id, player in self.game_players.items():
                if player.health > max_health:
                    max_health = player.health
                    winner = player_id
            
            self.game_over = True
            self.winner = winner
            print(f"[INFO] 시간 종료! 플레이어 {winner}가 승리했습니다!")
    
    def get_remaining_time(self):
        """남은 시간을 반환합니다"""
        if not self.game_started or not self.round_start_time:
            return self.round_time
        
        elapsed = time.time() - self.round_start_time
        return max(0, self.round_time - elapsed)
    
    def get_info(self):
        """방 정보를 반환합니다"""
        return {
            'room_id': self.room_id,
            'name': self.name,
            'players': len(self.players),
            'max_players': self.max_players,
            'status': self.status,
            'player_list': list(self.players.values())
        }
    
    def get_game_state(self):
        """게임 상태를 반환합니다"""
        players_data = {}
        for player_id, player in self.game_players.items():
            players_data[player_id] = {
                'id': player_id,
                'x': player.x,
                'y': player.y,
                'health': player.health,
                'facing_right': player.facing_right,
                'attacking': player.attacking,
                'name': player.name
            }
        
        return {
            'players': players_data,
            'game_started': self.game_started,
            'game_over': self.game_over,
            'winner': self.winner,
            'remaining_time': self.get_remaining_time()
        }

class UnifiedGameServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.clients = {}  # client_socket -> client_info
        self.rooms = {}    # room_id -> Room
        self.running = True
        
        # 신호 핸들러 설정
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """시스템 신호 처리"""
        print(f"\n[INFO] 신호 {signum} 수신. 서버를 종료합니다...")
        self.shutdown()
        sys.exit(0)
        
    def start(self):
        """통합 서버를 시작합니다"""
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(20)
            print(f"[INFO] ======================================")
            print(f"[INFO] 2D 멀티플레이어 격투 게임 통합 서버")
            print(f"[INFO] 서버 주소: {self.host}:{self.port}")
            print(f"[INFO] 로비 + 게임 기능 통합")
            print(f"[INFO] ======================================")
            
            # 게임 상태 업데이트 스레드 시작
            update_thread = threading.Thread(target=self.game_update_loop, daemon=True)
            update_thread.start()
            
            # 방 정리 스레드 시작
            cleanup_thread = threading.Thread(target=self.room_cleanup, daemon=True)
            cleanup_thread.start()
            
            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    print(f"[INFO] 새 클라이언트 연결: {address}")
                    
                    # 클라이언트 처리 스레드 시작
                    client_thread = threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket,), 
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"[ERROR] 클라이언트 연결 수락 오류: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERROR] 서버 오류: {e}")
        finally:
            self.cleanup()
    
    def game_update_loop(self):
        """게임 상태 업데이트 루프"""
        last_broadcast = time.time()
        broadcast_interval = 1.0 / 60  # 60 FPS
        
        while self.running:
            current_time = time.time()
            
            # 모든 방의 게임 상태 업데이트
            for room in self.rooms.values():
                if room.status == "playing":
                    room.update_game()
                    
                    # 게임 상태를 해당 방의 클라이언트들에게 전송
                    if current_time - last_broadcast >= broadcast_interval:
                        game_state_message = {
                            'type': 'game_state',
                            'data': room.get_game_state()
                        }
                        self.broadcast_to_room(room.room_id, game_state_message)
                        
                        # 게임 종료 체크
                        if room.game_over:
                            game_over_message = {
                                'type': 'game_over',
                                'winner': room.winner
                            }
                            self.broadcast_to_room(room.room_id, game_over_message)
                            room.status = "finished"
            
            if current_time - last_broadcast >= broadcast_interval:
                last_broadcast = current_time
            
            time.sleep(0.016)  # ~60 FPS
    
    def room_cleanup(self):
        """빈 방 정리"""
        while self.running:
            try:
                current_time = time.time()
                rooms_to_remove = []
                
                for room_id, room in self.rooms.items():
                    # 빈 방이고 30분 이상 지났거나 게임이 끝났으면 삭제
                    if ((len(room.players) == 0 and 
                         current_time - room.created_time > 1800) or
                        room.status == "finished"):
                        rooms_to_remove.append(room_id)
                
                for room_id in rooms_to_remove:
                    if room_id in self.rooms:
                        del self.rooms[room_id]
                        print(f"[INFO] 방 {room_id} 정리됨")
                
                # 상태 출력
                if len(self.clients) > 0 or len(self.rooms) > 0:
                    print(f"[STATUS] 연결된 클라이언트: {len(self.clients)}, 활성 방: {len(self.rooms)}")
                
                time.sleep(300)  # 5분마다 실행
                
            except Exception as e:
                print(f"[ERROR] 방 정리 오류: {e}")
                time.sleep(60)
    
    def handle_client(self, client_socket):
        """클라이언트 메시지를 처리합니다"""
        client_id = str(uuid.uuid4())[:8]
        self.clients[client_socket] = {
            'id': client_id,
            'name': None,
            'character': None,
            'room_id': None,
            'player_id': None,
            'connected_time': time.time()
        }
        
        try:
            while self.running:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                try:
                    message = json.loads(data)
                    response = self.process_message(client_socket, message)
                    
                    if response:
                        client_socket.send(json.dumps(response).encode('utf-8'))
                        
                except json.JSONDecodeError:
                    print(f"[WARNING] 잘못된 JSON 메시지 수신: {client_id}")
                except Exception as e:
                    print(f"[ERROR] 메시지 처리 오류 ({client_id}): {e}")
                    
        except ConnectionResetError:
            print(f"[INFO] 클라이언트 {client_id} 연결이 끊어졌습니다")
        except Exception as e:
            print(f"[ERROR] 클라이언트 처리 오류 ({client_id}): {e}")
        finally:
            self.disconnect_client(client_socket)
    
    def process_message(self, client_socket, message):
        """클라이언트 메시지를 처리하고 응답을 반환합니다"""
        msg_type = message.get('type')
        client_info = self.clients.get(client_socket)
        
        # 로비 메시지들
        if msg_type == 'set_player_info':
            client_info['name'] = message.get('name')
            client_info['character'] = message.get('character')
            print(f"[INFO] 플레이어 정보 설정: {client_info['name']} ({client_info['character']})")
            return {'type': 'success', 'message': '플레이어 정보가 설정되었습니다'}
        
        elif msg_type == 'create_room':
            return self.create_room(client_socket, message.get('room_name', '새 방'))
        
        elif msg_type == 'join_room':
            room_id = message.get('room_id')
            return self.join_room(client_socket, room_id)
        
        elif msg_type == 'get_room_list':
            return self.get_room_list()
        
        # 게임 메시지들
        elif msg_type == 'player_input':
            player_id = message['player_id']
            action = message['action']
            data = message.get('data')
            
            room_id = client_info['room_id']
            if room_id and room_id in self.rooms:
                self.rooms[room_id].update_player(player_id, action, data)
        
        else:
            return {'type': 'error', 'message': '알 수 없는 메시지 타입입니다'}
    
    def create_room(self, client_socket, room_name):
        """새 방을 생성합니다"""
        client_info = self.clients.get(client_socket)
        
        if not client_info['name']:
            return {'type': 'error', 'message': '플레이어 정보를 먼저 설정해주세요'}
        
        if client_info['room_id']:
            return {'type': 'error', 'message': '이미 방에 참가하고 있습니다'}
        
        # 새 방 생성
        room_id = str(uuid.uuid4())[:8]
        room = Room(room_id, room_name)
        self.rooms[room_id] = room
        
        # 방장으로 참가
        if room.add_player(client_info['id'], {
            'name': client_info['name'],
            'character': client_info['character']
        }):
            client_info['room_id'] = room_id
            client_info['player_id'] = 1
            print(f"[INFO] 방 생성: {room_name} (ID: {room_id}) by {client_info['name']}")
            
            # 게임이 시작되었는지 확인
            if room.status == "playing":
                return {
                    'type': 'game_ready',
                    'room_id': room_id,
                    'room_info': room.get_info(),
                    'player_id': 1
                }
            else:
                return {
                    'type': 'room_created',
                    'room_id': room_id,
                    'room_info': room.get_info(),
                    'player_id': 1
                }
        else:
            del self.rooms[room_id]
            return {'type': 'error', 'message': '방 생성에 실패했습니다'}
    
    def join_room(self, client_socket, room_id):
        """방에 참가합니다"""
        client_info = self.clients.get(client_socket)
        
        if not client_info['name']:
            return {'type': 'error', 'message': '플레이어 정보를 먼저 설정해주세요'}
        
        if client_info['room_id']:
            return {'type': 'error', 'message': '이미 방에 참가하고 있습니다'}
        
        if room_id not in self.rooms:
            return {'type': 'error', 'message': '존재하지 않는 방입니다'}
        
        room = self.rooms[room_id]
        
        if room.status != "waiting":
            return {'type': 'error', 'message': '참가할 수 없는 방입니다'}
        
        if room.add_player(client_info['id'], {
            'name': client_info['name'],
            'character': client_info['character']
        }):
            client_info['room_id'] = room_id
            client_info['player_id'] = 2
            print(f"[INFO] 방 참가: {client_info['name']} -> {room.name}")
            
            # 게임이 시작되었는지 확인
            if room.status == "playing":
                return {
                    'type': 'game_ready',
                    'room_id': room_id,
                    'room_info': room.get_info(),
                    'player_id': 2
                }
            else:
                return {
                    'type': 'room_joined',
                    'room_info': room.get_info(),
                    'player_id': 2
                }
        else:
            return {'type': 'error', 'message': '방이 가득 찼습니다'}
    
    def get_room_list(self):
        """방 목록을 반환합니다"""
        room_list = []
        for room in self.rooms.values():
            if room.status == "waiting":
                room_list.append(room.get_info())
        
        return {
            'type': 'room_list',
            'rooms': room_list
        }
    
    def broadcast_to_room(self, room_id, message):
        """특정 방의 클라이언트들에게 메시지를 브로드캐스트합니다"""
        message_str = json.dumps(message)
        disconnected_clients = []
        
        for client_socket, client_info in self.clients.items():
            if client_info['room_id'] == room_id:
                try:
                    client_socket.send(message_str.encode())
                except:
                    disconnected_clients.append(client_socket)
        
        # 연결이 끊어진 클라이언트 정리
        for client_socket in disconnected_clients:
            self.disconnect_client(client_socket)
    
    def disconnect_client(self, client_socket):
        """클라이언트 연결을 해제합니다"""
        if client_socket in self.clients:
            client_info = self.clients[client_socket]
            
            # 방에서 나가기
            if client_info['room_id']:
                room_id = client_info['room_id']
                if room_id in self.rooms:
                    room = self.rooms[room_id]
                    room.remove_player(client_info['id'])
                    
                    # 방이 비었으면 삭제
                    if len(room.players) == 0:
                        del self.rooms[room_id]
                        print(f"[INFO] 빈 방 삭제: {room_id}")
            
            print(f"[INFO] 클라이언트 {client_info['id']} 연결 해제")
            del self.clients[client_socket]
        
        try:
            client_socket.close()
        except:
            pass
    
    def shutdown(self):
        """서버를 종료합니다"""
        print("[INFO] 서버를 종료합니다...")
        self.running = False
        
        # 모든 클라이언트 연결 해제
        for client_socket in list(self.clients.keys()):
            self.disconnect_client(client_socket)
        
        # 서버 소켓 닫기
        try:
            self.socket.close()
        except:
            pass
        
        print("[INFO] 서버가 종료되었습니다")
    
    def cleanup(self):
        """정리 작업을 수행합니다"""
        self.shutdown()

def main():
    """통합 서버 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='2D 멀티플레이어 격투 게임 통합 서버')
    parser.add_argument('--host', default='0.0.0.0', help='서버 바인드 주소 (기본값: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=12345, help='서버 포트 (기본값: 12345)')
    
    args = parser.parse_args()
    
    server = UnifiedGameServer(args.host, args.port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[INFO] Ctrl+C 감지. 서버를 종료합니다...")
    finally:
        server.shutdown()

if __name__ == "__main__":
    main()
