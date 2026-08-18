@echo off
chcp 65001 >nul
title 外卖客服系统 - 全部启动

echo ============================================
echo   外卖客服系统  智能客服多Agent平台
echo ============================================
echo.
echo   ▸ 启动外卖后端 (Spring Boot)  端口 8080
echo   ▸ 启动 AI 客服   (FastAPI)     端口 8000
echo   ▸ 启动管理后台   (Vue Admin)   端口 8088
echo   ▸ 启动外卖 H5   (UniApp H5)    端口 8082
echo.
echo ============================================
echo.

set "BASE=D:\work\agent 外卖客服"
set "VENV=%BASE%\.venv\Scripts"

:: 把 venv 加到 PATH 最前面，之后直接用无空格的 python 命令
set "PATH=%VENV%;%PATH%"

:: 验证关键命令
echo [检查] mvn: & mvn --version 2>nul | find "Apache Maven" >nul && echo   OK || echo   X 未找到!
echo [检查] npm: & npm --version 2>nul >nul && echo   OK || echo   X 未找到!
echo [检查] python: & python --version 2>nul >nul && echo   OK || echo   X 未找到!
echo.

:: 1. 外卖后端 - mvn 不含空格，直接用
cd /d "%BASE%\-agent\外卖系统\sky-take-out\sky-server"
start "Backend-8080" cmd /k mvn spring-boot:run -Dspring-boot.run.profiles=dev

:: 2. AI客服 - python 不含空格，通过 PATH 找到 venv 里的
cd /d "%BASE%\-agent\python-impl"
start "AIChat-8000" cmd /k python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

:: 3. 管理后台 - npm 不含空格
cd /d "%BASE%\-agent\外卖系统\sky-take-out\web-sky-admin"
start "Admin-8088" cmd /k npm run serve

:: 4. 外卖H5 - npm 不含空格
cd /d "%BASE%\-agent\外卖系统\sky-take-out\web-sky-weixin-uniapp"
start "H5-8082" cmd /k npm run serve

echo   已启动 4 个服务窗口
echo.
echo ============================================
echo   访问地址:




echo   外卖后端 : http://localhost:8080/doc.html
echo   AI客服   : http://localhost:8000/docs
echo   管理后台 : http://localhost:8088
echo   外卖H5   : http://localhost:8082
echo ============================================
echo.
echo   按任意键关闭此窗口 ^(不影响已启动的服务^)
pause >nul