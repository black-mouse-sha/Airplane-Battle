# -*- coding: utf-8 -*-
"""素材背景清理：把烘焙进图片里的棋盘格 / 纯白背景改成真正的透明。

这些素材是从网页上截图来的，所谓"透明背景"其实是画上去的棋盘格（白 + #cccccc 交替）。
这里从四周用 8 邻域漫水填充，把连通的背景色像素 alpha 置 0；有深色描边的
主体不会被吃掉，因为填充会在描边处停下。
"""
from __future__ import annotations

import os
import sys
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

CHECKER = [(255, 255, 255), (204, 204, 204), (192, 192, 192), (238, 238, 238)]
TOLERANCE = 14


def is_background(pixel) -> bool:
    r, g, b, a = pixel
    if a == 0:
        return False
    for cr, cg, cb in CHECKER:
        if abs(r - cr) <= TOLERANCE and abs(g - cg) <= TOLERANCE and abs(b - cb) <= TOLERANCE:
            return True
    return False


def border_is_background(surface) -> bool:
    w, h = surface.get_size()
    samples = 0
    hits = 0
    step_x = max(1, w // 24)
    step_y = max(1, h // 24)
    for x in range(0, w, step_x):
        for y in (0, h - 1):
            samples += 1
            hits += is_background(surface.get_at((x, y)))
    for y in range(0, h, step_y):
        for x in (0, w - 1):
            samples += 1
            hits += is_background(surface.get_at((x, y)))
    return samples > 0 and hits / samples >= 0.7


def strip_background(surface) -> pygame.Surface:
    w, h = surface.get_size()
    result = surface.convert_alpha()
    raw = bytearray(pygame.image.tobytes(result, "RGBA"))

    def get(x, y):
        i = (y * w + x) * 4
        return raw[i], raw[i + 1], raw[i + 2], raw[i + 3]

    visited = bytearray(w * h)
    queue = deque()

    def push(x, y):
        if 0 <= x < w and 0 <= y < h and not visited[y * w + x]:
            visited[y * w + x] = 1
            if is_background(get(x, y)):
                queue.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    cleared = 0
    while queue:
        x, y = queue.popleft()
        i = (y * w + x) * 4
        if raw[i + 3] == 0:
            continue
        raw[i + 3] = 0
        cleared += 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and not visited[ny * w + nx]:
                        visited[ny * w + nx] = 1
                        if is_background(get(nx, ny)):
                            queue.append((nx, ny))

    out = pygame.image.frombytes(bytes(raw), (w, h), "RGBA")
    return out, cleared / (w * h)


def main() -> int:
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "game/img"
    preview_dir = sys.argv[2] if len(sys.argv) > 2 else ""
    pygame.init()
    pygame.display.set_mode((1, 1))

    targets = [
        "player_ship.png",
        "bullet.png",
        "boom.png",
        "enemy3.png",
        "enemy6.png",
        "explosion1.png",
        "explosion2.png",
        "explosion3.png",
    ]
    for name in targets:
        path = os.path.join(src_dir, name)
        if not os.path.exists(path):
            print(f"skip {name}: 不存在")
            continue
        original = pygame.image.load(path)
        if not border_is_background(original):
            print(f"skip {name}: 边缘不是白/棋盘背景，保持原样")
            continue
        cleaned, ratio = strip_background(original)
        pygame.image.save(cleaned, path)
        print(f"{name:20} 透明化 {ratio * 100:5.1f}% 的像素")

        if preview_dir:
            bg = pygame.Surface(original.get_size())
            bg.fill((24, 18, 40))
            bg.blit(cleaned, (0, 0))
            pygame.image.save(bg, os.path.join(preview_dir, f"clean_{name}"))
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
