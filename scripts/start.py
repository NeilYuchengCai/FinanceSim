#!/usr/bin/env python3
"""FinanceSim Quick Start - 快速启动脚本"""
import subprocess
import webbrowser
import time
import os
import sys

# 项目路径
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(BASE, "backend")
FRONTEND = os.path.join(BASE, "frontend")

# 端口配置
BACKEND_PORT = 8080
FRONTEND_PORT = 5173

print("=" * 60)
print("  FinanceSim - 金融市场模拟器")
print("=" * 60)
print()

# 启动后端
print(f"[1/3] 启动后端服务 (端口 {BACKEND_PORT})...")
backend_cmd = [sys.executable, "-m", "uvicorn", "app.main:app", 
               "--host", "127.0.0.1", "--port", str(BACKEND_PORT), 
               "--log-level", "warning"]
subprocess.Popen(
    backend_cmd,
    cwd=BACKEND,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

time.sleep(4)

# 启动前端
print(f"[2/3] 启动前端服务 (端口 {FRONTEND_PORT})...")
if os.name == "nt":
    frontend_cmd = f'cmd /c "npm run dev -- --port {FRONTEND_PORT}"'
    subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
else:
    frontend_cmd = ["npm", "run", "dev", "--", f"--port={FRONTEND_PORT}"]
    subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

time.sleep(5)

# 打开浏览器
print("[3/3] 打开浏览器...")
webbrowser.open(f"http://localhost:{FRONTEND_PORT}")

print()
print("=" * 60)
print("  ✓ 启动成功！")
print("=" * 60)
print()
print(f"  前端访问: http://localhost:{FRONTEND_PORT}")
print(f"  后端 API: http://localhost:{BACKEND_PORT}/api/v1")
print(f"  API文档:  http://localhost:{BACKEND_PORT}/docs")
print()
print("=" * 60)
print()
print("提示：")
print("  - 关闭此窗口不会停止服务")
print("  - 要停止服务，请关闭打开的两个终端窗口")
print("  - 按 Enter 键退出...")
print()
try:
    input()
except KeyboardInterrupt:
    pass
