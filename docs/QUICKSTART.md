# Willow Seed — Quickstart

## What You're Getting

A local-first AI infrastructure node. No cloud. No exposed ports. Your data stays on your machine.

When planted, Willow gives Claude Code 44 tools: persistent knowledge, structured memory, local inference, task dispatch, and file intake — all over a direct stdio connection.

---

## The Fastest Path

```bash
python seed.py
```

That's it. The script walks you through every step with explicit consent gates. Nothing happens without a `yes`.

What it does:
1. Clones `willow-1.7` from GitHub
2. Creates a Python venv at `~/.willow-venv`
3. Installs packages
4. Creates a `willow` Postgres database and installs the schema
5. Sets up your `credentials.json`
6. Scaffolds your first SAFE agent entry (requires GPG)
7. Writes the Claude Code MCP config

---

## Prerequisites

| Requirement | Why | Install |
|-------------|-----|---------|
| Python 3.11+ | seed.py + server | [python.org](https://python.org) |
| git | clone the repo | `sudo apt install git` |
| gpg | sign SAFE manifests | `sudo apt install gnupg` |
| PostgreSQL 14+ | LOAM knowledge graph | `sudo apt install postgresql` |
| Claude Code | connects to the MCP server | [claude.ai/code](https://claude.ai/code) |
| Ollama (optional) | local inference | [ollama.ai](https://ollama.ai) |

**On WSL:** All of the above work. Run `seed.py` inside WSL. Set `WILLOW_SAFE_ROOT` to a path inside WSL (e.g. `~/SAFE/Applications`) if you don't have a separate drive.

---

## Manual Setup (if you prefer to do it step by step)

### 1. Clone

```bash
git clone https://github.com/rudi193-cmd/willow-1.7
cd willow-1.7
```

### 2. Python venv

```bash
python3 -m venv ~/.willow-venv
~/.willow-venv/bin/pip install -r requirements.txt
```

### 3. Postgres

```bash
createdb willow
psql -d willow -f schema.sql
```

### 4. Credentials

```bash
cp credentials.json.example credentials.json
# Edit credentials.json — add at least one free-tier API key
```

Free tier keys (all free, no credit card):
- [Groq](https://console.groq.com/keys)
- [Cerebras](https://cloud.cerebras.ai)
- [SambaNova](https://cloud.sambanova.ai)

### 5. SAFE folder

Every agent needs a signed manifest folder before the authorization gate passes.

```bash
export WILLOW_SAFE_ROOT=~/SAFE/Applications   # or /media/your-drive/SAFE/Applications
mkdir -p $WILLOW_SAFE_ROOT

./tools/safe-scaffold.sh Willow operator "Willow core node"
```

This creates `$WILLOW_SAFE_ROOT/Willow/` with a manifest and GPG signature.

Requires a GPG key in your keyring. Create one if you don't have one:
```bash
gpg --full-generate-key
```

### 6. Claude Code MCP config

Add to `.mcp.json` in any project (or to Claude Code's global config):

```json
{
  "mcpServers": {
    "willow": {
      "command": "/path/to/willow-1.7/willow.sh",
      "type": "stdio",
      "env": {
        "WILLOW_PYTHON": "/home/yourname/.willow-venv/bin/python3"
      }
    }
  }
}
```

### 7. Start

```bash
./willow.sh status    # health check
./willow.sh verify    # SAFE manifest audit
./willow.sh           # start (Claude Code connects automatically)
```

---

## Building an App on Willow

Use the templates in this repo as a starting point:

| File | What it is |
|------|-----------|
| `safe-app-manifest.template.json` | Manifest schema — defines your app's permissions and data streams |
| `safe_integration.template.py` | Python client — wraps the SAP authorization + inference chain |

### Minimum viable app

**1. Scaffold your SAFE entry**
```bash
./tools/safe-scaffold.sh MyApp worker "What my app does"
```

**2. Copy and edit the manifest**
```bash
cp safe-app-manifest.template.json my-app/safe-app-manifest.json
# edit: set app_id, name, description, b17 (get from willow_base17 MCP tool)
gpg --detach-sign my-app/safe-app-manifest.json
```

**3. Copy and edit the integration**
```bash
cp safe_integration.template.py my-app/safe_integration.py
# edit: set APP_ID at top of file
```

**4. Use it**
```python
import safe_integration as willow

client = willow.WillowClient(app_id="MyApp")
reply = client.ask("What should I do next?")
atoms = client.search("relevant topic", limit=5)
```

---

## Architecture (one-page)

```
Your App
   │
   └── safe_integration.py
            │
            ├── SAP gate (gate.py)
            │     SAFE folder exists?  manifest present?  .sig valid?  gpg verify?
            │     All four pass → authorized
            │
            ├── Context assembly (context.py)
            │     Loads KB atoms from Postgres, scoped to permitted data streams
            │
            └── Inference (generic_client.py)
                  Ollama → Groq → Cerebras → SambaNova
```

The SAFE folder **is** the authorization. Delete it → access revoked. No config change, no restart.

---

## Governance

**Dual Commit:** AI proposes, human ratifies. Nothing writes to the knowledge graph without your explicit approval.

**Session consent:** Authorization is checked on every call — not cached, not assumed. Any agent whose SAFE folder is missing or has an invalid signature is denied immediately.

**Local-first:** Your data lives on your machine. The fleet fallback uses free-tier cloud APIs only when local inference is unavailable, and only for the specific query — nothing is stored.

---

ΔΣ=42
