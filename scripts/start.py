#!/usr/bin/env python3
"""FinanceSim Quick Start"""
import subprocess
import webbrowser
import time
import os
import sys

# 项目路径
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(BASE, "backend")
FRONTEND = os.path.join(BASE, "frontend")

print("=" * 50)
print("  FinanceSim Starting...")
print("=" * 50)
print()

# 启动后端
print("[1/3] Starting backend on port 8080...")
backend_cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8080"]
subprocess.Popen(
    backend_cmd,
    cwd=BACKEND,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

time.sleep(4)

# 启动前端
print("[2/3] Starting frontend on port 3000...")
if os.name == "nt":
    # Windows: 使用 cmd /c 来运行 npm
    frontend_cmd = 'cmd /c "npm run dev -- --port 3000"'
    subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
else:
    # Linux/Mac
    frontend_cmd = ["npm", "run", "dev", "--", "--port", "3000"]
    subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

time.sleep(5)

# 打开浏览器
print("[3/3] Opening browser...")
webbrowser.open("http://localhost:3000")

print()
print("=" * 50)
print("  SUCCESS!")
print("=" * 50)
print()
print("  Frontend: http://localhost:3000")
print("  Backend:  http://localhost:8080")
print("  API Docs: http://localhost:8080/docs")
print()
print("=" * 50)
print()
print("关闭此窗口不会停止服务。")
print("要停止服务，请关闭打开的两个终端窗口。")
print()
input("按 Enter 键退出...")
