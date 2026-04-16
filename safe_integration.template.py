"""
SAFE Application Integration Template
======================================
Copy this file to your application root as safe_integration.py.

Replace every occurrence of {APP_ID} with your app's ID
(must match app_id in safe-app-manifest.json and the SAFE folder name).

This is the portless SAP integration. No HTTP. No exposed ports.
Your app talks to Willow through direct Python imports and the MCP tool bus.

── Two integration paths ─────────────────────────────────────────────────────

Path A — Direct Python (recommended when your app runs inside the willow-1.7 venv)
  from safe_integration import WillowClient
  client = WillowClient(app_id="{APP_ID}")
  reply  = client.ask("What should I do next?")
  atoms  = client.search("governance rules", limit=5)

Path B — MCP tool calls (when your app is a Claude Code prompt or Claude artifact)
  Use willow_knowledge_search, willow_knowledge_ingest, willow_chat directly
  from Claude Code. The MCP server handles auth. No import needed.

── SAFE authorization ────────────────────────────────────────────────────────

Before your app can call anything, a SAFE folder must exist at:
  $WILLOW_SAFE_ROOT/{APP_ID}/
  $WILLOW_SAFE_ROOT/{APP_ID}/safe-app-manifest.json
  $WILLOW_SAFE_ROOT/{APP_ID}/safe-app-manifest.json.sig

Scaffold it: ./tools/safe-scaffold.sh {APP_ID} worker "My app description"

── Usage ─────────────────────────────────────────────────────────────────────

import safe_integration as willow

client = willow.WillowClient(app_id="{APP_ID}")

# Ask a question (Ollama → free fleet fallback)
reply = client.ask("What is the capital of France?")

# Search the knowledge graph
atoms = client.search("France geography", limit=3)

# Ingest content into the knowledge graph (staged — Sean ratifies)
client.contribute("Paris is the capital of France.", category="reference")
"""

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Optional


# ── Configuration ─────────────────────────────────────────────────────────────

# Path to willow-1.7 repo root. Defaults to sibling directory or WILLOW_ROOT env var.
_WILLOW_ROOT = Path(
    os.environ.get("WILLOW_ROOT", Path(__file__).parent.parent / "willow-1.7")
)


def _ensure_path():
    """Add willow-1.7 to sys.path if it's not already importable."""
    root = str(_WILLOW_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


# ── Client ────────────────────────────────────────────────────────────────────

class WillowClient:
    """
    SAP application client. Wraps the AppClient from sap.clients.generic_client.

    Parameters
    ----------
    app_id : str
        Your app's ID — must match the SAFE folder and manifest.
    model : str, optional
        Ollama model to use. Defaults to "llama3.2:1b".
    personas_path : str, optional
        Absolute path to your personas.py. Required if your app has a persona.
    persona_name : str, optional
        Name of the persona to load from personas.py.
    category_filter : list[str], optional
        KB categories to scope context assembly to.
    """

    def __init__(
        self,
        app_id: str,
        model: str = "llama3.2:1b",
        personas_path: Optional[str] = None,
        persona_name: Optional[str] = None,
        category_filter: Optional[list] = None,
    ):
        _ensure_path()
        try:
            from sap.clients.generic_client import AppClient
        except ImportError as e:
            raise ImportError(
                f"Cannot import AppClient from willow-1.7.\n"
                f"Check WILLOW_ROOT points to your willow-1.7 directory.\n"
                f"Current WILLOW_ROOT: {_WILLOW_ROOT}\n"
                f"Original error: {e}"
            )

        self._client = AppClient(
            app_id=app_id,
            personas_path=personas_path,
            persona_name=persona_name,
            model=model,
            category_filter=category_filter,
        )
        self.app_id = app_id

    def ask(self, question: str) -> str:
        """
        Ask a question. Assembles KB context → builds prompt → calls Ollama
        or free fleet fallback. Returns the model's response as a string.
        """
        return self._client.ask(question) or ""

    def search(self, query: str, limit: int = 5) -> list:
        """
        Search the Willow knowledge graph. Returns a list of matching atoms.
        Each atom is a dict with keys: b17, title, content, category.
        """
        _ensure_path()
        try:
            from core.pg_bridge import try_connect
        except ImportError:
            return []

        pg = try_connect()
        if not pg:
            return []

        try:
            cur = pg.cursor()
            cur.execute(
                """
                SELECT b17, title, content, category
                FROM knowledge_atoms
                WHERE to_tsvector('english', coalesce(content,'') || ' ' || coalesce(title,''))
                      @@ plainto_tsquery('english', %s)
                  AND domain != 'archived'
                ORDER BY ts_rank(
                    to_tsvector('english', coalesce(content,'') || ' ' || coalesce(title,'')),
                    plainto_tsquery('english', %s)
                ) DESC
                LIMIT %s
                """,
                (query, query, limit)
            )
            rows = cur.fetchall()
            cur.close()
            return [
                {"b17": r[0], "title": r[1], "content": r[2], "category": r[3]}
                for r in rows
            ]
        except Exception:
            return []

    def contribute(self, content: str, category: str = "reference", title: str = "") -> dict:
        """
        Stage content for ingestion into the Willow knowledge graph.
        Nothing is written to the KB until Sean ratifies via willow_ratify.
        Returns {"ok": bool, "staged": path_or_error}.
        """
        _ensure_path()
        try:
            from core.willow_store import WillowStore
        except ImportError:
            return {"ok": False, "error": "Cannot import WillowStore"}

        store_root = Path(os.environ.get("WILLOW_STORE_ROOT", _WILLOW_ROOT / "store"))
        store = WillowStore(str(store_root))
        import uuid, datetime
        key = f"intake/{self.app_id}/{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
        store.put(key, {
            "source_app": self.app_id,
            "category": category,
            "title": title or content[:60],
            "content": content,
            "status": "pending_ratification",
        })
        return {"ok": True, "staged": key}


# ── Module-level convenience functions ────────────────────────────────────────
# These provide the simplest possible API for one-off use.

def ask(app_id: str, question: str, **kwargs) -> str:
    """Convenience wrapper: WillowClient(app_id).ask(question)."""
    return WillowClient(app_id, **kwargs).ask(question)


def search(app_id: str, query: str, limit: int = 5) -> list:
    """Convenience wrapper: WillowClient(app_id).search(query)."""
    return WillowClient(app_id).search(query, limit=limit)
