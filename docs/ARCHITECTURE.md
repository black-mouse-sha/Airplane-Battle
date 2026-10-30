# 架构与实现说明

> 这份文档讲「代码为什么长这样」，配合 6 张交互式架构图一起看更清楚（图在 `docs/diagrams/`，README 里有目录）。
> 源码全部在 `game.py` 一个文件里，约 538 行。

---

## 1. 设计取舍

| 选择 | 理由 | 代价 |
|---|---|---|
| **单文件** | 一个 Pygame 小游戏不该有构建步骤。`python game.py` 就能跑，改一行、存盘、重跑，没有 import 关系要维护。 | 538 行后开始难找东西；想加关卡就该拆包了。 |
| **数据用 dict，不建实体类** | 敌机、子弹、爆炸都只是「坐标 + 贴图」的载体，dict 足够，读写直观。 | 没有类型提示，字段名写错要到运行时才发现。 |
| **不用 `pygame.sprite.Group`** | 本项目碰撞规则是两组自定义判定（子弹×敌机、敌机×玩家），Sprite 组带来的抽象比省下的代码多。 | 自己维护三份列表，越界清理得手写。 |
| **素材路径锚定脚本目录** | `resource_path()` 用 `__file__` 算绝对路径，双击运行、在任何 cwd 下运行都不会找不到图。 | 无（这是原版最容易踩的坑，已经修好）。 |
| **无外部配置** | 数值全是文件顶部的常量。 | 调难度要改代码。 |

---

## 2. 分层

```text
入口层    main() ── init_pygame() ── build_assets() ── Game(...) ── play()
              │                                                      │
资源层    resource_path / load_image / load_sound / fit_image / load_explosion_frames / safe_font
              │                                                      │
对象层    Player（坐标、移动、扣血、无敌）      Game（事件、生成、更新、碰撞、绘制）      SoundBoard（音效、静音）
              │                                                      │
数据层    enemies[]  bullets[]  explosions[]  score  player.health  （全部是 list / dict / int）
```

### 入口层

- `main(argv)`：`argparse` 解析 `--smoke-test` / `--mute`，串起启动顺序，`finally: pygame.quit()` 保证退出干净。
- `init_pygame(headless)`：`pygame.init()` → `mixer.init()`。**音频失败不算致命错误**，返回 `audio_ok=False`，后面所有音效走空实现。
- `build_assets()`：一次性把所有图和爆炸帧读进内存，运行期不再碰磁盘。

### 资源层

| 函数 | 职责 | 失败行为 |
|---|---|---|
| `resource_path(*parts)` | 拼 `game/` 下的绝对路径 | — |
| `load_image(rel)` | `image.load` + `convert_alpha()`（保留透明通道） | 中文报错 + `SystemExit`，明确告诉用户缺哪个文件 |
| `fit_image(img, box)` | 等比缩放进 `box`，不拉扁 | — |
| `load_explosion_frames()` | 把 63x241 的 `boom.png` 切成 4 帧 48x48 | 同上 |
| `load_sound(rel)` | 返回 `Sound` | 只打印警告，返回 `None`，游戏继续 |
| `safe_font(size, bold)` | CJK 字体栈（雅黑 / 黑体 / 宋体 / Noto / 苹方） | `SysFont` 抛异常时回退到 `pygame.font.Font(None, size)` |

> `safe_font` 里的 `except Exception` 是刻意的：pygame 2.6.x 在部分 Windows 上枚举注册表字体时会因为非字符串的 DWORD 值抛 `TypeError`，这个 bug 不该让整个游戏起不来。

### 对象层

**`Player`**

| 成员 | 说明 |
|---|---|
| `x, y` | 左上角坐标，`move()` 里按方向键加减 10 像素，并做边界钳制 |
| `health` | 初始 5 |
| `invulnerable_until` | 时间戳；`hit(now)` 在无敌期内直接返回 `False`，表示这次撞击不算 |
| `rect` | 每次取都新建 `pygame.Rect`，避免外部改了缓存值 |

**`Game`**

| 方法 | 频率 | 做什么 |
|---|---|---|
| `handle_events()` | 每帧 | `pygame.event.get()`，处理 QUIT / ESC / B / V |
| `spawn_enemy(now)` | 每帧判断 | `now - enemy_spawn_time ≥ 300ms` 且数量 < 15 时，随机选一种敌机、随机 x、y=0 |
| `update(now, keys)` | 每帧 | 移动 → 射击 → 生成 → 位移 → 两组碰撞 → 清理过期爆炸 |
| `_resolve_bullet_hits()` | 每帧 | 子弹 × 敌机，命中：删子弹、删敌机、+100 分、音效、爆炸 |
| `_resolve_player_hits(now)` | 每帧 | 敌机 × 玩家，撞到：删敌机、`player.hit()`、爆炸；血量≤0 触发死亡流程 |
| `draw()` | 每帧 | blit 顺序：背景 → 飞船 → 子弹 → 敌机 → 爆炸帧 → HUD → `display.flip()` |
| `play(smoke_frames)` | 一局 | 主循环；`smoke_frames` 非空时用 `_NoKeys` 代替键盘、自动开火 |

**`SoundBoard`**：把「静音」收敛成 `play()` 里的一个判断，避免每处音效都写 `if not mute`。

---

## 3. 数据模型

```python
enemies    : list[dict]   # {"x": int, "y": int, "img": Surface}
bullets    : list[dict]   # {"x": int, "y": int, "img": Surface}
explosions : list[dict]   # {"x": int, "y": int, "start_time": int}  # x/y 是爆炸中心
score      : int
player     : Player
```

爆炸存**中心点**而不是左上角，因为爆炸帧大小（48x48）和敌机贴图大小（48x48，非正方形素材等比缩放后更小）不一致，画的时候用 `image.get_rect(center=...)` 对齐才不会偏。

---

## 4. 一帧都发生了什么

```text
t = get_ticks()                      # 毫秒时间戳，只用这一个时钟
handle_events()                      # 输入 → 状态标志
if paused:  draw();  tick(60); continue      # 暂停时只重绘
keys = get_pressed()
update(t, keys)                      # 逻辑
draw()                               # 渲染
tick(60)                             # 把这一帧压到 16.6ms
```

时间相关的判断全部基于 `get_ticks()` 的**绝对毫秒**，不做「每帧加多少」的累加，这样掉帧也不会让节奏漂移：

| 逻辑 | 判定式 |
|---|---|
| 能不能开火 | `now - last_shot > 100` |
| 该不该生成敌机 | `now - enemy_spawn_time > 300` |
| 爆炸播到第几帧 | `int((now - start_time) / 250)`，封顶 3 |
| 爆炸是否该清理 | `now - start_time ≥ 1000` |
| 是否还在无敌 | `now < invulnerable_until` |

---

## 5. 碰撞判定

用 `pygame.Rect.colliderect()` 做轴对齐矩形检测，够用且比像素级检测快几个数量级。

两个坑，都在 v1.2.0 修了：

1. **边遍历边删**。原版 `for enemy in enemies: if enemy['y'] > 600: enemies.remove(enemy)` 会漏掉紧随其后的元素；现在改成先算位移、再用列表推导一次性过滤。
2. **一帧多次扣血**。原来 `for enemy in enemies[:]` 里每个撞上的敌机都扣 1 血，三架同时撞就是 -3，还连着放三次死亡音效。现在第一次撞击后进入 800ms 无敌，后续撞击在 `Player.hit()` 里被拒。

---

## 6. 素材管线

```text
game/img/*.png ──load_image()──> Surface(convert_alpha)
                   │
                   ├── fit_image() ──> 等比缩放到目标框
                   ├── load_explosion_frames() ──> 4 帧（boom.png 竖切）
                   └── build_assets() ──> dict，常驻内存
game/sound/*.mp3 ──load_sound()──> Sound（失败 → None）
```

**为什么要 `convert_alpha()`**：不转换的话每帧 blit 都要做一次格式转换，600x600 全屏绘制在低端机上会明显掉帧。

**为什么要 `clean_assets.py`**：原始素材的"透明背景"其实是画上去的棋盘格，直接贴图会看到灰白方块。脚本用 8 邻域漫水填充把与四边连通、且接近白/棋盘灰的像素 alpha 置 0；主体有深色描边，填充到描边就停了，不会吃进图形内部。这一步是**离线**做的，产物已经提交进仓库，运行期没有额外开销。

---

## 7. 可测试性

界面程序最难测的是「跑起来有没有崩」。这里给了一个最小但够用的钩子：

```bash
python game.py --smoke-test 600
```

它做三件事：

1. 把 `SDL_VIDEODRIVER` / `SDL_AUDIODRIVER` 设成 `dummy`（必须在 `pygame.init()` 之前，否则不生效）；
2. 跳过引导页，用 `_NoKeys` 顶替 `pygame.key.get_pressed()`，同时打开自动开火——这样子弹、敌机、碰撞、爆炸、HUD 全部会被执行到；
3. 跑满 N 帧后打印一行统计并返回 0。

`.github/workflows/smoke.yml` 就是跑这个，外加 `compileall` 语法检查。它挡不住视觉回归（没有像素比对），但能挡住「改了代码忘了测，素材路径写错」这类最常见的事故。

---

## 8. 技术债与扩展点

| 技术债 | 影响 | 建议 |
|---|---|---|
| 单文件 538 行 | 加第二个玩法就要拆 | 按 `entities.py` / `assets.py` / `scenes.py` 拆 |
| 每帧 `font.render()` 两次 | 字体栅格化有开销 | 分数变化时才重渲染并缓存 Surface |
| 敌机/子弹用 dict | 字段名靠记忆 | 换 `dataclass`，成本很低 |
| 没有难度曲线 | 玩久了腻 | 用 `score // 1000` 提升 `ENEMY_SPEED`、缩短生成间隔 |
| 无场景管理 | 只有「引导页 + 一局」 | 引入 `Scene` 基类，做菜单 / 暂停菜单 / 结算页 |
| 音效无对象池 | 高频射击时 `Sound.play()` 会抢通道 | 用 `pygame.mixer.set_num_channels()` 扩通道，或复用 Channel |
| 无存档 | 最高分不留 | `json` 落盘到用户目录即可 |

---

## 9. 一次典型的改动路径

想加「难度随时间上升」：

1. `game.py` 顶部把 `ENEMY_SPEED`、`ENEMY_SPAWN_INTERVAL` 挪进 `Game.__init__` 变成实例属性；
2. `update()` 里按 `score` 或存活时间算一个新值；
3. `--smoke-test` 跑一遍确认没崩，再手动玩两分钟看手感；
4. `CHANGELOG.md` 记一笔。
