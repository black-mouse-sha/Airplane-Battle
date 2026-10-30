# 飞机大战 · 完整使用手册

> 面向「我只想跑起来」和「我想改它」两种人。README 里只讲 30 秒上手，这一篇讲全部细节。

---

## 1. 环境要求

| 项 | 要求 | 说明 |
|---|---|---|
| 操作系统 | Windows / macOS / Linux | 有桌面环境即可；纯 SSH 服务器只能用 `--smoke-test` |
| Python | 3.9 及以上 | 3.10 / 3.12 / 3.13 实测可用 |
| 依赖 | `pygame>=2.5,<3` | 官方 wheel，装上就能用，不需要编译 |
| 显示器 | 600x600 的窗口 | 窗口不可缩放，固定尺寸 |
| 声卡 | 可选 | 没有音频设备会自动静音，不影响玩 |

---

## 2. 三种启动方式

### 方式 A：双击 `run.bat`（Windows，最省事）

首次运行会自动建 `.venv` 并装依赖，第二次起直接开游戏。

### 方式 B：`run.sh`（macOS / Linux）

```bash
chmod +x run.sh
./run.sh
```

### 方式 C：手动

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python game.py
```

装依赖慢就换源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 3. 操作

| 按键 | 作用 | 什么时候有效 |
|---|---|---|
| `↑` `↓` `←` `→` | 移动飞船 | 游戏进行中 |
| `空格` | 发射子弹（100ms 冷却） | 游戏进行中 |
| `Enter` | 从引导页开始游戏 | 引导页 |
| `B` | 暂停 / 继续 | 游戏进行中 |
| `V` | 静音 / 取消静音 | 任何时候 |
| `ESC` | 直接退出 | 任何时候（包括死亡停顿中） |
| 关闭窗口 | 退出 | 任何时候 |

暂停时画面中央显示 `PAUSED (B 继续)`，静音时显示 `MUTED (V 开声音)`。

---

## 4. 规则

| 规则 | 数值 |
|---|---|
| 初始生命 | 5 |
| 击毁一架敌机 | +100 分 |
| 被敌机撞到 | -1 生命，之后 **800ms 无敌** |
| 生命归零 | 播放死亡音效，画面停留 3 秒后退出 |
| 敌机生成 | 每 300ms 一架，屏幕上最多 15 架 |
| 敌机下落速度 | 3 像素 / 帧（60 FPS 下约 180 像素 / 秒） |
| 子弹速度 | 10 像素 / 帧 |
| 飞船速度 | 10 像素 / 帧 |
| 爆炸特效 | 1 秒，4 帧动画 |

> 一帧内被三架敌机同时撞上只扣 1 血——这是 v1.2.0 加的无敌帧在兜底。

---

## 5. 命令行参数

```text
python game.py [--smoke-test [帧数]] [--mute]
```

| 参数 | 作用 |
|---|---|
| `--smoke-test` | 无窗口自检：改用 SDL dummy 驱动，自动开火跑指定帧数（默认 600）后退出 |
| `--mute` | 开局静音（背景乐也不会播放） |

### 无头自检输出

```bash
$ python game.py --smoke-test 600
[smoke] 600 帧完成，score=400, life=5, 敌人=10, 子弹=12
```

退出码恒为 `0`；如果素材缺失或代码抛异常，会以非 0 退出——CI 就是靠这个判断的。这个模式不读键盘、自动开火，所以能在没有显示器和声卡的 runner 上跑。

---

## 6. 素材

### 目录结构

```text
game/
├─ img/
│  ├─ player_ship.png      # 玩家飞船
│  ├─ enemy1..6.png        # 6 种敌机（随机抽取）
│  ├─ bullet.png           # 子弹
│  ├─ boom.png             # 爆炸序列图：63x241，竖排 4 帧
│  ├─ began.png            # 游戏内背景
│  └─ ui.png               # 引导页底图（上面写着 Enter/B/V 的操作说明）
└─ sound/
   ├─ background.mp3       # 循环背景乐
   ├─ shoot.mp3            # 射击
   ├─ destroyed.mp3        # 击毁敌机
   └─ die.mp3              # 死亡
```

### 换素材要注意什么

1. **格式**：PNG / JPG 都行（`pygame.image.load` 支持）；建议用带透明通道的 PNG。
2. **尺寸**：不用精确，代码会等比缩放到目标框内（飞船 60x44、敌机 48x48、子弹 6x12）。但源图太小会糊，建议源图边长 ≥ 128px。
3. **`boom.png` 必须是竖排 4 帧序列图**。换成单张图会导致 `load_explosion_frames()` 切出 4 个碎片。想换爆炸效果就自己拼一张 4 帧竖图。
4. **背景**：`began.png` 会被拉伸到 600x600，比例不对就会变形。
5. **仓库里有几张图没被代码用到**（`background_image*.png`、`beiy1/2.png`、`enemy21/31.png`、`explosion1..3.png`、`下载 (1).jpg`），是早期素材，留着当备份，不影响运行。

### 素材背景是画上去的棋盘格？

原始素材是从网页上截的图，所谓"透明背景"其实是烘焙进图片的灰白棋盘格。仓库里的飞船、子弹、爆炸、部分敌机已经用 `tools/clean_assets.py` 处理成真透明：

```bash
python tools/clean_assets.py game/img
```

脚本从图片四边做 8 邻域漫水填充，把与背景色接近且连通的像素 alpha 置 0；有深色描边的主体不会被吃掉。想处理别的图，把文件名加进脚本里的 `targets` 列表即可。

---

## 7. 常见问题

<details>
<summary><b>报错「没有找到 pygame」</b></summary>

依赖没装到当前解释器上。用仓库自带的方式跑最稳：

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
.venv/bin/python -m pip install -r requirements.txt           # macOS / Linux
```

确认解释器：`.venv\Scripts\python.exe -c "import pygame; print(pygame.version.ver)"`。
</details>

<details>
<summary><b>报错「缺少素材文件：...\game\img\xxx.png」</b></summary>

`game/` 目录不完整。这种情况下程序会直接告诉你缺哪个文件并退出，不会黑屏。重新拉一遍仓库，或把缺的文件补进对应目录。
</details>

<details>
<summary><b>没有声音 / 提示「音频设备不可用，游戏将静音运行」</b></summary>

说明 `pygame.mixer.init()` 失败了：可能是没有声卡（虚拟机、远程桌面）、音频服务没起来、或者被独占。游戏会自动静音继续跑，不影响操作。修好音频设备后重开即可。
</details>

<details>
<summary><b>按了 V，画面显示 MUTED 但音乐还在响？</b></summary>

静音是把所有 `Sound` 的音量设为 0，已经在播放的音频会立刻生效；如果背景乐是别的程序放的，那当然管不到。检查一下是不是开了音乐播放器。
</details>

<details>
<summary><b>报错里有 <code>pygame.font.SysFont ... TypeError: expected str ...</code></b></summary>

这是 pygame 2.6.x 在部分 Windows 上的已知问题：它会遍历注册表里的字体键，碰到非字符串值（某些软件写入的 DWORD）就崩。

本项目已经用 `safe_font()` 兜住了——字体枚举异常会自动回退到 pygame 内置字体，游戏能正常跑。如果你的**其它** pygame 项目也遇到，两种解法：

1. 升级/降级 pygame：`pip install "pygame==2.6.1"` 或 `pip install "pygame<2.6"`；
2. 打补丁：在 `pygame/sysfont.py` 的 `initsysfonts_win32()` 里，`_winreg.EnumValue` 之后加一句
   `if not isinstance(font, str): continue`。
</details>

<details>
<summary><b>窗口打开了但一片黑 / 闪一下就退</b></summary>

先跑无头自检看是代码问题还是显示问题：

```bash
python game.py --smoke-test 120
```

能出 `[smoke] 120 帧完成 ...` 说明逻辑没问题，问题在显示驱动（远程桌面、独显驱动、SDL 后端）。可以试 `set SDL_VIDEODRIVER=windows`（Windows）或 `export SDL_VIDEODRIVER=x11`（Linux）。
</details>

<details>
<summary><b>Linux 上 <code>pip install pygame</code> 报缺 SDL 头文件</b></summary>

用预编译 wheel 一般不需要系统库；确实要编译时：

```bash
sudo apt install -y python3-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
```
</details>

---

## 8. 想打包成 exe

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --add-data "game;game" --name AirplaneBattle game.py
```

产物在 `dist/AirplaneBattle/`。注意：

- Windows 上用 `;` 分隔 `--add-data`，macOS / Linux 用 `:`；
- `--windowed` 会隐藏控制台，此时 `[警告]` 提示看不到，排查问题先去掉它；
- 打包体积约 40–60 MB，主要是 SDL2 的 dll。

---

## 9. 已知限制

| 限制 | 说明 |
|---|---|
| 窗口固定 600x600 | 没有做分辨率适配，全屏/缩放都不支持 |
| 难度不递增 | 敌机速度、生成间隔是常量，玩久了难度不变 |
| 没有存档与排行榜 | 分数只存在内存里，退出即清零 |
| 部分敌机带原图背景 | `enemy1/2/4/5` 的源图是带场景背景的截图，抠不干净，显示为方形贴图 |
| 单文件结构 | 约 538 行塞在一个文件里，做关卡系统前值得先拆包 |
| 没有暂停菜单 | 暂停就是暂停，不提供「重新开始 / 回主菜单」 |
