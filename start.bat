@echo off
echo ==========================================
echo 殡仪馆服务管理系统 - 启动脚本 (Windows)
echo ==========================================

if not exist .env (
    echo [INFO] .env 文件不存在，从 .env.example 复制...
    copy .env.example .env
)

echo [INFO] 检查虚拟环境...
if not exist venv (
    echo [INFO] 创建虚拟环境...
    python -m venv venv
)

echo [INFO] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [INFO] 安装依赖...
pip install -r requirements.txt

echo [INFO] 启动服务...
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
