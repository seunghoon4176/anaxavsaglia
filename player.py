import pygame
import time
import os

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
        self.attack_cooldown = 0.5  # 초
        self.last_attack_time = 0
        self.attack_range = 80
        self.attack_damage = 20
        
        # 애니메이션
        self.facing_right = True
        self.animation_frame = 0
        self.animation_speed = 0.2
        self.last_animation_update = time.time()
        
        # 스프라이트 이미지 로드
        self.sprites = self.load_sprites()
        self.current_animation = "idle"
    
    def load_sprites(self):
        """캐릭터 스프라이트 이미지를 로드합니다"""
        sprites = {}
        character_dir = self.character
        
        try:
            # 이미지 파일들 로드 (1.png ~ 8.png)
            sprite_list = []
            for i in range(1, 9):
                image_path = os.path.join(character_dir, f"{i}.png")
                if os.path.exists(image_path):
                    image = pygame.image.load(image_path)
                    # 이미지 크기를 플레이어 크기에 맞게 조정
                    scaled_image = pygame.transform.scale(image, (self.width, self.height))
                    sprite_list.append(scaled_image)
            
            if sprite_list:
                # 애니메이션 프레임 할당
                sprites['idle'] = sprite_list[:2]      # 1.png, 2.png - 대기
                sprites['walk'] = sprite_list[2:6]     # 3.png ~ 6.png - 걷기
                sprites['attack'] = sprite_list[6:]    # 7.png, 8.png - 공격
                
            return sprites
            
        except Exception as e:
            print(f"스프라이트 로딩 실패 ({self.character}): {e}")
            return {}
        
    def move_left(self):
        """왼쪽으로 이동"""
        self.velocity_x = -self.speed
        self.facing_right = False
        self.current_animation = "walk"
        
    def move_right(self, screen_width):
        """오른쪽으로 이동"""
        self.velocity_x = self.speed
        self.facing_right = True
        self.current_animation = "walk"
        
    def jump(self):
        """점프"""
        if self.on_ground:
            self.velocity_y = -self.jump_power
            self.on_ground = False
    
    def attack(self):
        """공격"""
        current_time = time.time()
        if current_time - self.last_attack_time >= self.attack_cooldown:
            self.attacking = True
            self.current_animation = "attack"
            self.last_attack_time = current_time
            return True
        return False
    
    def take_damage(self, damage):
        """데미지를 받습니다"""
        self.health = max(0, self.health - damage)
        return self.health <= 0  # 죽었는지 반환
    
    def heal(self, amount):
        """체력을 회복합니다"""
        self.health = min(self.max_health, self.health + amount)
    
    def update(self, screen_height):
        """플레이어 상태를 업데이트합니다"""
        # 중력 적용
        if not self.on_ground:
            self.velocity_y += self.gravity
        
        # 위치 업데이트
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        # 지면 충돌 검사
        ground_y = screen_height - 100 - self.height
        if self.y >= ground_y:
            self.y = ground_y
            self.velocity_y = 0
            self.on_ground = True
        
        # 화면 경계 처리
        if self.x < 0:
            self.x = 0
        elif self.x > 1200 - self.width:  # 화면 너비에서 플레이어 너비를 뺀 값
            self.x = 1200 - self.width
        
        # 속도 감쇠 (마찰)
        self.velocity_x *= 0.8
        
        # 애니메이션 상태 결정
        if abs(self.velocity_x) > 0.1:
            self.current_animation = "walk"
        elif self.attacking:
            self.current_animation = "attack"
        else:
            self.current_animation = "idle"
        
        # 공격 상태 해제
        if self.attacking:
            # 공격 애니메이션 시간 후 해제
            if time.time() - self.last_attack_time > 0.2:
                self.attacking = False
        
        # 애니메이션 프레임 업데이트
        self.update_animation()
    
    def update_animation(self):
        """애니메이션 프레임을 업데이트합니다"""
        current_time = time.time()
        
        if current_time - self.last_animation_update >= self.animation_speed:
            if self.current_animation in self.sprites and len(self.sprites[self.current_animation]) > 0:
                self.animation_frame = (self.animation_frame + 1) % len(self.sprites[self.current_animation])
            self.last_animation_update = current_time
    
    def get_current_sprite(self):
        """현재 애니메이션 프레임의 스프라이트를 반환합니다"""
        if (self.current_animation in self.sprites and 
            len(self.sprites[self.current_animation]) > 0):
            sprite = self.sprites[self.current_animation][self.animation_frame]
            
            # 좌우 방향에 따라 이미지 뒤집기
            if not self.facing_right:
                sprite = pygame.transform.flip(sprite, True, False)
            
            return sprite
        
        return None
    
    def get_attack_rect(self):
        """공격 범위 사각형을 반환합니다"""
        if self.facing_right:
            return pygame.Rect(self.x + self.width, self.y, self.attack_range, self.height)
        else:
            return pygame.Rect(self.x - self.attack_range, self.y, self.attack_range, self.height)
    
    def get_rect(self):
        """플레이어의 충돌 사각형을 반환합니다"""
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    def draw(self, screen):
        """플레이어를 화면에 그립니다"""
        # 스프라이트 그리기
        sprite = self.get_current_sprite()
        if sprite:
            screen.blit(sprite, (self.x, self.y))
        else:
            # 스프라이트가 없으면 기본 사각형으로 그리기
            pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        
        # 체력바
        health_ratio = self.health / self.max_health
        health_bar_width = self.width
        health_bar_height = 8
        
        # 체력바 배경 (빨간색)
        pygame.draw.rect(screen, (255, 0, 0), 
                        (self.x, self.y - 15, health_bar_width, health_bar_height))
        
        # 체력바 (초록색)
        pygame.draw.rect(screen, (0, 255, 0), 
                        (self.x, self.y - 15, health_bar_width * health_ratio, health_bar_height))
        
        # 공격 중일 때 공격 범위 표시
        if self.attacking:
            attack_rect = self.get_attack_rect()
            pygame.draw.rect(screen, (255, 255, 0, 100), attack_rect, 2)
        
        # 방향 표시 (간단한 화살표)
        if self.facing_right:
            pygame.draw.polygon(screen, (255, 255, 255), [
                (self.x + self.width - 10, self.y + 10),
                (self.x + self.width - 5, self.y + 15),
                (self.x + self.width - 10, self.y + 20)
            ])
        else:
            pygame.draw.polygon(screen, (255, 255, 255), [
                (self.x + 10, self.y + 10),
                (self.x + 5, self.y + 15),
                (self.x + 10, self.y + 20)
            ])
    
    def to_dict(self):
        """플레이어 데이터를 딕셔너리로 변환합니다"""
        return {
            'id': getattr(self, 'id', 0),
            'x': self.x,
            'y': self.y,
            'health': self.health,
            'facing_right': self.facing_right,
            'attacking': self.attacking,
            'name': self.name
        }
    
    def from_dict(self, data):
        """딕셔너리에서 플레이어 데이터를 로드합니다"""
        self.x = data.get('x', self.x)
        self.y = data.get('y', self.y)
        self.health = data.get('health', self.health)
        self.facing_right = data.get('facing_right', self.facing_right)
        self.attacking = data.get('attacking', self.attacking)
