# Replant — Fresh Seed on /media/willow
b17: RPLNT1  ΔΣ=42

## Goal

Delete the old Willow install on `/media/willow` and plant a clean seed at the canonical partition location.
Then use the dashboard as the entry point to install apps one by one through the UI.

## Partition Routing (canonical rule)

- System/project files → `/media/willow/{project}/`
- Personal files → `~/Ashokoa/Filed/` or `~/personal/`
- `~/github/willow-1.7/` is a migration landing spot, not the intended home.

**Plant command:**
```bash
python3 seed.py --target /media/willow/willow-1.7
```

This places willow-1.7 at `/media/willow/willow-1.7/` and co-locates the SAFE root at `/media/willow/SAFE/Applications`.

---

## Prerequisites (audit gaps to close first)

Before planting, the following must be resolved:

1. **No live SAFE root** — fresh `~/SAFE/Applications` (or `/media/willow/SAFE/Applications`) needed,
   wired into both `WILLOW_SAFE_ROOT` (willow.sh) and `SAP_SAFE_ROOT` / `SAP_PGP_FINGERPRINT` (all .mcp.json env blocks).

2. **seed.py Step 5 uses wrong default SAFE root** — hardcoded to `/media/willow/SAFE/Applications`.
   Either fix the default or ensure the env var is set before running seed.

3. **seed.py has no Step 7** — app registration loop doesn't exist yet.
   The dashboard should handle this post-plant.

4. **schema.sql is outdated** — table names don't match the live DB.
   Fix before planting so a fresh `psql -d willow -f schema.sql` works.

5. **willow-mcp .mcp.json env vars missing** — all fleet repos need
   `SAP_SAFE_ROOT` and `SAP_PGP_FINGERPRINT` set in their .mcp.json.

6. **safe_integration.py files use HTTP porch** — need portless replacements
   before apps are usable post-plant.

---

## Replant Sequence (draft)

1. Archive `/media/willow` (rename to `/media/willow-archive` or similar)
2. Fix schema.sql, seed.py Step 5 default, willow.sh SAFE_ROOT
3. Run `python3 seed.py --target /media/willow` — plant fresh
4. Scaffold SAFE manifests for each app via `safe-scaffold.sh`
5. Launch dashboard — use it to register and enable apps one by one
6. Retire `~/SAFE_backup/` (archive, not delete)

---

## Apps to install via dashboard (post-plant)

- willow-dashboard (self, already working)
- safe-app-ask-jeles
- safe-app-field-notes
- safe-app-grove
- safe-app-the-binder
- safe-app-source-trail
- safe-app-genealogy
- safe-app-law-gazelle
- safe-app-llmphysics
- safe-app-vision-board (needs portless rewrite first)
- ... (full list in SAFE_backup/Applications/)

---

## Notes

- Dashboard is the missing entry point. Seed plants it. Everything else hangs off it.
- `safe-app-vision-board` has a FastAPI backend on port 8420 — needs portless rewrite before install.
- `safe-apps/` duplicate clone dir at `~/github/safe-apps/` can be deleted (same remotes as direct repos).
- `~/agents/haumana/` has 100+ March session handoffs — compost before replant.

---
