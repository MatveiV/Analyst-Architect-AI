"""Start both backend and frontend services as persistent processes."""
import os, sys, subprocess, time, socket, signal

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_BUILD = os.path.join(ROOT, "frontend", "build")

PID_DIR = os.path.join(ROOT, ".pids")
os.makedirs(PID_DIR, exist_ok=True)


def port_open(port, host="127.0.0.1"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        return True
    except:
        return False
    finally:
        s.close()


def start_backend():
    print("Starting backend (uvicorn :8000)...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    with open(os.path.join(PID_DIR, "backend.pid"), "w") as f:
        f.write(str(proc.pid))
    # Wait up to 60s for startup
    for _ in range(12):
        time.sleep(5)
        if port_open(8000):
            print(f"  Backend ready (pid={proc.pid})")
            return True
    print("  Backend failed to start in 60s")
    return False


def start_frontend():
    if not os.path.isdir(FRONTEND_BUILD):
        print(f"  Frontend build not found at {FRONTEND_BUILD}")
        return False
    print("Starting frontend (http.server :3000)...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3000", "--bind", "127.0.0.1"],
        cwd=FRONTEND_BUILD,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    with open(os.path.join(PID_DIR, "frontend.pid"), "w") as f:
        f.write(str(proc.pid))
    for _ in range(6):
        time.sleep(2)
        if port_open(3000):
            print(f"  Frontend ready (pid={proc.pid})")
            return True
    print("  Frontend failed to start")
    return False


def stop_all():
    for name in ("backend", "frontend"):
        pid_file = os.path.join(PID_DIR, f"{name}.pid")
        if os.path.isfile(pid_file):
            with open(pid_file) as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Stopped {name} (pid={pid})")
            except ProcessLookupError:
                print(f"{name} (pid={pid}) already stopped")
            os.remove(pid_file)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        stop_all()
        sys.exit(0)

    print(f"Starting services for {ROOT}")
    ok_b = start_backend()
    if not ok_b:
        print("Backend failed — aborting")
        sys.exit(1)
    ok_f = start_frontend()
    if not ok_f:
        print("Frontend build missing or failed — backend only on :8000")
    print("\nDone. Open http://localhost:3000 in your browser.")
    print("Run 'python start.py stop' to stop services.")
