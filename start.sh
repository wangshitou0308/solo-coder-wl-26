#!/bin/bash
echo "=========================================="
echo "殡仪馆服务管理系统 - 启动脚本 (Linux/Mac)"
echo "=========================================="

if [ ! -f .env ]; then
    echo "[INFO] .env 文件不存在，从 .env.example 复制..."
    cp .env.example .env
fi

echo "[INFO] 检查虚拟环境..."
if [ ! -d venv ]; then
    echo "[INFO] 创建虚拟环境..."
    python3 -m venv venv
fi

echo "[INFO] 激活虚拟环境..."
source venv/bin/activate

echo "[INFO] 安装依赖..."
pip install -r requirements.txt

echo "[INFO] 启动服务..."
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
