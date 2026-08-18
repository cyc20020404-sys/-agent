#!/usr/bin/env python3
"""外卖客服系统 - 一键启动所有服务"""
import subprocess
import sys
import os
import time

# 强制 UTF-8 输出，避免 CMD GBK 编码报错
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = r"D:\work\agent 外卖客服"
VENV = os.path.join(BASE, ".venv", "Scripts")

services = [
    {
        "name": "外卖后端-8080",
        "cwd": os.path.join(BASE, "-agent", "外卖系统", "sky-take-out", "sky-server"),
        "cmd": ["mvn", "spring-boot:run", "-Dspring-boot.run.profiles=dev"],
        "url": "http://localhost:8080/doc.html",
    },
    {
        "name": "AI客服-8000",
        "cwd": os.path.join(BASE, "-agent", "python-impl"),
        "cmd": [
            os.path.join(VENV, "python.exe"),
            "-m", "uvicorn", "api.main:app",
            "--host", "0.0.0.0", "--port", "8000", "--reload",
        ],
        "url": "http://localhost:8000/docs",

    },
    {
        "name": "管理后台-8088",
        "cwd": os.path.join(BASE, "-agent", "外卖系统", "sky-take-out", "web-sky-admin"),
        "cmd": ["npm", "run", "serve"],
        "url": "http://localhost:8088",
    },
    {
        "name": "外卖H5-8082",
        "cwd": os.path.join(BASE, "-agent", "外卖系统", "sky-take-out", "web-sky-weixin-uniapp"),
        "cmd": ["npm", "run", "serve"],
        "url": "http://localhost:8082",
    },
]

def main():
    print("=" * 44)
    print("  外卖客服系统  智能客服多Agent平台")
    print("=" * 44)
    print()

    for s in services:
        print(f"  ▸ 启动 {s['name']:20s}  → {s['url']}")

    print()
    print("=" * 44)
    print()

    processes = []
    for s in services:




        print(f"[{s['name']}] 正在启动...")
        try:
            p = subprocess.Popen(
                s["cmd"],

                cwd=s["cwd"],
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            processes.append((s["name"], p))
            print(f"  ✓ 已启动 (PID={p.pid})")
        except Exception as e:
            print(f"  ✗ 启动失败: {e}")

    print()
    print("=" * 44)
    print("  访问地址:")
    for s in services:
        print(f"  {s['name']:20s}  {s['url']}")
    print("=" * 44)
    print()
    print("所有服务窗口已打开，关闭此窗口不影响运行中的服务。")
    input("按 Enter 退出...")





if __name__ == "__main__":
    main()