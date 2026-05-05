#!/usr/bin/env bash
# install.sh — Willow Grove tester install
# b17: WGIST1  ΔΣ=42
#
# Usage:
#   bash install.sh               — Grove dashboard only (recommended for testers)
#   bash install.sh --with-mcp    — also install Willow MCP (for Claude Code users)

set -euo pipefail

GROVE_REPO="https://github.com/rudi193-cmd/safe-app-willow-grove.git"
WILLOW_REPO="https://github.com/rudi193-cmd/willow-1.9.git"
GROVE_DB="grove_local"
DEFAULT_INSTALL_DIR="${HOME}/willow-grove"
WITH_MCP=0

for arg in "$@"; do
    case $arg in
        --with-mcp) WITH_MCP=1 ;;
        *) ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────

hdr()  { echo ""; echo "─── $1 $(printf '─%.0s' $(seq 1 $((52 - ${#1}))))"; }
ok()   { echo "  ✓  $1"; }
warn() { echo "  ⚠  $1"; }
fail() { echo "  ✗  $1" >&2; exit 1; }
info() { echo "     $1"; }

# ── 1. Prerequisites ──────────────────────────────────────────────────────────

hdr "Checking prerequisites"

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "${PY_VER}" | cut -d. -f1)
PY_MINOR=$(echo "${PY_VER}" | cut -d. -f2)
if [[ "${PY_MAJOR}" -lt 3 || ( "${PY_MAJOR}" -eq 3 && "${PY_MINOR}" -lt 11 ) ]]; then
    fail "Python 3.11+ required (found ${PY_VER}) — https://python.org"
fi
ok "Python ${PY_VER}"

command -v git  >/dev/null 2>&1 || fail "git not found — sudo apt install git"
ok "git"

command -v psql >/dev/null 2>&1 || fail "psql not found — sudo apt install postgresql"
command -v createdb >/dev/null 2>&1 || fail "createdb not found — sudo apt install postgresql"

# Quick Postgres connectivity check
if ! psql -lqt >/dev/null 2>&1; then
    fail "Cannot connect to Postgres — is it running? Try: sudo service postgresql start"
fi
ok "PostgreSQL"

if [[ ${WITH_MCP} -eq 1 ]]; then
    command -v gpg >/dev/null 2>&1 || fail "gpg not found (required for --with-mcp) — sudo apt install gnupg"
    ok "gpg"
fi

# ── 2. Install location ───────────────────────────────────────────────────────

hdr "Install location"
read -rp "  Install to [${DEFAULT_INSTALL_DIR}]: " REPLY
INSTALL_DIR="${REPLY:-${DEFAULT_INSTALL_DIR}}"
mkdir -p "${INSTALL_DIR}"
ok "Using ${INSTALL_DIR}"

# ── 3. Clone safe-app-willow-grove ───────────────────────────────────────────

hdr "Cloning safe-app-willow-grove"
GROVE_DIR="${INSTALL_DIR}/safe-app-willow-grove"
if [[ -d "${GROVE_DIR}/.git" ]]; then
    info "Already cloned — pulling latest"
    git -C "${GROVE_DIR}" pull origin master --quiet
else
    git clone "${GROVE_REPO}" "${GROVE_DIR}" --quiet
fi
ok "safe-app-willow-grove ready"

# ── 4. Clone willow-1.9 (optional, for Claude Code + MCP) ───────────────────

WILLOW_DIR="${INSTALL_DIR}/willow-1.9"
if [[ ${WITH_MCP} -eq 1 ]]; then
    hdr "Cloning willow-1.9 (MCP server)"
    if [[ -d "${WILLOW_DIR}/.git" ]]; then
        info "Already cloned — pulling latest"
        git -C "${WILLOW_DIR}" pull origin master --quiet
    else
        git clone "${WILLOW_REPO}" "${WILLOW_DIR}" --quiet
    fi
    ok "willow-1.9 ready"
fi

# ── 5. Python venv ────────────────────────────────────────────────────────────

hdr "Python environment"
VENV="${HOME}/.willow-venv"
if [[ ! -x "${VENV}/bin/python3" ]]; then
    python3 -m venv "${VENV}"
    ok "Created venv at ${VENV}"
else
    ok "Reusing existing venv at ${VENV}"
fi
PYTHON="${VENV}/bin/python3"
PIP="${VENV}/bin/pip"

# ── 6. Install dependencies ───────────────────────────────────────────────────

hdr "Installing Grove dependencies"
"${PIP}" install -r "${GROVE_DIR}/requirements.txt" --quiet
ok "Grove dependencies installed"

if [[ ${WITH_MCP} -eq 1 ]]; then
    hdr "Installing Willow MCP dependencies"
    "${PIP}" install -r "${WILLOW_DIR}/requirements.txt" --quiet
    ok "Willow MCP dependencies installed"
fi

# ── 7. Database setup ─────────────────────────────────────────────────────────

hdr "Database setup"
if psql -lqt 2>/dev/null | grep -qw "${GROVE_DB}"; then
    info "Database '${GROVE_DB}' already exists — skipping create"
else
    createdb "${GROVE_DB}"
    ok "Created database ${GROVE_DB}"
fi

psql -d "${GROVE_DB}" -f "${GROVE_DIR}/schema.sql" -q
ok "Schema applied (idempotent — safe to re-run)"

# ── 8. Willow MCP setup (root.py) ─────────────────────────────────────────────

if [[ ${WITH_MCP} -eq 1 ]]; then
    hdr "Willow MCP setup"
    info "Running root.py (Sleipnir) — this sets up credentials, GPG, Postgres schema..."
    "${PYTHON}" "${WILLOW_DIR}/root.py" --skip-socket
    ok "Willow MCP configured"
fi

# ── 9. Configuration ──────────────────────────────────────────────────────────

hdr "Your display name"
read -rp "  Display name in Grove (GROVE_SENDER) [$(whoami)]: " GROVE_SENDER
GROVE_SENDER="${GROVE_SENDER:-$(whoami)}"

SHELL_RC="${HOME}/.bashrc"
if [[ "${SHELL:-}" == *zsh* ]]; then
    SHELL_RC="${HOME}/.zshrc"
fi

if grep -q "GROVE_SENDER" "${SHELL_RC}" 2>/dev/null; then
    info "Grove env vars already in ${SHELL_RC} — skipping"
else
    cat >> "${SHELL_RC}" << EOF

# Willow Grove (added by install.sh)
export WILLOW_PG_DB=${GROVE_DB}
export GROVE_SENDER=${GROVE_SENDER}
EOF
    ok "Env vars added to ${SHELL_RC}"
fi

# ── 10. MCP config for Claude Code (optional) ────────────────────────────────

if [[ ${WITH_MCP} -eq 1 ]]; then
    MCP_JSON="${GROVE_DIR}/.mcp.json"
    if [[ ! -f "${MCP_JSON}" ]]; then
        cat > "${MCP_JSON}" << EOF
{
  "mcpServers": {
    "willow": {
      "command": "${WILLOW_DIR}/willow.sh",
      "type": "stdio",
      "env": {
        "WILLOW_PYTHON": "${PYTHON}",
        "WILLOW_PG_DB": "willow_19"
      }
    }
  }
}
EOF
        ok "Claude Code MCP config written to ${MCP_JSON}"
        info "Open Claude Code in ${GROVE_DIR} to connect the MCP server."
    else
        info ".mcp.json already exists — skipping"
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  Willow Grove installed."
echo "══════════════════════════════════════════════════════════"
echo ""
echo "  Start the dashboard:"
echo ""
echo "    source ${SHELL_RC}"
echo "    cd ${GROVE_DIR}"
echo "    ${PYTHON} app.py"
echo ""
echo "  To connect to Sean (cross-instance messaging):"
echo ""
echo "    1. Install Tailscale: curl -fsSL https://tailscale.com/install.sh | sh"
echo "    2. Sean adds you to the network."
echo "    3. Run: ${PYTHON} grove_standalone.py"
echo "       Press F1 to see your address. Share it with Sean."
echo "    4. Incoming messages appear in #u2u-inbox."
echo ""
if [[ ${WITH_MCP} -eq 1 ]]; then
    echo "  To start the LAN command server:"
    echo "    ${PYTHON} ${GROVE_DIR}/grove_serve.py &"
    echo ""
fi
echo "  Questions? Message Sean in Grove or open an issue on GitHub."
echo ""
