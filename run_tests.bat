@echo off
echo ==========================================
echo 殡仪馆服务管理系统 - 测试脚本 (Windows)
echo ==========================================

if not exist venv (
    echo [ERROR] 虚拟环境不存在，请先运行 start.bat
    pause
    exit /b 1
)

echo [INFO] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [INFO] 运行测试...
pytest tests/ -v --tb=short --asyncio-mode=auto

echo.
echo ==========================================
echo 测试完成
echo ==========================================
pause
