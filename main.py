import pygame
import os

# 게임 설정
WIDTH, HEIGHT = 1280, 720
FPS = 60  # 60 frames per second
WHITE = (255, 255, 255)

# 캐릭터 설정
PLAYER_SIZE = (80, 80)
GRAVITY = 1
JUMP_POWER = 18
MOVE_SPEED = 7

class Fighter:
    def __init__(self, x, y, sprite_folder):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.on_ground = True
        self.sprites, self.masks = self.load_sprites_and_masks(sprite_folder)
        self.current_frame = 0
        self.rect = self.sprites[0].get_rect(topleft=(self.x, self.y))
        self.facing_right = True
        self.attacking = False
        self.attack_cooldown = 0
        self.defending = False
        # self.counter = False  # 카운터 입력 제거
        self.dashing = False
        self.jumping = False
        self.idle_anim_timer = 0
        self.idle_anim_index = 0
        self.health = 100
        self.invincible = False
        self.invincible_timer = 0

    def take_damage(self, amount):
        if self.invincible or self.health <= 0:
            return
        self.health = max(0, self.health - amount)
        self.invincible = True
        self.invincible_timer = 90  # 1.5초 무적

    def load_sprites_and_masks(self, folder):
        sprites = []
        masks = []
        for i in range(1, 9):
            tight_path = os.path.join(folder, f"{i}_tight.png")
            cut_path = os.path.join(folder, f"{i}_cut.png")
            orig_path = os.path.join(folder, f"{i}.png")
            if os.path.exists(tight_path):
                img = pygame.image.load(tight_path).convert_alpha()
            elif os.path.exists(cut_path):
                img = pygame.image.load(cut_path).convert_alpha()
            else:
                img = pygame.image.load(orig_path).convert_alpha()
            img = pygame.transform.scale(img, PLAYER_SIZE)
            sprites.append(img)
            masks.append(pygame.mask.from_surface(img))
        return sprites, masks

    def move(self, left, right, jump, dash=False):
        if dash and (left or right):
            self.dashing = True
            self.vx = -MOVE_SPEED * 2 if left else MOVE_SPEED * 2
            self.facing_right = not left
        elif left:
            self.vx = -MOVE_SPEED
            self.facing_right = False
            self.dashing = False
        elif right:
            self.vx = MOVE_SPEED
            self.facing_right = True
            self.dashing = False
        else:
            self.vx = 0
            self.dashing = False
        if jump and self.on_ground:
            self.vy = -JUMP_POWER
            self.on_ground = False
            self.jumping = True

    def attack(self):
        if not self.attacking and self.attack_cooldown == 0:
            self.attacking = True
            self.current_frame = 5  # 6.png (공격)
            self.attack_cooldown = FPS // 2

    def defend(self):
        if not self.defending:
            self.defending = True
            self.current_frame = 4  # 5.png (방어)

    def counter_attack(self):
        self.counter = True
        self.current_frame = 7  # 8.png (카운터)

    def dash(self):
        self.dashing = True
        self.current_frame = 3  # 4.png (회피/대시)

    def update(self):
        # 중력 적용
        self.vy += GRAVITY
        self.y += self.vy
        self.x += self.vx
        # 바닥 충돌
        if self.y + PLAYER_SIZE[1] >= HEIGHT - 30:
            self.y = HEIGHT - 30 - PLAYER_SIZE[1]
            self.vy = 0
            self.on_ground = True
            self.jumping = False
        else:
            self.on_ground = False
        # 공격 쿨타임
        if self.attacking:
            self.current_frame = 5  # 6.png (공격)
            self.attack_cooldown -= 1
            if self.attack_cooldown <= 0:
                self.attacking = False
                self.attack_cooldown = 0
        elif self.defending:
            self.current_frame = 4  # 5.png (방어)
        elif self.dashing:
            self.current_frame = 3  # 4.png (회피/대시)
        elif self.jumping:
            self.current_frame = 6  # 7.png (점프)
        elif self.vx != 0:
            self.current_frame = 1  # 2.png (걷기)
        else:
            self.idle_anim_timer += 1
            if self.idle_anim_timer >= FPS // 6:
                self.idle_anim_timer = 0
                self.idle_anim_index = (self.idle_anim_index + 1) % 3
            self.current_frame = self.idle_anim_index  # 0,1,2 (1~3.png)
        self.rect = self.sprites[self.current_frame].get_rect(topleft=(self.x, self.y))
        # 무적 타이머
        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False

    def draw(self, screen, color=None):
        img = self.sprites[self.current_frame]
        mask = self.masks[self.current_frame]
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
            mask = pygame.mask.from_surface(img)
        # 무적 중이면 5프레임마다 깜박임
        if self.invincible and (self.invincible_timer // 5) % 2 == 0:
            pass  # 깜박임: 그리지 않음
        else:
            screen.blit(img, (self.x, self.y))
        # 히트박스(마스크) 시각화: 외곽선(윤곽선)만 점 찍기
        if color:
            w, h = mask.get_size()
            for y in range(h):
                for x in range(w):
                    if not mask.get_at((x, y)):
                        continue
                    # 8방향 이웃 중 하나라도 0이면 윤곽선
                    is_outline = False
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
                        nx, ny = x+dx, y+dy
                        if 0 <= nx < w and 0 <= ny < h:
                            if not mask.get_at((nx, ny)):
                                is_outline = True
                                break
                        else:
                            # 경계 바깥도 윤곽선
                            is_outline = True
                            break
                    if is_outline:
                        # 무적 중이면 윤곽선도 깜박임
                        if not (self.invincible and (self.invincible_timer // 5) % 2 == 0):
                            screen.set_at((int(self.x + x), int(self.y + y)), color)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("아낙사 vs 아글라이아 Beta 0.0.1")
    clock = pygame.time.Clock()

    # 플랫폼(2층, 3층 등) 정의: (x, y, w, h)
    # platforms = [
    #     pygame.Rect(200, 600, 300, 20),   # 2층 왼쪽 (낮춤)
    #     pygame.Rect(780, 600, 300, 20),   # 2층 오른쪽 (낮춤)
    #     pygame.Rect(500, 420, 280, 20),   # 3층 중앙 (낮춤)
    # ]

    # 플레이어 생성
    player1 = Fighter(100, HEIGHT - 150, "aglia")
    player2 = Fighter(600, HEIGHT - 150, "anaxa")

    # 라운드/타이머/승리 수
    round_time = 120  # 120초
    round_timer = FPS * round_time
    p1_wins = 0
    p2_wins = 0
    round_over = False
    font = pygame.font.SysFont(None, 48)
    big_font = pygame.font.SysFont(None, 80)

    def draw_center_text(text, size=48, color=(0,0,0), y=None):
        fnt = pygame.font.SysFont(None, size)
        txt = fnt.render(text, True, color)
        rect = txt.get_rect(center=(WIDTH//2, y if y is not None else HEIGHT//2))
        screen.blit(txt, rect)

    def platform_collision(player, jump_flag_name):
        # 플레이어가 플랫폼 위에 서도록 처리
        pass  # 플랫폼 기능 비활성화

    running = True
    round_countdown = 0
    p1_attack_pressed = False
    p2_attack_pressed = False
    p1_jump_pressed = False
    p2_jump_pressed = False
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # 공격/점프 입력 KEYDOWN에서만 동작
            if event.type == pygame.KEYDOWN:
                # Player 1
                if event.key == pygame.K_s and not p1_attack_pressed:
                    player1.attack()
                    p1_attack_pressed = True
                if event.key == pygame.K_w and not p1_jump_pressed:
                    p1_jump_pressed = True
                if event.key == pygame.K_q:
                    player1.defend()
                # Player 2
                if event.key == pygame.K_DOWN and not p2_attack_pressed:
                    player2.attack()
                    p2_attack_pressed = True
                if event.key == pygame.K_UP and not p2_jump_pressed:
                    p2_jump_pressed = True
                if event.key == pygame.K_RCTRL:
                    player2.defend()
            # 방어 해제 (키업)
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_q:
                    player1.defending = False
                if event.key == pygame.K_LSHIFT:
                    player1.dashing = False
                if event.key == pygame.K_f:
                    player1.jumping = False
                if event.key == pygame.K_RSHIFT:
                    player2.dashing = False
                if event.key == pygame.K_RCTRL:
                    player2.defending = False
                if event.key == pygame.K_s:
                    p1_attack_pressed = False
                if event.key == pygame.K_DOWN:
                    p2_attack_pressed = False
                if event.key == pygame.K_w:
                    p1_jump_pressed = False
                if event.key == pygame.K_UP:
                    p2_jump_pressed = False

        # 입력 처리
        keys = pygame.key.get_pressed()
        # Player 1: A, D, W, S(공격), Q(방어), E(카운터), LSHIFT(대시)
        p1_left = keys[pygame.K_a]
        p1_right = keys[pygame.K_d]
        p1_dash = keys[pygame.K_LSHIFT]
        # 점프는 키다운에서만 동작
        player1.move(p1_left, p1_right, p1_jump_pressed, dash=p1_dash)
        # Player 2: ←, →, ↑, ↓(공격), RCTRL(방어), RALT(카운터), RSHIFT(대시)
        p2_left = keys[pygame.K_LEFT]
        p2_right = keys[pygame.K_RIGHT]
        p2_dash = keys[pygame.K_RSHIFT]
        player2.move(p2_left, p2_right, p2_jump_pressed, dash=p2_dash)

        # 각 프레임마다 상태 업데이트
        if not round_over:
            player1.update()
            player2.update()
        # 플랫폼 충돌 처리 (점프 입력 플래그도 전달)
        # platform_collision(player1, 'p1_jump_pressed')
        # platform_collision(player2, 'p2_jump_pressed')

        # 라운드 종료 체크 및 카운트다운
        if not round_over:
            round_timer -= 1
            if round_timer <= 0:
                round_over = True
                # 체력 많은 쪽 승리
                if player1.health > player2.health:
                    p1_wins += 1
                elif player2.health > player1.health:
                    p2_wins += 1
            if player1.health <= 0:
                round_over = True
                p2_wins += 1
            elif player2.health <= 0:
                round_over = True
                p1_wins += 1
            if round_over:
                round_countdown = FPS * 5  # 5초 대기

        # 3판2선승제 종료
        match_over = (p1_wins == 2 or p2_wins == 2)
        if not round_over:
            # 1P가 공격 중이고 2P와 충돌
            offset = (int(player2.rect.x - player1.rect.x), int(player2.rect.y - player1.rect.y))
            collide = player1.masks[player1.current_frame].overlap(player2.masks[player2.current_frame], offset)
            if player1.attacking and collide and not player2.invincible:
                if player2.defending:
                    # 방어 중 공격 맞으면 자동 카운터
                    player1.take_damage(20)
                else:
                    player2.take_damage(10)
            # 2P가 공격 중이고 1P와 충돌
            offset2 = (int(player1.rect.x - player2.rect.x), int(player1.rect.y - player2.rect.y))
            collide2 = player2.masks[player2.current_frame].overlap(player1.masks[player1.current_frame], offset2)
            if player2.attacking and collide2 and not player1.invincible:
                if player1.defending:
                    player2.take_damage(20)
                else:
                    player1.take_damage(10)

        # 라운드 종료 후 5초 카운트다운
        if round_over and not match_over:
            round_countdown -= 1
            # 중앙에 라운드 결과 표시
            if player1.health <= 0:
                draw_center_text("2P WIN!", 80, (0,0,255))
            elif player2.health <= 0:
                draw_center_text("1P WIN!", 80, (255,0,0))
            elif round_timer <= 0:
                if player1.health > player2.health:
                    draw_center_text("1P WIN!", 80, (255,0,0))
                elif player2.health > player1.health:
                    draw_center_text("2P WIN!", 80, (0,0,255))
                else:
                    draw_center_text("DRAW", 80, (128,128,128))
            # 카운트다운 표시
            cd_sec = max(1, round_countdown // FPS + 1)
            draw_center_text(f"NEXT ROUND IN {cd_sec}", 48, (0,0,0), y=HEIGHT//2+60)
            if round_countdown <= 0:
                # 다음 라운드 준비
                round_over = False
                round_timer = FPS * round_time
                player1.x, player1.y = 100, HEIGHT - 150
                player2.x, player2.y = 600, HEIGHT - 150
                player1.vx = player1.vy = 0
                player2.vx = player2.vy = 0
                player1.health = 100
                player2.health = 100
                player1.attacking = player1.defending = player1.counter = player1.dashing = player1.jumping = False
                player2.attacking = player2.defending = player2.counter = player2.dashing = player2.jumping = False

        # 그리기
        screen.fill(WHITE)
        # 체력바
        bar_w = 300
        bar_h = 20
        # 1P 체력바 (빨강, 왼쪽 상단)
        pygame.draw.rect(screen, (100,100,100), (40, 30, bar_w, bar_h))
        pygame.draw.rect(screen, (255,0,0), (40, 30, int(bar_w * player1.health / 100), bar_h))
        # 2P 체력바 (파랑, 오른쪽 상단)
        pygame.draw.rect(screen, (100,100,100), (WIDTH-40-bar_w, 30, bar_w, bar_h))
        pygame.draw.rect(screen, (0,0,255), (WIDTH-40-bar_w, 30, int(bar_w * player2.health / 100), bar_h))

        # 체력바 사이에 시간/라운드 표시
        timer_sec = max(0, round_timer // FPS)
        timer_text = font.render(f"{timer_sec:03}", True, (0,0,0))
        timer_rect = timer_text.get_rect(center=(WIDTH//2, 40))
        screen.blit(timer_text, timer_rect)

        # 라운드 승리 표시 (O: win, X: lose)
        round_text = font.render(
            f"{'O'*p1_wins}{'X'*(2-p1_wins)}  VS  {'O'*p2_wins}{'X'*(2-p2_wins)}",
            True, (0,0,0))
        round_rect = round_text.get_rect(center=(WIDTH//2, 80))
        screen.blit(round_text, round_rect)

        # 플랫폼 그리기
        # for plat in platforms:
        #     pygame.draw.rect(screen, (180,180,180), plat)

        # 최종 승자 표시
        if match_over:
            if p1_wins == 2:
                draw_center_text("1P MATCH WIN!", 80, (255,0,0))
            else:
                draw_center_text("2P MATCH WIN!", 80, (0,0,255))

        pygame.draw.rect(screen, (100, 200, 100), (0, HEIGHT - 30, WIDTH, 30))  # 바닥
        player1.draw(screen, color=(255,0,0))  # 빨간색 윤곽선
        player2.draw(screen, color=(0,0,255))  # 파란색 윤곽선
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
