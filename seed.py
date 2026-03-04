#!/usr/bin/env python3
"""
seed.py — Willow Bootstrap
Plant this. Everything grows from here.

Usage: python seed.py
No dependencies required. Stdlib only.
"""

import os
import sys
import subprocess
import urllib.request
import urllib.error
import platform
import shutil
import time

WILLOW_PORTS = [2121, 8420]
WILLOW_REPO = "https://github.com/rudi193-cmd/willow-1.4"
WILLOW_DIR_NAME = "willow-1.4"
WILLOW_START = {
    "Windows": "willow-14.bat",
    "Darwin": "willow-14.sh",
    "Linux": "willow-14.sh",
}


# ── Decision 1 ────────────────────────────────────────────────────────────────

def check_running():
    """Is Willow already running on a known port?"""
    for port in WILLOW_PORTS:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/", timeout=2)
            return port
        except Exception:
            continue
    return None


# ── Decision 2 ────────────────────────────────────────────────────────────────

def find_local_repo():
    """Is there a Willow installation on this device?"""
    candidates = [
        os.getcwd(),
        os.path.join(os.getcwd(), WILLOW_DIR_NAME),
        os.path.join(os.path.expanduser("~"), WILLOW_DIR_NAME),
        os.path.join(os.path.expanduser("~"), "Documents", WILLOW_DIR_NAME),
        os.path.join(os.path.expanduser("~"), "Documents", "GitHub", WILLOW_DIR_NAME),
    ]
    for path in candidates:
        if os.path.isfile(os.path.join(path, "server.py")):
            return path
    return None


# ── Decision 3 ────────────────────────────────────────────────────────────────

def check_internet():
    """Is GitHub reachable?"""
    try:
        urllib.request.urlopen("https://github.com", timeout=5)
        return True
    except Exception:
        return False


def clone_willow(target_dir):
    """Clone the Willow repo."""
    if not shutil.which("git"):
        print("\n  ERROR: git is not installed.")
        print("  Install it at https://git-scm.com/downloads and try again.")
        return None

    print(f"\n  Cloning Willow into: {target_dir}")
    result = subprocess.run(
        ["git", "clone", WILLOW_REPO, target_dir],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ERROR: Clone failed.\n{result.stderr}")
        return None
    return target_dir


# ── Helpers ───────────────────────────────────────────────────────────────────

def consent(action):
    """Ask for explicit user consent. Returns True if granted."""
    print()
    answer = input(f"  May I {action}? [yes/no]: ").strip().lower()
    return answer in ("yes", "y")


def install_deps(path):
    req = os.path.join(path, "requirements.txt")
    req_base = os.path.join(path, "requirements.base.txt")
    target = req if os.path.isfile(req) else req_base if os.path.isfile(req_base) else None
    if target:
        print("  Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", target, "-q"], check=True)


def start_willow(path):
    system = platform.system()
    script = WILLOW_START.get(system, "willow-14.sh")
    script_path = os.path.join(path, script)

    if os.path.isfile(script_path):
        if system == "Windows":
            subprocess.Popen(["cmd", "/c", "start", script_path], cwd=path)
        else:
            subprocess.Popen(["bash", script_path], cwd=path)
    else:
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app",
             "--host", "0.0.0.0", "--port", "2121"],
            cwd=path
        )


def open_browser(port):
    url = f"http://localhost:{port}/"
    if platform.system() == "Windows":
        os.startfile(url)
    elif platform.system() == "Darwin":
        subprocess.run(["open", url])
    else:
        subprocess.run(["xdg-open", url])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("  Willow")
    print("  Plant this. Everything grows from here.")
    print()

    # Decision 1: Already running?
    port = check_running()
    if port:
        print(f"  Willow is running on port {port}.")
        print(f"  Opening http://localhost:{port}/")
        open_browser(port)
        return

    # Decision 2: Repo on device?
    local_path = find_local_repo()
    if local_path:
        print(f"  Found Willow at: {local_path}")
        if not consent("install dependencies and start Willow"):
            print("\n  Nothing installed. Goodbye.")
            return
        install_deps(local_path)
        start_willow(local_path)
        print("\n  Willow is starting...")
        time.sleep(4)
        open_browser(2121)
        return

    # Decision 3: Clone from GitHub
    print("  Willow is not installed on this device.")
    print()
    print("  To install, this script will:")
    print("    1. Clone Willow from GitHub")
    print("    2. Install Python dependencies")
    print("    3. Start the Willow server")
    print("    4. Open the sign-in page in your browser")
    print()
    print("  Your data stays on this machine.")
    print("  Consent is required every session.")
    print("  You can remove Willow at any time by deleting the folder.")

    if not consent("clone Willow from GitHub and install it on this device"):
        print("\n  Nothing installed. Goodbye.")
        return

    if not check_internet():
        print("\n  ERROR: No internet connection. Check your connection and try again.")
        return

    default_dir = os.path.join(os.path.expanduser("~"), "Documents", WILLOW_DIR_NAME)
    print(f"\n  Install location: {default_dir}")
    custom = input("  Press Enter to accept, or type a different path: ").strip()
    install_dir = custom if custom else default_dir

    if os.path.exists(install_dir):
        print(f"\n  Directory already exists: {install_dir}")
        print("  Remove it or choose a different location and try again.")
        return

    cloned = clone_willow(install_dir)
    if not cloned:
        return

    install_deps(cloned)
    start_willow(cloned)
    print("\n  Willow is starting...")
    time.sleep(4)
    open_browser(2121)


if __name__ == "__main__":
    main()
