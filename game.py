import pygame  # 游戏包
import random  # 随机产生敌人用
import os      # 让这个文件在让任何电脑上都能运行

# 获取game目录的路径，这个目录与game.py文件同级   (这里获取到的是绝对路径 可以试试相对路径去优化)
game_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game')

# 构建资源路径    lambda 是 高级版 def resource_path(){}
resource_path = lambda filename: os.path.join(game_dir, filename)

# 初始化Pygame    激活
pygame.init()
pygame.mixer.init()

# 设置屏幕大小
SCREEN_WIDTH, SCREEN_HEIGHT = 600, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# 设置标题和图标
pygame.display.set_caption("太空侵略者")

# 定义颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# 加载背景音乐和音效
background_music = pygame.mixer.Sound(resource_path('sound/background.mp3'))
shoot_sound = pygame.mixer.Sound(resource_path('sound/shoot.mp3'))
destroyed_sound = pygame.mixer.Sound(resource_path('sound/destroyed.mp3'))
die_sound = pygame.mixer.Sound(resource_path('sound/die.mp3'))  # 飞船死亡音效

# 播放背景音乐
background_music.play(-1)

# 玩家飞船
player_image = pygame.image.load(resource_path('img/player_ship.png'))
player_image = pygame.transform.scale(player_image, (50, 30))
player_x = SCREEN_WIDTH // 2 - player_image.get_width() // 2
player_y = SCREEN_HEIGHT - player_image.get_height() - 20
player_speed = 10

# 敌人
enemy_images = [pygame.image.load(resource_path(f'img/enemy{i}.png')) for i in range(1, 7)]
enemy_images = [pygame.transform.scale(img, (40, 30)) for img in enemy_images]
enemy_speed = 3
enemy_spawn_interval = 300  # 敌人生成的时间间隔，单位为毫秒
enemy_spawn_time = pygame.time.get_ticks()

# 子弹
bullet_image = pygame.image.load(resource_path('img/bullet.png'))
bullet_image = pygame.transform.scale(bullet_image, (3, 6))
bullets = []
bullet_speed = 10
last_shot = pygame.time.get_ticks()

# 爆炸效果
explosion_image = pygame.image.load(resource_path('img/boom.png'))
explosion_duration = 1000  # 爆炸持续时间，单位为毫秒
explosions = []

# 背景图片
background_image = pygame.image.load(resource_path('img/began.png'))
background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
began_image =  pygame.image.load(resource_path('img/ui.png'))
began_image = pygame.transform.scale(began_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
# 得分和生命值
score = 0
player_health = 5  # 初始生命值为3

# 敌人列表和最大敌人数量
enemies = []
max_enemies = 15

# 游戏循环标志
running = True
paused = False  # 添加暂停标志
mute = False  # 添加静音标志

# 游戏说明
def show_instructions():
    instructions = [
        "<bui bui game>"
    ]
    font = pygame.font.SysFont('arial', 40)  # 使用Arial字体

    # 绘制背景图片

    screen.blit(began_image, (0, 0))

    for i, instr in enumerate(instructions):
        text_surface = font.render(instr, True, WHITE)
        if instr == instructions[0]:  # 为第一个说明文字添加加粗和颜色
            font.set_bold(True)
            text_surface = font.render(instr, True, (255, 0, 0))  # 红色
            font.set_bold(False)
        screen.blit(text_surface, (50, 50 + i * 50))
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # 处理退出事件
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                waiting = False

# 在游戏主循环之前调用 show_instructions() 函数
show_instructions()  # 显示游戏说明并等待用户按键继续
# 游戏主循环
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                paused = not paused  # 切换暂停状态
            elif event.key == pygame.K_v:
                mute = not mute  # 切换静音状态
                if mute:
                    background_music.set_volume(0)
                    shoot_sound.set_volume(0)
                    destroyed_sound.set_volume(0)
                    die_sound.set_volume(0)
                else:
                    background_music.set_volume(1)
                    shoot_sound.set_volume(1)
                    destroyed_sound.set_volume(1)
                    die_sound.set_volume(1)

    if not paused:
        # 玩家控制
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player_x > 0:
            player_x -= player_speed
        if keys[pygame.K_RIGHT] and player_x < SCREEN_WIDTH - player_image.get_width():
            player_x += player_speed
        if keys[pygame.K_UP] and player_y > 0:
            player_y -= player_speed
        if keys[pygame.K_DOWN] and player_y < SCREEN_HEIGHT - player_image.get_height():
            player_y += player_speed

        # 子弹发射
        current_time = pygame.time.get_ticks()
        if keys[pygame.K_SPACE] and current_time - last_shot > 100:
            if not mute:
                shoot_sound.play()  # 播放射击音效
            bullets.append({'x': player_x + player_image.get_width() // 2 - bullet_image.get_width() // 2, 'y': player_y, 'img': bullet_image})
            last_shot = current_time

        # 更新敌人
        if current_time - enemy_spawn_time > enemy_spawn_interval:
            enemy_spawn_time = current_time
            if len(enemies) < max_enemies:
                enemy_x = random.randint(0, SCREEN_WIDTH - 40)
                enemy_y = 0
                enemies.append({'x': enemy_x, 'y': enemy_y, 'img': random.choice(enemy_images)})

        for enemy in enemies:
            enemy['y'] += enemy_speed
            if enemy['y'] > SCREEN_HEIGHT:
                enemies.remove(enemy)

        # 更新子弹位置
        for bullet in bullets:
            bullet['y'] -= bullet_speed
            if bullet['y'] <= 0:
                bullets.remove(bullet)

        # 碰撞检测：子弹和敌人
        for bullet in bullets[:]:
            for enemy in enemies[:]:
                if (bullet['x'] < enemy['x'] + enemy['img'].get_width() and
                    enemy['x'] < bullet['x'] + bullet_image.get_width() and
                    bullet['y'] < enemy['y'] + enemy['img'].get_height() and
                    enemy['y'] < bullet['y'] + bullet_image.get_height()):
                    bullets.remove(bullet)
                    enemies.remove(enemy)
                    if not mute:
                        destroyed_sound.play()  # 播放摧毁音效
                    score += 100
                    explosions.append({'x': enemy['x'], 'y': enemy['y'], 'start_time': pygame.time.get_ticks()})
                    break

        # 碰撞检测：敌人和飞船
        for enemy in enemies[:]:
            if (player_x < enemy['x'] + enemy['img'].get_width() and
                enemy['x'] < player_x + player_image.get_width() and
                player_y < enemy['y'] + enemy['img'].get_height() and
                enemy['y'] < player_y + player_image.get_height()):
                player_health -= 1  # 减少生命值
                enemies.remove(enemy)
                if player_health <= 0:
                    if not mute:
                        die_sound.play()  # 播放飞船死亡音效
                    explosions.append({'x': player_x, 'y': player_y, 'start_time': pygame.time.get_ticks()})
                    pygame.time.wait(3000)  # 死亡后休眠三秒
                    running = False  # 游戏结束
        # 更新爆炸效果
        for explosion in explosions[:]:
            if pygame.time.get_ticks() - explosion['start_time'] < explosion_duration:
                screen.blit(explosion_image, (explosion['x'], explosion['y']))
            else:
                explosions.remove(explosion)

        # 绘制背景、玩家飞船、子弹、敌人和得分
        screen.blit(background_image, (0, 0))
        screen.blit(player_image, (player_x, player_y))
        for bullet in bullets:
            screen.blit(bullet['img'], (bullet['x'], bullet['y']))
        for enemy in enemies:
            screen.blit(enemy['img'], (enemy['x'], enemy['y']))
        font = pygame.font.SysFont(None, 36)
        score_text = font.render(f"score: {score}", True, WHITE)
        health_text = font.render(f"life: {player_health}", True, WHITE)
        screen.blit(score_text, (10, 10))
        screen.blit(health_text, (SCREEN_WIDTH - 150, 10))

        # 更新屏幕显示
        pygame.display.flip()
        # 控制游戏帧率
        pygame.time.Clock().tick(60)

# 退出Pygame
pygame.quit()