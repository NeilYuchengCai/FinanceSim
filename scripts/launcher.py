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
        lines = PID_FILE.read_text().strip().split("\n")
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


def install_deps():
    print("Installing dependencies...")
    subprocess.run([PYTHON, "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt"), "-q"], check=False)
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Installing frontend deps...")
        subprocess.run(["npm", "install", "--silent"], cwd=str(FRONTEND_DIR), check=False)
    print("Done.")


def start_backend(host="127.0.0.1"):
    print(f"Starting backend (port 8000, host={host})...")
    cmd = [PYTHON, "-m", "uvicorn", "app.main:app", "--reload", f"--host={host}", "--port=8000", "--log-level=info"]
    proc = subprocess.Popen(cmd, cwd=str(BACKEND_DIR), creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
    time.sleep(3)
    return proc.pid


def start_frontend(host=None):
    print("Starting frontend (port 5173)...")
    cmd = ["npm", "run", "dev"]
    if host:
        cmd.extend(["--", "--host", "0.0.0.0"])
    proc = subprocess.Popen(cmd, cwd=str(FRONTEND_DIR), creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
    time.sleep(4)
    return proc.pid


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
