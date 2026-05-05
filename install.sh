#!/usr/bin/env bash
# install.sh — Willow Grove tester install
# b17: WGIST2  ΔΣ=42
#
# Usage:
#   bash install.sh

set -euo pipefail

GROVE_REPO="https://github.com/rudi193-cmd/safe-app-willow-grove.git"
WILLOW_REPO="https://github.com/rudi193-cmd/willow-1.9.git"
GROVE_DB="grove_local"
DEFAULT_INSTALL_DIR="${HOME}/willow-grove"

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

command -v gpg  >/dev/null 2>&1 || fail "gpg not found — sudo apt install gnupg"
ok "gpg"

command -v psql     >/dev/null 2>&1 || fail "psql not found — sudo apt install postgresql"
command -v createdb >/dev/null 2>&1 || fail "createdb not found — sudo apt install postgresql"
if ! psql -lqt >/dev/null 2>&1; then
    fail "Cannot connect to Postgres — is it running? Try: sudo service postgresql start"
fi
ok "PostgreSQL"

# ── 2. Install location ───────────────────────────────────────────────────────

hdr "Install location"
read -rp "  Install to [${DEFAULT_INSTALL_DIR}]: " REPLY
INSTALL_DIR="${REPLY:-${DEFAULT_INSTALL_DIR}}"
mkdir -p "${INSTALL_DIR}"
ok "Using ${INSTALL_DIR}"

# ── 3. Clone repos ────────────────────────────────────────────────────────────

hdr "Cloning safe-app-willow-grove"
GROVE_DIR="${INSTALL_DIR}/safe-app-willow-grove"
if [[ -d "${GROVE_DIR}/.git" ]]; then
    info "Already cloned — pulling latest"
    git -C "${GROVE_DIR}" pull origin master --quiet
else
    git clone "${GROVE_REPO}" "${GROVE_DIR}" --quiet
fi
ok "safe-app-willow-grove ready"

hdr "Cloning willow-1.9"
WILLOW_DIR="${INSTALL_DIR}/willow-1.9"
if [[ -d "${WILLOW_DIR}/.git" ]]; then
    info "Already cloned — pulling latest"
    git -C "${WILLOW_DIR}" pull origin master --quiet
else
    git clone "${WILLOW_REPO}" "${WILLOW_DIR}" --quiet
fi
ok "willow-1.9 ready"

# ── 4. Python venv ────────────────────────────────────────────────────────────

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

# ── 5. Install dependencies ───────────────────────────────────────────────────

hdr "Installing dependencies"
"${PIP}" install -r "${GROVE_DIR}/requirements.txt" --quiet
"${PIP}" install -r "${WILLOW_DIR}/requirements.txt" --quiet
ok "Dependencies installed"

# ── 6. Database setup ─────────────────────────────────────────────────────────

hdr "Database setup"
if psql -lqt 2>/dev/null | grep -qw "${GROVE_DB}"; then
    info "Database '${GROVE_DB}' already exists — skipping create"
else
    createdb "${GROVE_DB}"
    ok "Created database ${GROVE_DB}"
fi
psql -d "${GROVE_DB}" -f "${GROVE_DIR}/schema.sql" -q
ok "Grove schema applied"

# ── 7. Willow setup (root.py) ─────────────────────────────────────────────────

hdr "Willow setup"
info "Running Sleipnir (root.py) — GPG key, vault, knowledge schema, PATH..."
WILLOW_PYTHON="${PYTHON}" "${PYTHON}" "${WILLOW_DIR}/root.py" --skip-socket
ok "Willow configured"

# ── 8. Provider / API key ─────────────────────────────────────────────────────

hdr "AI provider"
echo ""
echo "  Willow needs an AI provider to power @willow and the card builder."
echo ""
echo "  Options:"
echo "    1) Ollama — free, runs locally. Install: https://ollama.ai"
echo "    2) Anthropic (Claude) — paste your API key"
echo "    3) OpenAI (GPT) — paste your API key"
echo "    4) Gemini — paste your API key"
echo "    5) Skip — I'll set this up later with: willow providers enable <name> <key>"
echo ""
read -rp "  Choose [1-5]: " PROVIDER_CHOICE

case "${PROVIDER_CHOICE}" in
    1)
        if command -v ollama >/dev/null 2>&1; then
            ok "Ollama detected — it's already the default provider"
        else
            warn "Ollama not installed. Install from https://ollama.ai then run: ollama pull qwen2.5:3b"
        fi
        ;;
    2)
        read -rsp "  Anthropic API key: " API_KEY; echo ""
        if [[ -n "${API_KEY}" ]]; then
            WILLOW_PYTHON="${PYTHON}" WILLOW_PG_DB="willow_19" \
                "${WILLOW_DIR}/willow.sh" providers enable anthropic "${API_KEY}"
            ok "Anthropic provider enabled"
        fi
        ;;
    3)
        read -rsp "  OpenAI API key: " API_KEY; echo ""
        if [[ -n "${API_KEY}" ]]; then
            WILLOW_PYTHON="${PYTHON}" WILLOW_PG_DB="willow_19" \
                "${WILLOW_DIR}/willow.sh" providers enable openai "${API_KEY}"
            ok "OpenAI provider enabled"
        fi
        ;;
    4)
        read -rsp "  Gemini API key: " API_KEY; echo ""
        if [[ -n "${API_KEY}" ]]; then
            WILLOW_PYTHON="${PYTHON}" WILLOW_PG_DB="willow_19" \
                "${WILLOW_DIR}/willow.sh" providers enable gemini "${API_KEY}"
            ok "Gemini provider enabled"
        fi
        ;;
    *)
        info "Skipped. Run 'willow providers enable <name> <key>' when ready."
        ;;
esac

# ── 9. Display name ───────────────────────────────────────────────────────────

hdr "Your display name"
read -rp "  Display name in Grove (GROVE_SENDER) [$(whoami)]: " GROVE_SENDER
GROVE_SENDER="${GROVE_SENDER:-$(whoami)}"

# ── 10. Environment ───────────────────────────────────────────────────────────

SHELL_RC="${HOME}/.bashrc"
[[ "${SHELL:-}" == *zsh* ]] && SHELL_RC="${HOME}/.zshrc"

if grep -q "GROVE_SENDER" "${SHELL_RC}" 2>/dev/null; then
    info "Grove env vars already in ${SHELL_RC} — skipping"
else
    cat >> "${SHELL_RC}" << EOF

# Willow Grove (added by install.sh)
export WILLOW_PG_DB=${GROVE_DB}
export GROVE_SENDER=${GROVE_SENDER}
export WILLOW_ROOT=${WILLOW_DIR}
EOF
    ok "Env vars added to ${SHELL_RC}"
fi

# ── Done ──────────════════════════════════════════════════════════════════════

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
echo "  To change your AI provider later:"
echo "    willow providers list"
echo "    willow providers enable <name> <api_key>"
echo ""
echo "  Questions? Message Sean in Grove or open an issue on GitHub."
echo ""
