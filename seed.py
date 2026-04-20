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
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WILLOW_REPO     = "https://github.com/rudi193-cmd/willow-1.7"
WILLOW_DIR_NAME = "willow-1.7"
VENV_PATH       = Path.home() / ".willow-venv"

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


# ── Consent gate ──────────────────────────────────────────────────────────────

def consent(action):
    """Ask for explicit consent. Returns True only if the user types yes/y."""
    print()
    try:
        answer = input(f"  May I {action}? [yes/no]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n  Interrupted. Nothing installed.")
        sys.exit(0)
    return answer in ("yes", "y")


# ── Prerequisite checks ───────────────────────────────────────────────────────

def check_python():
    v = sys.version_info
    if v < MIN_PYTHON:
        err(f"Python {v.major}.{v.minor} — need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")
        return False
    ok(f"python3   ({v.major}.{v.minor}.{v.micro})")
    return True


def check_tool(name, display=None):
    display = display or name
    path = shutil.which(name)
    if path:
        ok(f"{display:<10}{path}")
        return True
    warn(f"{display:<10}not found")
    return False


def check_gpg_key():
    """Return the first available secret key fingerprint, or None."""
    try:
        result = subprocess.run(
            ["gpg", "--list-secret-keys", "--with-colons"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if line.startswith("fpr:"):
                return line.split(":")[9]
    except Exception:
        pass
    return None


def check_postgres():
    """Return True if psql can connect to the local socket."""
    try:
        result = subprocess.run(
            ["psql", "-d", "postgres", "-c", "SELECT 1;"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# ── Step 1: Get Willow ────────────────────────────────────────────────────────

def find_local_repo():
    candidates = [
        Path.cwd() / WILLOW_DIR_NAME,
        Path.home() / "github" / WILLOW_DIR_NAME,
        Path.home() / WILLOW_DIR_NAME,
        Path.home() / "Documents" / WILLOW_DIR_NAME,
        Path.home() / "Documents" / "GitHub" / WILLOW_DIR_NAME,
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


def step_get_willow(forced_target: Path | None = None) -> Path | None:
    hdr("Step 1 — Get Willow")

    # --target bypasses detection entirely
    if forced_target is not None:
        if (forced_target / "willow.sh").exists():
            ok(f"Using existing installation: {forced_target}")
            return forced_target
        if forced_target.exists():
            err(f"Directory exists but doesn't look like willow-1.7: {forced_target}")
            return None
        if not consent(f"clone Willow from GitHub into {forced_target}"):
            return None
        return forced_target if clone_willow(forced_target) else None

    existing = find_local_repo()
    if existing:
        ok(f"Found existing installation: {existing}")
        return existing

    info("Willow is not installed on this device.")
    default = Path.home() / "github" / WILLOW_DIR_NAME
    print(f"\n     Install location: {default}")
    try:
        custom = input("     Press Enter to accept, or type a different path: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Interrupted.")
        return None
    target = Path(custom).expanduser() if custom else default

    if target.exists():
        err(f"Directory already exists: {target}")
        info("Remove it or choose a different location.")
        return None

    if not consent(f"clone Willow from GitHub into {target}"):
        return None

    return target if clone_willow(target) else None


# ── Step 2: Python venv ───────────────────────────────────────────────────────

def step_venv(willow_path: Path) -> bool:
    hdr("Step 2 — Python environment")

    python = sys.executable

    if VENV_PATH.exists():
        ok(f"venv exists: {VENV_PATH}")
    else:
        if not consent(f"create a virtual environment at {VENV_PATH}"):
            warn("Skipped. You can create it manually:")
            info(f"  python3 -m venv {VENV_PATH}")
            return False
        result = subprocess.run([python, "-m", "venv", str(VENV_PATH)])
        if result.returncode != 0:
            err("venv creation failed.")
            return False
        ok(f"Created {VENV_PATH}")

    venv_pip = VENV_PATH / "bin" / "pip"
    req = willow_path / "requirements.txt"

    if not req.exists():
        warn(f"requirements.txt not found at {req} — skipping install")
        return True

    if not consent("install Python packages from requirements.txt"):
        warn("Skipped. Install manually:")
        info(f"  {venv_pip} install -r {req}")
        return True

    info("Installing packages (this may take a minute)...")
    result = subprocess.run(
        [str(venv_pip), "install", "-r", str(req), "-q"]
    )
    if result.returncode != 0:
        err("Package install failed. Try manually:")
        info(f"  {venv_pip} install -r {req}")
        return False
    ok("Packages installed")
    return True


# ── Step 3: Postgres ──────────────────────────────────────────────────────────

def step_postgres(willow_path: Path) -> bool:
    hdr("Step 3 — Postgres")

    if not shutil.which("psql"):
        warn("psql not found — skipping database setup.")
        info("Install Postgres: https://www.postgresql.org/download/")
        info("Then run:  psql -d willow -f " + str(willow_path / "schema.sql"))
        return False

    if not check_postgres():
        warn("Postgres is not running or peer auth is not configured.")
        info("Start Postgres and ensure your Unix user can connect without a password.")
        info("Then run:  psql -d willow -f " + str(willow_path / "schema.sql"))
        return False

    # Check if willow DB exists
    result = subprocess.run(
        ["psql", "-d", "postgres", "-tAc", "SELECT 1 FROM pg_database WHERE datname='willow';"],
        capture_output=True, text=True
    )
    db_exists = result.stdout.strip() == "1"

    if db_exists:
        ok("'willow' database exists")
    else:
        if not consent("create a 'willow' Postgres database"):
            warn("Skipped. Create manually:  createdb willow")
            return False
        result = subprocess.run(["createdb", "willow"], capture_output=True, text=True)
        if result.returncode != 0:
            err(f"createdb failed: {result.stderr.strip()}")
            return False
        ok("Created 'willow' database")

    schema = willow_path / "schema.sql"
    if not schema.exists():
        warn(f"schema.sql not found at {schema}")
        return False

    if not consent("install the Willow schema (tables, indexes)"):
        warn("Skipped. Install manually:")
        info(f"  psql -d willow -f {schema}")
        return False

    result = subprocess.run(
        ["psql", "-d", "willow", "-f", str(schema)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err(f"Schema install failed: {result.stderr.strip()}")
        return False
    ok("Schema installed")
    return True


# ── Step 4: Credentials ───────────────────────────────────────────────────────

def step_credentials(willow_path: Path):
    hdr("Step 4 — API keys")

    creds = willow_path / "credentials.json"
    example = willow_path / "credentials.json.example"

    if creds.exists():
        ok(f"credentials.json exists: {creds}")
    else:
        if example.exists():
            shutil.copy2(example, creds)
            ok(f"Copied credentials.json.example → credentials.json")
        else:
            warn("credentials.json.example not found — skipping")
            return

    print()
    info("Willow uses free-tier cloud LLMs as a fallback when local models")
    info("are not available. Groq, Cerebras, and SambaNova all offer free tiers:")
    print()
    info("  Groq:       https://console.groq.com/keys")
    info("  Cerebras:   https://cloud.cerebras.ai")
    info("  SambaNova:  https://cloud.sambanova.ai")
    print()
    info(f"Add your keys to: {creds}")


# ── Step 5: SAFE ──────────────────────────────────────────────────────────────

def step_safe(willow_path: Path) -> str | None:
    """Create the SAFE root directory. Returns safe_root path on success, None on skip."""
    hdr("Step 5 — SAFE authorization")

    # Co-locate SAFE with the Willow partition if installing there,
    # otherwise fall back to the canonical partition default.
    partition_safe = str(Path.home() / "SAFE" / "Applications")
    safe_root = os.environ.get("WILLOW_SAFE_ROOT", partition_safe)

    info("The SAFE root is where signed app manifests live.")
    info(f"Default location: {safe_root}")
    print()

    if not shutil.which("gpg"):
        warn("gpg not found. Install it: sudo apt install gnupg")
        info("After installing gpg and creating a key, re-run seed.py.")
        return None

    key = check_gpg_key()
    if not key:
        warn("No GPG secret key found in your keyring.")
        info("Create one:  gpg --full-generate-key")
        info("Then re-run seed.py.")
        return None

    ok(f"GPG key: {key}")

    safe_path = Path(safe_root)
    if not safe_path.exists():
        if not consent(f"create SAFE root at {safe_root}"):
            warn("Skipped. Set WILLOW_SAFE_ROOT and re-run.")
            return None
        safe_path.mkdir(parents=True, exist_ok=True)
        ok(f"Created: {safe_root}")
    else:
        ok(f"SAFE root exists: {safe_root}")

    scaffold = willow_path / "tools" / "safe-scaffold.sh"
    if not scaffold.exists():
        warn(f"safe-scaffold.sh not found at {scaffold}")
        return None

    ok("SAFE root ready")
    return safe_root


# ── Step 6: Claude Code MCP config ───────────────────────────────────────────

def step_mcp(willow_path: Path, safe_root: str | None):
    hdr("Step 6 — Claude Code MCP")

    # Prefer the pipx-installed willow-mcp binary; fall back to willow.sh
    willow_mcp_bin = shutil.which("willow-mcp") or str(
        Path.home() / ".local" / "bin" / "willow-mcp"
    )

    # Install willow-mcp if not present
    if not shutil.which("willow-mcp"):
        info("willow-mcp not found. Attempting install via pipx...")
        if shutil.which("pipx"):
            result = subprocess.run(["pipx", "install", "willow-mcp"], capture_output=True, text=True)
            if result.returncode == 0:
                ok("Installed willow-mcp via pipx")
                willow_mcp_bin = shutil.which("willow-mcp") or willow_mcp_bin
            else:
                warn("pipx install failed. Falling back to willow.sh.")
                willow_mcp_bin = str(willow_path / "willow.sh")
        else:
            warn("pipx not found. Falling back to willow.sh.")
            willow_mcp_bin = str(willow_path / "willow.sh")

    store_root = str(Path.home() / ".willow" / "store")
    mcp_env = {
        "WILLOW_STORE_ROOT": store_root,
    }
    if safe_root:
        mcp_env["SAP_SAFE_ROOT"] = safe_root
        key = check_gpg_key()
        if key:
            mcp_env["SAP_PGP_FINGERPRINT"] = key

    mcp_entry = {
        "willow": {
            "command": willow_mcp_bin,
            "env": mcp_env,
        }
    }

    project_mcp_path = willow_path / ".mcp.json"

    print()
    info(f"MCP server: {willow_mcp_bin}")
    info(f"Store root: {store_root}")
    if safe_root:
        info(f"SAFE root:  {safe_root}")
    print()

    if not project_mcp_path.exists():
        if consent(f"write .mcp.json to {project_mcp_path}"):
            project_mcp_path.write_text(
                json.dumps({"mcpServers": mcp_entry}, indent=2) + "\n"
            )
            ok(f"Written: {project_mcp_path}")
    else:
        ok(f".mcp.json exists: {project_mcp_path}")

    # Print snippet for other projects
    print()
    info("Use the same .mcp.json in any project repo to connect to Willow:")
    print(json.dumps({"mcpServers": mcp_entry}, indent=2))


# ── Step 7: SAFE app registration ────────────────────────────────────────────

def step_register_apps(willow_path: Path, safe_root: str):
    hdr("Step 7 — Register system apps")

    scaffold = willow_path / "tools" / "safe-scaffold.sh"
    if not scaffold.exists():
        warn(f"safe-scaffold.sh not found — skipping app registration")
        return

    # Core system entries every install needs
    apps = [
        ("willow",           "operator", "Willow core system node"),
        ("heimdallr",        "operator", "Watchman — Claude Code CLI in willow-1.7"),
        ("willow-dashboard", "operator", "Terminal dashboard — system entry point"),
    ]

    env = {**os.environ, "WILLOW_SAFE_ROOT": safe_root}

    for app_id, agent_type, description in apps:
        app_dir = Path(safe_root) / app_id
        if app_dir.exists():
            ok(f"Already registered: {app_id}")
            continue
        result = subprocess.run(
            ["bash", str(scaffold), app_id, agent_type, description],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            ok(f"Registered: {app_id}")
        else:
            err(f"Failed to register {app_id}: {result.stderr.strip()[:100]}")


# ── Summary ───────────────────────────────────────────────────────────────────

def summary(willow_path: Path):
    print()
    print("─" * 56)
    print()
    print("  Willow is planted.  ΔΣ=42")
    print()
    print("  Next:")
    print(f"    ./willow.sh status       (health check)")
    print(f"    ./willow.sh verify       (SAFE manifest audit)")
    print(f"    ./willow.sh              (start MCP server)")
    print()
    print("  Then launch the dashboard:")
    print(f"    cd ~/github/willow-dashboard")
    print(f"    python3 dashboard.py")
    print()
    print("  Install apps from the dashboard — no manual setup needed.")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main(forced_target: Path | None = None):
    print()
    print("  Willow")
    print("  Plant this. Everything grows from here.")
    print()
    print("─" * 56)

    hdr("Prerequisites")

    python_ok = check_python()
    if not python_ok:
        print("\n  Python 3.11+ is required. Aborting.")
        sys.exit(1)

    has_git  = check_tool("git")
    has_gpg  = check_tool("gpg")
    has_psql = check_tool("psql", "psql")

    if not has_git:
        print("\n  git is required to clone Willow.")
        print("  Install: https://git-scm.com/downloads")
        sys.exit(1)

    if not has_gpg:
        warn("gpg not found — SAFE authorization step will be skipped.")
        info("Install:  sudo apt install gnupg   (or brew install gnupg on macOS)")

    if not has_psql:
        warn("psql not found — Postgres setup step will be skipped.")
        info("Install:  https://www.postgresql.org/download/")

    # Step 1: Get Willow
    willow_path = step_get_willow(forced_target)
    if willow_path is None:
        print("\n  Nothing installed. Goodbye.")
        sys.exit(0)

    # Step 2: venv
    step_venv(willow_path)

    # Step 3: Postgres
    if has_psql:
        step_postgres(willow_path)
    else:
        hdr("Step 3 — Postgres")
        warn("Skipped (psql not found)")
        info(f"When Postgres is available:  psql -d willow -f {willow_path / 'schema.sql'}")

    # Step 4: Credentials
    step_credentials(willow_path)

    # Step 5: SAFE
    safe_root = None
    if has_gpg:
        safe_root = step_safe(willow_path)
    else:
        hdr("Step 5 — SAFE authorization")
        warn("Skipped (gpg not found)")
        info("Install gpg then re-run seed.py to create the SAFE root.")

    # Step 6: Claude Code MCP
    step_mcp(willow_path, safe_root)

    # Step 7: Register system apps
    if safe_root:
        step_register_apps(willow_path, safe_root)
    else:
        hdr("Step 7 — Register system apps")
        warn("Skipped (no SAFE root)")

    # Summary
    summary(willow_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Willow bootstrap installer")
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Install path. Bypasses auto-detection. Use this when planting on a specific partition.",
    )
    args = parser.parse_args()
    main(args.target)
