"""
module2_dream_graph — Dream Graph. Public entry point.

Exports are split into two tiers so callers that only need the data shapes
(e.g. Module 3's schemas.py) can import without pulling in the SQLite/OpenAI
persistence dependency chain:

  TIER 1 — pure schema types (no external deps, always safe to import):
      DreamGraph, Node, Edge, NodeType, EdgeType

  TIER 2 — persistence + embedding (requires sqlalchemy, aiosqlite, openai):
      build_and_persist_graph, build_graph, load_graph, persist_graph,
      init_db, link_recurring_symbols

Usage — schema-only (Module 3, Module 4, Module 6, tests):
    from modules.module2_dream_graph import DreamGraph, Node, NodeType

Usage — full pipeline (app.py, Module 5):
    from modules.module2_dream_graph import build_and_persist_graph
"""

# Tier 1: pure models — no heavy deps, safe for any importer
from .models import DreamGraph, Edge, EdgeType, Node, NodeType


def _load_persistence():
    """Lazy import guard so the module can be imported in environments without
    sqlalchemy/aiosqlite/openai installed (e.g. CI, unit tests, Module 3 schema checks)."""
    from .builder import build_graph
    from .db import init_db, load_graph, persist_graph
    from .totems import link_recurring_symbols
    return build_graph, init_db, load_graph, persist_graph, link_recurring_symbols


async def init_db() -> None:
    """Initialize the local SQLite database and create tables if they don't exist.
    Lazy-loads the db module on first call."""
    _, _init_db, _, _, _ = _load_persistence()
    await _init_db()


async def build_and_persist_graph(
    dream_id: str,
    user_id: str,
    story,  # shared.models.Story — typed loosely to avoid circular import at module load
    version: int = 1,
) -> DreamGraph:
    """The main entrypoint. Builds the typed graph, persists it, then links recurring
    totems and backfills the match results.

    Order matters here: link_recurring_symbols() calls store_node_embedding() per node,
    which does an UPDATE against rows that persist_graph() writes — it silently no-ops if
    those rows don't exist yet. persist_graph() must run first so there's something to
    update.

    Heavy imports (sqlalchemy, aiosqlite, openai) are deferred to first call.
    """
    build_graph, _init_db, _load_graph, persist_graph, link_recurring_symbols = _load_persistence()
    graph = await build_graph(dream_id, user_id, story, version)
    await persist_graph(graph)
    graph = await link_recurring_symbols(graph)
    return graph


__all__ = [
    # Tier 1 — always available
    "DreamGraph",
    "Node",
    "Edge",
    "NodeType",
    "EdgeType",
    # Tier 2 — available after first call (lazy-loaded)
    "build_and_persist_graph",
    "init_db",
]
