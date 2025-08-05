import time
from player import Player

class GameState:
    def __init__(self):
        self.players = {}  # 플레이어 ID -> 플레이어 데이터
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
        self.players[player_id] = player.to_dict()
        
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
        print("게임이 시작되었습니다!")
    
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
                player_data['x'] = min(1150, player_data['x'] + speed)  # 1200 - 50 (플레이어 너비)
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
            attack_x = attacker['x'] + 50  # 플레이어 너비
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
                print(f"플레이어 {player_id}가 {damage} 데미지를 받았습니다! (체력: {player_data['health']})")
                
                # 죽음 처리
                if player_data['health'] <= 0:
                    self.game_over = True
                    self.winner = attacker_id
                    print(f"플레이어 {attacker_id}가 승리했습니다!")
    
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
                # 0.2초 후 공격 상태 해제
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
            print(f"시간 종료! 플레이어 {winner}가 승리했습니다!")
        
        self.last_update = current_time
    
    def get_remaining_time(self):
        """남은 시간을 반환합니다"""
        if not self.game_started or not self.round_start_time:
            return self.round_time
        
        elapsed = time.time() - self.round_start_time
        return max(0, self.round_time - elapsed)
    
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
