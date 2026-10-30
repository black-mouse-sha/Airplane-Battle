@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   飞机大战 - 一键启动
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 没找到 python。请先安装 Python 3.9+ 并勾选 "Add to PATH"。
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] 首次运行，正在创建虚拟环境 .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败。
        pause
        exit /b 1
    )
) else (
    echo [1/2] 虚拟环境已存在。
)

echo [2/2] 检查依赖 ...
.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，试试换源：
    echo    .venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
    exit /b 1
)

echo 启动游戏 ... 方向键移动 / 空格射击 / B 暂停 / V 静音 / ESC 退出
.venv\Scripts\python.exe game.py
set code=%errorlevel%
if not "%code%"=="0" pause
exit /b %code%
