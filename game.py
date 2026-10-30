# -*- coding: utf-8 -*-
"""飞机大战 · Airplane Battle

一个用 Pygame 写的复古太空射击小游戏：操控飞船左右上下移动、发射子弹击毁敌机，
同时躲开撞过来的敌机。开局有引导页，运行中可用 B 暂停、V 静音、ESC 退出。

运行：
    python game.py

自检（无窗口、自动跑 N 帧后退出，用于 CI）：
    python game.py --smoke-test 600
"""

from __future__ import annotations

import argparse
import os
import random
import sys

try:
    import pygame
except ImportError:  # pragma: no cover - 仅在没装依赖时触发
    sys.exit(
        "没有找到 pygame。\n"
        "请先安装依赖：pip install -r requirements.txt\n"
        "（或直接双击仓库里的 run.bat）"
    )

# ---------------------------------------------------------------- 基础配置

TITLE = "太空侵略者"

SCREEN_WIDTH, SCREEN_HEIGHT = 600, 600
FPS = 60

PLAYER_SIZE = (60, 44)
PLAYER_SPEED = 10
PLAYER_HEALTH = 5
PLAYER_BOTTOM_MARGIN = 20

ENEMY_SIZE = (48, 48)
ENEMY_KINDS = 6
ENEMY_SPEED = 3
ENEMY_SPAWN_INTERVAL = 300  # 敌人生成间隔（毫秒）
MAX_ENEMIES = 15

BULLET_SIZE = (6, 12)
BULLET_SPEED = 10
SHOT_COOLDOWN = 100  # 两发子弹的最小间隔（毫秒）

EXPLOSION_DURATION = 1000  # 爆炸特效持续时间（毫秒）
EXPLOSION_FRAMES = 4  # boom.png 是竖向的 4 帧序列图
EXPLOSION_SIZE = (48, 48)
DEATH_FREEZE = 3000  # 死亡后停留时间（毫秒）
INVULNERABLE_TIME = 800  # 被撞后短暂无敌，避免一帧内被连扣多血

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DANGER = (255, 0, 0)
MUTED_GREY = (160, 160, 160)

# 逗号分隔的字体候选，SysFont 会依次尝试；都没有时退回 pygame 自带字体
CJK_FONT_STACK = "microsoftyaheiui,microsoftyahei,simhei,simsun,notosanscjksc,pingfangsc,arial"

GAME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game")


def resource_path(*parts: str) -> str:
    """把 game/ 目录下的相对路径拼成绝对路径，保证在任意工作目录下都能跑。"""
    return os.path.join(GAME_DIR, *parts)


# ---------------------------------------------------------------- 素材加载


def load_image(relative_path: str, size=None):
    """加载图片；素材缺失时给出人能看懂的报错，而不是一屏 traceback。"""
    path = resource_path(relative_path)
    if not os.path.exists(path):
        raise SystemExit(
            f"缺少素材文件：{path}\n"
            "请确认 game/img、game/sound 目录完整（可以从仓库重新下载）。"
        )
    try:
        image = pygame.image.load(path).convert_alpha()
    except pygame.error as exc:
        raise SystemExit(f"素材无法解析：{path}\n{exc}")
    if size is not None:
        image = pygame.transform.smoothscale(image, size)
    return image


def load_sound(relative_path: str):
    """加载音效；音频设备不可用时返回 None，让游戏静音继续跑。"""
    path = resource_path(relative_path)
    if not os.path.exists(path):
        print(f"[警告] 缺少音效 {path}，将跳过该音效", file=sys.stderr)
        return None
    try:
        return pygame.mixer.Sound(path)
    except pygame.error as exc:
        print(f"[警告] 音效加载失败 {path}: {exc}", file=sys.stderr)
        return None


def safe_font(size: int, bold: bool = False):
    """取系统字体，优先选能显示中文的字体。

    pygame 2.6.x 在 Windows 上枚举注册表字体时，如果键下存在非字符串的值
    （例如某些软件写入的 DWORD），pygame.font.SysFont 会直接抛 TypeError。
    这里捕获后回退到 pygame 自带的默认字体，保证游戏一定能起来；
    默认字体没有中文字形，所以暂停提示同时给英文，避免出现空白。
    """
    try:
        return pygame.font.SysFont(CJK_FONT_STACK, size, bold=bold)
    except Exception:  # noqa: BLE001 - 字体枚举的实现细节不该让游戏崩
        font = pygame.font.Font(None, size)
        font.set_bold(bold)
        return font


def fit_image(image, box):
    """按比例缩放到 box 内，别把素材拉扁——原版直接 scale 会把角色压变形。"""
    width, height = image.get_size()
    scale = min(box[0] / width, box[1] / height)
    return pygame.transform.smoothscale(
        image, (max(1, round(width * scale)), max(1, round(height * scale)))
    )


def load_explosion_frames():
    """boom.png 是一张 63x241 的竖向序列图，切成 4 帧当动画用。

    原版把整张竖图直接 blit 到命中点上，画面上会出现一条白色长条——
    这里按帧切开，正确播放爆炸动画。
    """
    sheet = load_image(os.path.join("img", "boom.png"))
    width, height = sheet.get_size()
    frame_height = height // EXPLOSION_FRAMES
    frames = []
    for index in range(EXPLOSION_FRAMES):
        rect = pygame.Rect(0, index * frame_height, width, frame_height)
        frame = sheet.subsurface(rect).copy()
        frames.append(pygame.transform.smoothscale(frame, EXPLOSION_SIZE))
    return frames


class SoundBoard:
    """集中管理音效与静音状态，避免到处写 if not mute。"""

    def __init__(self, sounds: dict, enabled: bool):
        self.sounds = sounds
        self.enabled = enabled
        self.muted = False

    def play(self, name: str) -> None:
        if not self.enabled or self.muted:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        volume = 0 if self.muted else 1
        for sound in self.sounds.values():
            if sound is not None:
                sound.set_volume(volume)
        return self.muted


# ---------------------------------------------------------------- 游戏对象


class Player:
    def __init__(self, image):
        self.image = image
        self.x = SCREEN_WIDTH // 2 - image.get_width() // 2
        self.y = SCREEN_HEIGHT - image.get_height() - PLAYER_BOTTOM_MARGIN
        self.health = PLAYER_HEALTH
        self.invulnerable_until = 0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x, self.y, self.image.get_width(), self.image.get_height())

    def move(self, keys) -> None:
        if keys[pygame.K_LEFT] and self.x > 0:
            self.x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] and self.x < SCREEN_WIDTH - self.image.get_width():
            self.x += PLAYER_SPEED
        if keys[pygame.K_UP] and self.y > 0:
            self.y -= PLAYER_SPEED
        if keys[pygame.K_DOWN] and self.y < SCREEN_HEIGHT - self.image.get_height():
            self.y += PLAYER_SPEED

    def hit(self, now: int) -> bool:
        """扣一次血；无敌期内返回 False，表示这次撞击不生效。"""
        if now < self.invulnerable_until:
            return False
        self.health -= 1
        self.invulnerable_until = now + INVULNERABLE_TIME
        return True


class Game:
    """整个对局的状态机：引导页 → 游戏 → 暂停 / 结束。"""

    def __init__(self, screen: pygame.Surface, assets: dict, sounds: SoundBoard, clock):
        self.screen = screen
        self.assets = assets
        self.sounds = sounds
        self.clock = clock

        self.player = Player(assets["player"])
        self.bullets = []
        self.enemies = []
        self.explosions = []

        self.score = 0
        self.running = True
        self.paused = False

        self.font_score = safe_font(36)
        self.font_hint = safe_font(28)
        now = pygame.time.get_ticks()
        self.last_shot = now
        self.enemy_spawn_time = now

    # -- 引导页 --------------------------------------------------------

    def show_instructions(self) -> None:
        font = safe_font(40)
        waiting = True
        while waiting and self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    waiting = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        waiting = False
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False
                        waiting = False

            self.screen.blit(self.assets["ui"], (0, 0))
            text = font.render("<bui bui game>", True, DANGER)
            self.screen.blit(text, (50, 50))
            pygame.display.flip()
            self.clock.tick(FPS)

    # -- 主循环 --------------------------------------------------------

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_b:
                    self.paused = not self.paused
                elif event.key == pygame.K_v:
                    self.sounds.toggle_mute()

    def spawn_enemy(self, now: int) -> None:
        if now - self.enemy_spawn_time < ENEMY_SPAWN_INTERVAL:
            return
        self.enemy_spawn_time = now
        if len(self.enemies) >= MAX_ENEMIES:
            return
        image = random.choice(self.assets["enemies"])
        self.enemies.append(
            {"x": random.randint(0, SCREEN_WIDTH - image.get_width()), "y": 0, "img": image}
        )

    def update(self, now: int, keys, autofire: bool = False) -> None:
        self.player.move(keys)

        # 发射子弹
        if (keys[pygame.K_SPACE] or autofire) and now - self.last_shot > SHOT_COOLDOWN:
            self.sounds.play("shoot")
            self.bullets.append(
                {
                    "x": self.player.x
                    + self.player.image.get_width() // 2
                    - self.assets["bullet"].get_width() // 2,
                    "y": self.player.y,
                    "img": self.assets["bullet"],
                }
            )
            self.last_shot = now

        self.spawn_enemy(now)

        # 敌人下移；越过下边界就用列表推导一次性剔除，避免边遍历边删除
        bottom = SCREEN_HEIGHT
        for enemy in self.enemies:
            enemy["y"] += ENEMY_SPEED
        self.enemies = [enemy for enemy in self.enemies if enemy["y"] <= bottom]

        # 子弹上移
        for bullet in self.bullets:
            bullet["y"] -= BULLET_SPEED
        self.bullets = [bullet for bullet in self.bullets if bullet["y"] > 0]

        self._resolve_bullet_hits()
        self._resolve_player_hits(now)

        # 爆炸特效到期就清掉
        self.explosions = [
            boom for boom in self.explosions
            if now - boom["start_time"] < EXPLOSION_DURATION
        ]

    def _resolve_bullet_hits(self) -> None:
        bullet_w, bullet_h = self.assets["bullet"].get_size()
        for bullet in self.bullets[:]:
            bullet_rect = pygame.Rect(bullet["x"], bullet["y"], bullet_w, bullet_h)
            for enemy in self.enemies[:]:
                enemy_rect = pygame.Rect(
                    enemy["x"], enemy["y"], enemy["img"].get_width(), enemy["img"].get_height()
                )
                if bullet_rect.colliderect(enemy_rect):
                    self.bullets.remove(bullet)
                    self.enemies.remove(enemy)
                    self.sounds.play("destroyed")
                    self.score += 100
                    self.spawn_explosion(
                        enemy["x"] + enemy["img"].get_width() // 2,
                        enemy["y"] + enemy["img"].get_height() // 2,
                        pygame.time.get_ticks(),
                    )
                    break

    def spawn_explosion(self, center_x: int, center_y: int, now: int) -> None:
        self.explosions.append(
            {"x": center_x, "y": center_y, "start_time": now}
        )

    def _resolve_player_hits(self, now: int) -> None:
        player_rect = self.player.rect
        for enemy in self.enemies[:]:
            enemy_rect = pygame.Rect(
                enemy["x"], enemy["y"], enemy["img"].get_width(), enemy["img"].get_height()
            )
            if not player_rect.colliderect(enemy_rect):
                continue
            self.enemies.remove(enemy)
            # 一次撞击只扣一次血（无敌帧兜底），否则三架敌机同帧撞上会瞬间空血
            if self.player.hit(now):
                self.spawn_explosion(
                    self.player.x + self.player.image.get_width() // 2,
                    self.player.y + self.player.image.get_height() // 2,
                    now,
                )
                if self.player.health <= 0:
                    self.sounds.play("die")
                    self._wait_with_events(DEATH_FREEZE)
                    self.running = False
                    return

    def _wait_with_events(self, duration_ms: int) -> None:
        """死亡后的停顿：保持窗口响应，别让玩家以为程序卡死了。"""
        deadline = pygame.time.get_ticks() + duration_ms
        while pygame.time.get_ticks() < deadline and self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
            self.draw()
            self.clock.tick(FPS)

    # -- 绘制 ----------------------------------------------------------

    def draw(self) -> None:
        screen = self.screen
        now = pygame.time.get_ticks()
        screen.blit(self.assets["background"], (0, 0))
        screen.blit(self.player.image, (self.player.x, self.player.y))

        for bullet in self.bullets:
            screen.blit(bullet["img"], (bullet["x"], bullet["y"]))
        for enemy in self.enemies:
            screen.blit(enemy["img"], (enemy["x"], enemy["y"]))

        # 爆炸按帧播放：1 秒 4 帧，最后停在余烬那一帧
        booms = self.assets["booms"]
        frame_ms = EXPLOSION_DURATION / len(booms)
        for boom in self.explosions:
            index = min(len(booms) - 1, int((now - boom["start_time"]) / frame_ms))
            image = booms[index]
            screen.blit(image, image.get_rect(center=(boom["x"], boom["y"])))

        # HUD 垫一层半透明底，避免分数压在敌机上看不清
        hud = pygame.Surface((SCREEN_WIDTH, 46), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 110))
        screen.blit(hud, (0, 0))

        score_text = self.font_score.render(f"score: {self.score}", True, WHITE)
        health_text = self.font_score.render(f"life: {self.player.health}", True, WHITE)
        screen.blit(score_text, (10, 6))
        screen.blit(health_text, (SCREEN_WIDTH - health_text.get_width() - 10, 6))

        if self.paused:
            self._draw_banner("PAUSED  (B 继续)", DANGER)
        elif self.sounds.muted:
            self._draw_banner("MUTED  (V 开声音)", MUTED_GREY)

        pygame.display.flip()

    def _draw_banner(self, text: str, color) -> None:
        surface = self.font_hint.render(text, True, color)
        rect = surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        plate = rect.inflate(36, 24)
        plate_surface = pygame.Surface(plate.size, pygame.SRCALPHA)
        pygame.draw.rect(
            plate_surface, (0, 0, 0, 160), plate_surface.get_rect(), border_radius=10
        )
        pygame.draw.rect(
            plate_surface, (*color, 220), plate_surface.get_rect(), 2, border_radius=10
        )
        self.screen.blit(plate_surface, plate)
        self.screen.blit(surface, rect)

    # -- 一局 ----------------------------------------------------------

    def play(self, smoke_frames: int | None = None) -> int:
        """跑一局。smoke_frames 不为空时不读键盘、自动开火，跑满帧数就退出。"""
        frames = 0
        autofire = smoke_frames is not None
        while self.running:
            self.handle_events()
            if not self.running:
                break

            now = pygame.time.get_ticks()
            if not self.paused:
                keys = pygame.key.get_pressed() if not autofire else _NONE_KEYS
                self.update(now, keys, autofire=autofire)
                self.draw()
                frames += 1
                if smoke_frames is not None and frames >= smoke_frames:
                    print(
                        f"[smoke] {frames} 帧完成，score={self.score}, "
                        f"life={self.player.health}, 敌人={len(self.enemies)}, "
                        f"子弹={len(self.bullets)}"
                    )
                    return 0
            else:
                self.draw()
            self.clock.tick(FPS)
        return 0


class _NoKeys:
    """无头自检用：伪装成 pygame.key.get_pressed() 的返回对象。"""

    def __getitem__(self, item):
        return 0


_NONE_KEYS = _NoKeys()


# ---------------------------------------------------------------- 启动


def build_assets() -> dict:
    return {
        "player": fit_image(load_image(os.path.join("img", "player_ship.png")), PLAYER_SIZE),
        "enemies": [
            fit_image(load_image(os.path.join("img", f"enemy{i}.png")), ENEMY_SIZE)
            for i in range(1, ENEMY_KINDS + 1)
        ],
        "bullet": fit_image(load_image(os.path.join("img", "bullet.png")), BULLET_SIZE),
        "booms": load_explosion_frames(),
        "background": load_image(
            os.path.join("img", "began.png"), (SCREEN_WIDTH, SCREEN_HEIGHT)
        ),
        "ui": load_image(os.path.join("img", "ui.png"), (SCREEN_WIDTH, SCREEN_HEIGHT)),
    }


def init_pygame(headless: bool):
    if headless:
        # 必须在 pygame.init() 之前设置，SDL 才会用虚拟驱动
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    pygame.init()
    audio_ok = True
    try:
        pygame.mixer.init()
    except pygame.error as exc:
        audio_ok = False
        print(f"[警告] 音频设备不可用，游戏将静音运行：{exc}", file=sys.stderr)

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    return screen, audio_ok


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="飞机大战（Pygame 版）")
    parser.add_argument(
        "--smoke-test",
        type=int,
        nargs="?",
        const=600,
        default=None,
        metavar="帧数",
        help="无窗口自检：自动跑指定帧数后退出（默认 600 帧）",
    )
    parser.add_argument("--mute", action="store_true", help="开局静音")
    args = parser.parse_args(argv)

    smoke = args.smoke_test
    screen, audio_ok = init_pygame(headless=smoke is not None)

    assets = build_assets()
    pygame.display.set_icon(assets["player"])

    if audio_ok:
        sounds = {
            "background": load_sound(os.path.join("sound", "background.mp3")),
            "shoot": load_sound(os.path.join("sound", "shoot.mp3")),
            "destroyed": load_sound(os.path.join("sound", "destroyed.mp3")),
            "die": load_sound(os.path.join("sound", "die.mp3")),
        }
    else:
        sounds = {}

    soundboard = SoundBoard(sounds, enabled=audio_ok)
    if args.mute:
        soundboard.toggle_mute()

    if not soundboard.muted and sounds.get("background") is not None:
        sounds["background"].play(-1)  # -1 = 循环播放

    game = Game(screen, assets, soundboard, pygame.time.Clock())
    if smoke is None:
        game.show_instructions()

    try:
        return game.play(smoke_frames=smoke)
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
