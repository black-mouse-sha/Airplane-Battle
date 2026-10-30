#!/usr/bin/env bash
# 一行启动：./run.sh
# 需要 Python 3.9+；Linux 上 pygame 的音频依赖 libsdl2 相关系统库
set -euo pipefail

cd "$(dirname "$0")"

PY=${PYTHON:-python3}
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "[错误] 没找到 $PY，请先安装 Python 3.9+" >&2
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "[1/2] 创建虚拟环境 .venv ..."
  "$PY" -m venv .venv
else
  echo "[1/2] 虚拟环境已存在。"
fi

echo "[2/2] 检查依赖 ..."
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt

echo "启动游戏 ... 方向键移动 / 空格射击 / B 暂停 / V 静音 / ESC 退出"
exec .venv/bin/python game.py "$@"
