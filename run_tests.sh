#!/bin/bash
echo "=========================================="
echo "殡仪馆服务管理系统 - 测试脚本 (Linux/Mac)"
echo "=========================================="

if [ ! -d venv ]; then
    echo "[ERROR] 虚拟环境不存在，请先运行 start.sh"
    exit 1
fi

echo "[INFO] 激活虚拟环境..."
source venv/bin/activate

echo "[INFO] 运行测试..."
pytest tests/ -v --tb=short --asyncio-mode=auto

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
