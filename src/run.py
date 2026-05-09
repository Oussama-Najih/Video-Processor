import os
import sys
import signal
import subprocess
import time

from utils.main import clear
from utils.main import consumer

id = "36"


CONTAINER_NAME="nsfw_detect_service"
SERVICES = [
    ("thumbnail", ["python3", "-u", "-m", "src.thumbnail_service"]),
    ("transcode", ["python3", "-u", "-m", "src.transcode_service"]),
    ("nsfw",      ["python3", "-u", "-m", "src.nsfw_service"]),
]

procs = []
stopping = False

def start_services():
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    for name, cmd in SERVICES:
        print(f"[LAUNCHER] Starting {name}: {' '.join(cmd)}")
        p = subprocess.Popen(cmd, env=env, stdout=sys.stdout, stderr=sys.stderr)
        procs.append((name, p))
        time.sleep(0.2)

    print("[LAUNCHER] All services started.")

def stop_services(sig=None, frame=None):
    global stopping
    if stopping:
        return
    stopping = True

    print(f"\n[LAUNCHER] Stopping services (signal={sig})...")

    for name, p in procs:
        if p.poll() is None:
            print(f"[LAUNCHER] Sending SIGINT to {name} (pid={p.pid})")
            p.send_signal(signal.SIGINT)

    deadline = time.time() + 15
    for name, p in procs:
        if p.poll() is None:
            try:
                p.wait(timeout=max(0, deadline - time.time()))
            except subprocess.TimeoutExpired:
                print(f"[LAUNCHER] Killing {name} (pid={p.pid})")
                p.kill()
    
    clear()
    print("[NSFW] Shutting down Docker container...")
    subprocess.run(["docker", "stop", CONTAINER_NAME])

    clear()


    print("[LAUNCHER] Done.")
    sys.exit(0)

def monitor():
    while True:
        for name, p in procs:
            code = p.poll()
            if code is not None and not stopping:
                print(f"[LAUNCHER] Service '{name}' exited unexpectedly with code {code}. Stopping all.")
                stop_services()
        time.sleep(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop_services)
    signal.signal(signal.SIGTERM, stop_services)

    start_services()
    monitor()