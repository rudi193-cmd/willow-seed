---
b17: WSED1
title: Security Audit — willow-seed
date: 2026-05-06
auditor: Hanuman (Claude Code, Sonnet 4.6)
status: open
---

# Security Audit — willow-seed

Part of Level 2 full-fleet security audit. willow-seed — Willow system installer. Clones willow-1.9 repo, creates virtual environment, installs dependencies, seeds SAFE folder structure, and launches the system.

## Rubric Results

| # | Check | Status | Notes |
|---|---|---|---|
| R1 | SQL injection | N/A | No database queries |
| R2 | Shell injection | ✅ PASS | subprocess.run with list args only; install.sh uses quoted variables throughout |
| R3 | Path traversal | ✅ PASS | All paths resolved via Path(__file__).parent or Path.home(); no user-controlled path construction |
| R4 | Hardcoded credentials | ✅ PASS | No credentials; only hardcoded URLs (GitHub repo URL, public) |
| R5 | CORS wildcard | N/A | No HTTP server |
| R6 | XSS | N/A | No HTML rendering |
| R7 | Unsigned code execution | ⚠️ WARN | os.execv to re-exec self; subprocess git clone of a hardcoded URL — both safe in isolation, but clone URL is hardcoded (see P2) |
| R8 | Missing auth on APIs | N/A | No API surface |
| R9 | Bare except swallowing errors | ✅ PASS | Exceptions caught with informative error messages; no silent swallows |
| R10 | Predictable temp paths | ✅ PASS | No temp files; clone to user-controlled or script-adjacent directory |
| R11 | Race conditions | ✅ PASS | Single-threaded sequential installer; no shared state |
| R12 | safe_integration.py status() | ✅ PASS | safe_integration.template.py present — correct for a seed/installer |
| R13 | Entry point importable | ✅ PASS | Both seed.py and install.sh are clean entry points |
| R14 | requirements.txt pinned | ⚠️ WARN | requirements.base.txt uses `>=` bounds only — not pinned to exact versions |
| R15 | No hardcoded dev paths | ✅ PASS | WILLOW_REPO is a public GitHub URL (not a dev machine path); all local paths dynamic |

## Findings

### P2: WS-URL-01 — Hardcoded clone URL not overridable

**Severity:** P2
**Status:** Open
**Files:** `seed.py:21`, `install.sh:11`

```python
WILLOW_REPO = "https://github.com/rudi193-cmd/willow-1.9"
```

The install source is hardcoded in two places. A user who wants to install from a fork or a local mirror has no way to override it without editing the file. For a seed/bootstrapper, this is a portability concern rather than a security issue — but if the GitHub repo were ever compromised, users have no way to pin to a known-good URL without source edits.

**Recommended fix:** Accept `WILLOW_REPO` as an env var override:
```python
WILLOW_REPO = os.environ.get("WILLOW_REPO", "https://github.com/rudi193-cmd/willow-1.9")
```

---

### P2: WS-DEP-01 — requirements.base.txt uses minimum version bounds only

**Severity:** P2
**Status:** Open

`mcp>=1.0.0`, `psycopg2-binary>=2.9.0`, etc. — minimum bounds only, no upper bounds or exact pins. A `pip install` could pull future breaking releases. Low risk for an installer (dependencies are standard, well-maintained packages), but worth pinning for reproducibility.

---

## Strengths

- **Subprocess calls are correct.** `subprocess.run(["git", "clone", ...])` — list args, no shell=True.
- **install.sh is well-quoted.** All variable expansions use double quotes; no word-splitting or glob expansion vulnerabilities.
- **safe_integration.template.py present.** Seed provides the SAFE template to new applications — the correct pattern for a bootstrapper.
- **os.execv re-exec is safe.** Used to restart inside the venv with the same arguments after venv activation — not dynamic code execution.
- **No credentials or secrets.** Only public GitHub URLs and local paths.
