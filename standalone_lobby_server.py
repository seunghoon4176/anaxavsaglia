#!/usr/bin/env python3
"""
독립 배포용 로비 서버
배포 시 이 파일만 서버에서 실행하면 됩니다.
"""

import socket
import threading
import json
import time
import uuid
import signal
import sys
import os

class Room:
    def __init__(self, room_id, name, max_players=2):
        self.room_id = room_id
        self.name = name
        self.max_players = max_players
        self.players = {}  # player_id -> player_info
        self.game_server = None
        self.game_port = None
        self.status = "waiting"  # waiting, playing, finished
        self.created_time = time.time()
    
    def add_player(self, player_id, player_info):
        """플레이어를 방에 추가합니다"""
        if len(self.players) >= self.max_players:
            return False
        
        self.players[player_id] = player_info
        
        # 방이 가득 차면 게임 서버 시작
        if len(self.players) >= self.max_players:
            self.start_game()
        
        return True
    
    def remove_player(self, player_id):
        """플레이어를 방에서 제거합니다"""
        if player_id in self.players:
            del self.players[player_id]
        
        # 게임 중이었다면 게임 서버 종료
        if self.game_server and self.status == "playing":
            self.stop_game()
    
    def start_game(self):
        """게임 서버를 시작합니다"""
        try:
            # 사용 가능한 포트 찾기
            self.game_port = self.find_available_port(13000, 14000)
            
            # 게임 서버 시작
            from standalone_game_server import StandaloneGameServer
            self.game_server = StandaloneGameServer('0.0.0.0', self.game_port)
            self.game_thread = threading.Thread(target=self.game_server.start, daemon=True)
            self.game_thread.start()
            
            # 게임 서버가 시작될 때까지 잠시 대기
            time.sleep(2)
            
            self.status = "playing"
            print(f"[INFO] 방 {self.room_id}에서 게임이 시작되었습니다 (포트: {self.game_port})")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 게임 서버 시작 실패: {e}")
            return False
    
    def stop_game(self):
        """게임 서버를 중지합니다"""
        if self.game_server:
            self.game_server.shutdown()
            self.game_server = None
        
        self.status = "finished"
        print(f"[INFO] 방 {self.room_id}의 게임이 종료되었습니다")
    
    def find_available_port(self, start_port, end_port):
        """사용 가능한 포트를 찾습니다"""
        for port in range(start_port, end_port):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.bind(('0.0.0.0', port))
                test_socket.close()
                return port
            except OSError:
                continue
        raise Exception("사용 가능한 포트를 찾을 수 없습니다")
    
    def get_info(self):
        """방 정보를 반환합니다"""
        return {
            'room_id': self.room_id,
            'name': self.name,
            'players': len(self.players),
            'max_players': self.max_players,
            'status': self.status,
            'game_port': self.game_port,
            'player_list': list(self.players.values())
        }

class StandaloneLobbyServer:
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
        """로비 서버를 시작합니다"""
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(20)
            print(f"[INFO] ======================================")
            print(f"[INFO] 2D 멀티플레이어 격투 게임 로비 서버")
            print(f"[INFO] 서버 주소: {self.host}:{self.port}")
            print(f"[INFO] 서버가 시작되었습니다...")
            print(f"[INFO] ======================================")
            
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
            print(f"[ERROR] 로비 서버 오류: {e}")
        finally:
            self.cleanup()
    
    def room_cleanup(self):
        """빈 방 정리 및 상태 모니터링"""
        while self.running:
            try:
                # 5분마다 방 정리
                current_time = time.time()
                rooms_to_remove = []
                
                for room_id, room in self.rooms.items():
                    # 빈 방이고 30분 이상 지났으면 삭제
                    if (len(room.players) == 0 and 
                        current_time - room.created_time > 1800):  # 30분
                        rooms_to_remove.append(room_id)
                
                for room_id in rooms_to_remove:
                    if room_id in self.rooms:
                        self.rooms[room_id].stop_game()
                        del self.rooms[room_id]
                        print(f"[INFO] 빈 방 {room_id} 정리됨")
                
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
        
        if msg_type == 'set_player_info':
            # 플레이어 정보 설정
            client_info['name'] = message.get('name')
            client_info['character'] = message.get('character')
            print(f"[INFO] 플레이어 정보 설정: {client_info['name']} ({client_info['character']})")
            return {'type': 'success', 'message': '플레이어 정보가 설정되었습니다'}
        
        elif msg_type == 'create_room':
            # 방 생성
            return self.create_room(client_socket, message.get('room_name', '새 방'))
        
        elif msg_type == 'join_room':
            # 방 참가
            room_id = message.get('room_id')
            return self.join_room(client_socket, room_id)
        
        elif msg_type == 'leave_room':
            # 방 나가기
            return self.leave_room(client_socket)
        
        elif msg_type == 'get_room_list':
            # 방 목록 요청
            return self.get_room_list()
        
        elif msg_type == 'get_room_info':
            # 방 정보 요청
            room_id = message.get('room_id')
            return self.get_room_info(room_id)
        
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
            print(f"[INFO] 방 생성: {room_name} (ID: {room_id}) by {client_info['name']}")
            return {
                'type': 'room_created',
                'room_id': room_id,
                'room_info': room.get_info()
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
            print(f"[INFO] 방 참가: {client_info['name']} -> {room.name}")
            
            # 게임이 시작되었는지 확인
            if room.status == "playing":
                return {
                    'type': 'game_ready',
                    'room_info': room.get_info(),
                    'game_server': {
                        'host': self.host if self.host != '0.0.0.0' else 'localhost',
                        'port': room.game_port
                    }
                }
            else:
                return {
                    'type': 'room_joined',
                    'room_info': room.get_info()
                }
        else:
            return {'type': 'error', 'message': '방이 가득 찼습니다'}
    
    def leave_room(self, client_socket):
        """방에서 나갑니다"""
        client_info = self.clients.get(client_socket)
        
        if not client_info['room_id']:
            return {'type': 'error', 'message': '참가 중인 방이 없습니다'}
        
        room_id = client_info['room_id']
        if room_id in self.rooms:
            room = self.rooms[room_id]
            room.remove_player(client_info['id'])
            
            # 방이 비었으면 삭제
            if len(room.players) == 0:
                room.stop_game()
                del self.rooms[room_id]
                print(f"[INFO] 빈 방 삭제: {room_id}")
        
        client_info['room_id'] = None
        return {'type': 'success', 'message': '방에서 나갔습니다'}
    
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
    
    def get_room_info(self, room_id):
        """방 정보를 반환합니다"""
        if room_id not in self.rooms:
            return {'type': 'error', 'message': '존재하지 않는 방입니다'}
        
        room = self.rooms[room_id]
        return {
            'type': 'room_info',
            'room_info': room.get_info()
        }
    
    def disconnect_client(self, client_socket):
        """클라이언트 연결을 해제합니다"""
        if client_socket in self.clients:
            client_info = self.clients[client_socket]
            
            # 방에서 나가기
            if client_info['room_id']:
                self.leave_room(client_socket)
            
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
        
        # 모든 방의 게임 서버 종료
        for room in self.rooms.values():
            room.stop_game()
        
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
    """로비 서버 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='2D 멀티플레이어 격투 게임 로비 서버')
    parser.add_argument('--host', default='0.0.0.0', help='서버 바인드 주소 (기본값: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=12345, help='서버 포트 (기본값: 12345)')
    
    args = parser.parse_args()
    
    server = StandaloneLobbyServer(args.host, args.port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[INFO] Ctrl+C 감지. 서버를 종료합니다...")
    finally:
        server.shutdown()

if __name__ == "__main__":
    main()
