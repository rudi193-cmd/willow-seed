#!/usr/bin/env python3
"""
seed.py — Willow Bootstrap
Plant this. Everything grows from here.

Usage:
  python seed.py                          # auto-detect or prompt for location
  python seed.py --target /path/to/dir   # skip detection, install here
Requires: Python 3.11+, stdlib only.
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

WILLOW_REPO     = "https://github.com/rudi193-cmd/willow-1.9"
WILLOW_DIR_NAME = "willow-1.9"

MIN_PYTHON = (3, 11)


# ── Output helpers ────────────────────────────────────────────────────────────

def hdr(text):
    print(f"\n─── {text} " + "─" * max(0, 52 - len(text)))

def ok(text):
    print(f"  ✓  {text}")

def warn(text):
    print(f"  ⚠  {text}")

def err(text):
    print(f"  ✗  {text}")

def info(text):
    print(f"     {text}")


# ── Returning user shortcut ───────────────────────────────────────────────────

def already_installed() -> Path | None:
    """If Willow is installed and version-pinned, return the willow-1.9 path."""
    version_file = Path.home() / ".willow" / "version"
    if not version_file.exists():
        return None
    candidates = [
        Path(__file__).parent / WILLOW_DIR_NAME,
        Path.home() / "Desktop" / WILLOW_DIR_NAME,
        Path.home() / "github" / WILLOW_DIR_NAME,
    ]
    for p in candidates:
        if (p / "willow.sh").exists():
            return p
    return None


# ── Prerequisite checks ───────────────────────────────────────────────────────

def check_python() -> bool:
    v = sys.version_info
    if v < MIN_PYTHON:
        err(f"Python {v.major}.{v.minor} — need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")
        return False
    ok(f"python3   ({v.major}.{v.minor}.{v.micro})")
    return True


def check_tool(name, display=None) -> bool:
    display = display or name
    path = shutil.which(name)
    if path:
        ok(f"{display:<10}{path}")
        return True
    warn(f"{display:<10}not found")
    return False


# ── Step 1: Get Willow ────────────────────────────────────────────────────────

def find_local_repo(forced_target: Path | None = None) -> Path | None:
    if forced_target:
        if (forced_target / "willow.sh").exists():
            return forced_target
        return None
    # Seed lives on Desktop — look next to it first, then common locations
    seed_dir = Path(__file__).parent
    candidates = [
        seed_dir / WILLOW_DIR_NAME,
        Path.home() / "Desktop" / WILLOW_DIR_NAME,
        Path.home() / "github" / WILLOW_DIR_NAME,
        Path.home() / WILLOW_DIR_NAME,
    ]
    for p in candidates:
        if (p / "willow.sh").exists():
            return p
    return None


def clone_willow(target: Path) -> bool:
    if not shutil.which("git"):
        err("git not found — install git and try again.")
        return False
    try:
        urllib.request.urlopen("https://github.com", timeout=5)
    except Exception:
        err("Cannot reach GitHub. Check your internet connection.")
        return False
    info(f"Cloning into: {target}")
    result = subprocess.run(
        ["git", "clone", WILLOW_REPO, str(target)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err(f"Clone failed:\n{result.stderr}")
        return False
    ok(f"Cloned to {target}")
    return True


def get_willow(forced_target: Path | None = None) -> Path | None:
    hdr("Step 1 — Get Willow")

    existing = find_local_repo(forced_target)
    if existing:
        ok(f"Found: {existing}")
        return existing

    # Default clone target: next to seed.py on Desktop
    default = Path(__file__).parent / WILLOW_DIR_NAME
    info(f"Willow not found. Install location: {default}")
    try:
        custom = input("     Press Enter to accept, or type a different path: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Interrupted.")
        return None
    target = Path(custom).expanduser() if custom else default

    if target.exists():
        err(f"Directory already exists: {target}")
        return None

    try:
        answer = input(f"  Clone Willow into {target}? [yes/no]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n  Interrupted.")
        return None
    if answer not in ("yes", "y"):
        return None

    return target if clone_willow(target) else None


# ── Handoff to root.py ────────────────────────────────────────────────────────

def handoff(willow_path: Path) -> None:
    print()
    print("─" * 56)
    print()
    print("  Willow is planted.  ΔΣ=42")
    print()

    root = willow_path / "root.py"
    if root.exists():
        print("  Handing off to root.py...")
        print()
        try:
            input("  Press Enter to continue, or Ctrl-C to stop.")
        except (KeyboardInterrupt, EOFError):
            print(f"\n  Stopped. Run when ready:\n    python3 {root}")
            return
        os.execv(sys.executable, [sys.executable, str(root)])
    else:
        print(f"  root.py not found at {root}")
        print(f"  Run manually:  python3 {willow_path}/root.py")
        print()


def handoff_dashboard(willow_path: Path) -> None:
    """Returning user — skip straight to dashboard."""
    candidates = [
        willow_path.parent / "willow-dashboard" / "dashboard.py",
        Path.home() / "github" / "willow-dashboard" / "dashboard.py",
    ]
    override = os.environ.get("WILLOW_DASHBOARD_PATH", "")
    if override:
        candidates.insert(0, Path(override))
    for p in candidates:
        if p.exists():
            os.execv(sys.executable, [sys.executable, str(p)])
    # Fallback: hand to root.py which will chain forward
    handoff(willow_path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main(forced_target: Path | None = None):
    print()
    print("  Willow")
    print("  Plant this. Everything grows from here.")
    print()
    print("─" * 56)

    # Returning user — skip install, go straight to dashboard
    installed = already_installed()
    if installed:
        ok(f"Willow {(Path.home() / '.willow' / 'version').read_text().strip()} installed at {installed}")
        print()
        handoff_dashboard(installed)
        return

    hdr("Prerequisites")

    if not check_python():
        print("\n  Python 3.11+ is required. Aborting.")
        sys.exit(1)

    if not check_tool("git"):
        print("\n  git is required to clone Willow.")
        print("  Install: https://git-scm.com/downloads")
        sys.exit(1)

    check_tool("gpg")
    check_tool("psql")

    willow_path = get_willow(forced_target)
    if willow_path is None:
        print("\n  Nothing installed. Goodbye.")
        sys.exit(0)

    handoff(willow_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Willow bootstrap installer")
    parser.add_argument("--target", type=Path, default=None,
                        help="Install path. Bypasses auto-detection.")
    args = parser.parse_args()
    main(args.target)
