import os
import time
import subprocess
import signal

# Simple file watcher that restarts `py app.py` whenever `app.py` changes.
# Run this from the project root.

SCRIPT = "app.py"
PY_LAUNCHER = "py"
POLL_INTERVAL = 0.5


def start_app():
    return subprocess.Popen([PY_LAUNCHER, SCRIPT])


def main():
    if not os.path.exists(SCRIPT):
        print(f"{SCRIPT} not found in current directory.")
        return

    last_mtime = os.path.getmtime(SCRIPT)
    proc = start_app()
    print(f"Started {SCRIPT} (pid={proc.pid})")

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            try:
                m = os.path.getmtime(SCRIPT)
            except FileNotFoundError:
                continue
            if m != last_mtime:
                last_mtime = m
                print(f"Change detected in {SCRIPT}, restarting...")
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()
                proc = start_app()
                print(f"Restarted {SCRIPT} (pid={proc.pid})")
    except KeyboardInterrupt:
        print("Watcher stopped by user, terminating app...")
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass


if __name__ == "__main__":
    main()
