"""
FinanceSim Launcher
Cross-platform launcher for backend and frontend
"""
import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Find Python
def find_python():
    candidates = []
    user = Path.home()
    for py_ver in ["python3.13", "python3.12", "python3.11", "python", "py"]:
        try:
            result = subprocess.run([py_ver, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return py_ver
        except FileNotFoundError:
            pass
    # Try common paths
    for path in [
        user / "AppData" / "Local" / "Programs" / "Python" / "Python313" / "python.exe",
        user / "AppData" / "Local" / "Programs" / "Python" / "Python312" / "python.exe",
        user / "AppData" / "Local" / "Programs" / "Python" / "Python311" / "python.exe",
    ]:
        if path.exists():
            return str(path)
    return None

PYTHON = find_python()
if not PYTHON:
    print("[ERROR] Python not found!")
    input("Press Enter to exit...")
    sys.exit(1)

print(f"[OK] Python: {PYTHON}")

# Find Node
def find_node():
    candidates = [
        r"C:\Program Files\nodejs\node.exe",
        Path.home() / ".workbuddy" / "binaries" / "node" / "versions" / "22.22.2-3" / "node.exe",
    ]
    for path in candidates:
        if isinstance(path, str):
            path = Path(path)
        if path.exists():
            return str(path)
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "node"
    except FileNotFoundError:
        pass
    return None

NODE = find_node()
if not NODE:
    print("[ERROR] Node.js not found!")
    input("Press Enter to exit...")
    sys.exit(1)

print(f"[OK] Node: {NODE}")

# PID tracking
PID_FILE = Path(os.environ.get("TEMP", "/tmp")) / "fs_pids.txt"


def save_pids(bp, fp):
    PID_FILE.write_text(f"{bp}\n{fp}\n")


def kill_pids():
    if PID_FILE.exists():
        try:
            lines = PID_FILE.read_text(encoding='utf-8', errors='ignore').strip().split("\n")
        except UnicodeDecodeError:
            lines = PID_FILE.read_text(encoding='gbk', errors='ignore').strip().split("\n")
        for line in lines:
            try:
                pid = int(line.strip())
                os.kill(pid, signal.SIGTERM)
            except (ValueError, ProcessLookupError, OSError):
                pass
        PID_FILE.unlink(missing_ok=True)
    # Also kill by process name
    subprocess.run(["taskkill", "/IM", "uvicorn.exe", "/T", "/F"], capture_output=True)
    subprocess.run(["taskkill", "/IM", "node.exe", "/F"], capture_output=True)


def check_deps_installed():
    """检查依赖是否已安装"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import aiosqlite
        print("[OK] Backend dependencies already installed")
        return True
    except ImportError as e:
        print(f"[WARN] Missing dependency: {e}")
        return False


def check_frontend_deps():
    """检查前端依赖是否已安装"""
    return (FRONTEND_DIR / "node_modules").exists()


def install_deps():
    """依赖检查（已安装则跳过）"""
    # 快速检查，不打印过多信息
    try:
        import fastapi, uvicorn, sqlalchemy, aiosqlite
        print("[OK] Backend ready")
    except ImportError:
        print("Installing backend deps...")
        subprocess.run(
            [PYTHON, "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt"), "-q"],
            capture_output=True
        )
    
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Installing frontend deps...")
        subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), capture_output=True)
        print("[OK] Frontend ready")
    else:
        print("[OK] Frontend ready")


def cleanup_invalid_packages():
    """Remove invalid package directories starting with ~"""
    import glob
    invalid_dirs = glob.glob(os.path.join(Path.home(), "AppData", "Local", "Programs", "Python", "Python*", "Lib", "site-packages", "~*"))
    for dir_path in invalid_dirs:
        try:
            import shutil
            shutil.rmtree(dir_path, ignore_errors=True)
            print(f"  Removed: {dir_path}")
        except:
            pass


def start_backend(host="127.0.0.1", background=True):
    """启动后端服务"""
    print(f"Starting backend (port 8000)...")
    cmd = [PYTHON, "-m", "uvicorn", "app.main:app", f"--host={host}", "--port=8000", "--log-level=warning"]
    
    # 不使用 --reload，避免后台运行时的问题
    if background:
        # 后台启动，重定向输出到日志文件
        log_file = PROJECT_ROOT / "backend.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            proc = subprocess.Popen(
                cmd,
                cwd=str(BACKEND_DIR),
                stdout=f,
                stderr=f,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )
        time.sleep(5)  # 等待后端完全启动
        
        # 检查进程是否还在运行
        if proc.poll() is None:
            print(f"Backend started successfully (PID: {proc.pid})")
            return proc.pid
        else:
            print(f"[ERROR] Backend failed to start. Check {log_file}")
            sys.exit(1)
    else:
        # 前台启动（用于调试）
        return subprocess.run(cmd, cwd=str(BACKEND_DIR)).returncode


def start_frontend(background=True):
    """启动前端服务"""
    print("Starting frontend (port 5173)...")
    
    # 使用完整路径或确保npm在PATH中
    npm_cmd = ["npm", "run", "dev"]
    
    if background:
        # 后台启动，重定向输出
        log_file = PROJECT_ROOT / "frontend.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            proc = subprocess.Popen(
                npm_cmd,
                cwd=str(FRONTEND_DIR),
                shell=True,
                stdout=f,
                stderr=f,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )
        time.sleep(5)  # 等待前端完全启动
        
        # 检查进程是否还在运行
        if proc.poll() is None:
            print(f"Frontend started successfully (PID: {proc.pid})")
            return proc.pid
        else:
            print(f"[ERROR] Frontend failed to start. Check {log_file}")
            sys.exit(1)
    else:
        # 前台启动
        return subprocess.run(npm_cmd, cwd=str(FRONTEND_DIR), shell=True).returncode


def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"


def check_status():
    import socket
    def is_listening(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        return result == 0
    return is_listening(8000), is_listening(5173)


def menu():
    while True:
        os.system("cls" if sys.platform == "win32" else "clear")
        print()
        print("========================================")
        print("   FinanceSim Control Panel")
        print("========================================")
        print()
        print("   [1] Start Local Server")
        print("   [2] Start LAN Access")
        print("   [3] Stop All Services")
        print("   [4] Check Status")
        print("   [5] Open Browser")
        print("   [6] Restart")
        print("   [0] Exit")
        print()
        be, fe = check_status()
        print(f"   Backend:  {'RUNNING' if be else 'STOPPED'}")
        print(f"   Frontend: {'RUNNING' if fe else 'STOPPED'}")
        print()
        choice = input("Choose [0-6]: ").strip()

        if choice == "1":
            install_deps()
            bp = start_backend()
            fp = start_frontend()
            save_pids(bp, fp)
            print()
            print("========================================")
            print("   http://localhost:5173")
            print("   API:  http://localhost:8000/api/v1")
            print("   Docs: http://localhost:8000/docs")
            print("========================================")
            print()
            input("Press Enter to return to menu...")
        elif choice == "2":
            install_deps()
            bp = start_backend("0.0.0.0")
            fp = start_frontend("0.0.0.0")
            save_pids(bp, fp)
            ip = get_local_ip()
            print()
            print("========================================")
            print(f"   Local:  http://localhost:5173")
            print(f"   LAN:    http://{ip}:5173")
            print(f"   API:    http://{ip}:8000/api/v1")
            print("   NOTE: Allow ports 8000/5173 in Firewall")
            print("========================================")
            print()
            input("Press Enter to return to menu...")
        elif choice == "3":
            print()
            print("Stopping all services...")
            kill_pids()
            print("Done.")
            print()
            input("Press Enter to return to menu...")
        elif choice == "4":
            os.system("cls" if sys.platform == "win32" else "clear")
            print()
            print("========================================")
            print("        Service Status")
            print("========================================")
            print()
            be, fe = check_status()
            print(f"   Backend (8000):  {'RUNNING' if be else 'STOPPED'}")
            print(f"   Frontend (5173): {'RUNNING' if fe else 'STOPPED'}")
            print()
            input("Press Enter to return to menu...")
        elif choice == "5":
            subprocess.run(["start", "", "http://localhost:5173"], shell=True if sys.platform == "win32" else False)
            time.sleep(1)
        elif choice == "6":
            print()
            print("Restarting...")
            kill_pids()
            time.sleep(1)
            install_deps()
            bp = start_backend()
            fp = start_frontend()
            save_pids(bp, fp)
            print()
            print("========================================")
            print("   http://localhost:5173")
            print("========================================")
            print()
            input("Press Enter to return to menu...")
        elif choice == "0":
            kill_pids()
            print()
            print("Done.")
            time.sleep(1)
            break
        else:
            print("Invalid choice.")
            time.sleep(1)


if __name__ == "__main__":
    menu()
