"""Phase 1 check: verify headroom is installed and its proxy can start.

Run from the repo root:  python -m src.check_headroom
"""

import shutil
import socket
import subprocess
import sys
import time

from src.config import load_config

STARTUP_TIMEOUT_SECONDS = 30


def port_is_open(port: int) -> bool:
    """Return True if something is listening on localhost:port."""
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def check_installed() -> bool:
    """Step 1: is the headroom CLI on PATH?"""
    if shutil.which("headroom") is None:
        print("FAIL  headroom CLI not found. Activate the venv and run: pip install -r requirements.txt")
        return False
    print("OK    headroom CLI found.")
    return True


def run_doctor(port: int) -> bool:
    """Run `headroom doctor`. It needs the proxy running, so call it after the proxy is up."""
    result = subprocess.run(["headroom", "doctor", "--port", str(port)], capture_output=True, text=True)
    print(result.stdout + result.stderr)
    # doctor exit codes: 0 healthy, 1 warnings only, 2 at least one failure
    if result.returncode >= 2:
        print("FAIL  `headroom doctor` reported failures (see output above).")
        return False
    print("OK    `headroom doctor` passed (warnings about wrapping other tools are fine).")
    return True


def check_proxy(port: int) -> bool:
    """Step 2: start the headroom proxy, wait for the port, run doctor, then stop it."""
    if port_is_open(port):
        print(f"FAIL  port {port} is already in use. Change headroom.proxy_port in config.yaml.")
        return False

    proc = subprocess.Popen(
        ["headroom", "proxy", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + STARTUP_TIMEOUT_SECONDS
        while time.time() < deadline:
            if proc.poll() is not None:
                print("FAIL  proxy exited early. Try `headroom proxy` manually to see the error.")
                return False
            if port_is_open(port):
                print(f"OK    headroom proxy started on port {port}.")
                return run_doctor(port)
            time.sleep(0.5)
        print(f"FAIL  proxy did not open port {port} within {STARTUP_TIMEOUT_SECONDS}s.")
        return False
    finally:
        proc.terminate()
        proc.wait()


def main() -> int:
    port = load_config()["headroom"]["proxy_port"]
    if not check_installed():
        return 1
    return 0 if check_proxy(port) else 1


if __name__ == "__main__":
    sys.exit(main())
