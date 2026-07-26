"""
Module 2 — SQLite persistence.

Public contract:

    await persist_graph(graph) -> None
    await load_graph(dream_id, version=None) -> DreamGraph | None
    await find_nearest_node_embedding(user_id, embedding, node_type, exclude_dream_id) -> NearestMatch | None
    await store_node_embedding(user_id, dream_id, version, node, embedding) -> None

Local SQLite file — no server, no URL/port/password to configure. Embeddings are stored
as a JSON list of floats (SQLite has no native vector type/index), and cosine similarity
is computed in Python with numpy over the small number of past nodes any one user will
realistically have at hackathon scale. If this ever needs to scale past a few thousand
embedded nodes per user, swap this file for a real vector store — the rest of the module
(builder.py, totems.py, models.py) doesn't know or care how persistence works underneath.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from shared.config import DREAM_DB_URL
from .models import DreamGraph, Edge, Node, NodeType

Base = declarative_base()

_engine = create_async_engine(DREAM_DB_URL, echo=False)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


class GraphNodeRow(Base):
    __tablename__ = "graph_nodes"

    row_id = Column(Integer, primary_key=True)
    dream_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    node_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    label = Column(String, nullable=False)
    attributes = Column(JSON, nullable=False, default=dict)
    is_recurring_symbol = Column(Integer, nullable=False, default=0)  # bool as 0/1
    matched_totem_id = Column(String, nullable=True)
    matched_totem_similarity = Column(Float, nullable=True)
    embedding = Column(JSON, nullable=True)  # list[float], compared in Python — see find_nearest_node_embedding
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GraphEdgeRow(Base):
    __tablename__ = "graph_edges"

    row_id = Column(Integer, primary_key=True)
    dream_id = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    edge_id = Column(String, nullable=False)
    from_id = Column(String, nullable=False)
    to_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)


async def init_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# Graph persistence
# ---------------------------------------------------------------------------

async def persist_graph(graph: DreamGraph) -> None:
    async with _Session() as s:
        for n in graph.nodes:
            s.add(
                GraphNodeRow(
                    dream_id=graph.dream_id,
                    user_id=graph.user_id,
                    version=graph.version,
                    node_id=n.id,
                    type=n.type.value,
                    label=n.label,
                    attributes=n.attributes,
                    is_recurring_symbol=int(n.is_recurring_symbol),
                    matched_totem_id=n.matched_totem_id,
                    matched_totem_similarity=n.matched_totem_similarity,
                )
            )
        for e in graph.edges:
            s.add(
                GraphEdgeRow(
                    dream_id=graph.dream_id,
                    version=graph.version,
                    edge_id=e.id,
                    from_id=e.from_id,
                    to_id=e.to_id,
                    type=e.type.value,
                    weight=e.weight,
                    metadata_=e.metadata,
                )
            )
        await s.commit()


async def load_graph(dream_id: str, version: Optional[int] = None) -> Optional[DreamGraph]:
    async with _Session() as s:
        node_stmt = select(GraphNodeRow).where(GraphNodeRow.dream_id == dream_id)
        edge_stmt = select(GraphEdgeRow).where(GraphEdgeRow.dream_id == dream_id)
        if version is not None:
            node_stmt = node_stmt.where(GraphNodeRow.version == version)
            edge_stmt = edge_stmt.where(GraphEdgeRow.version == version)
        else:
            latest = select(GraphNodeRow.version).where(
                GraphNodeRow.dream_id == dream_id
            ).order_by(GraphNodeRow.version.desc()).limit(1)
            latest_version = (await s.execute(latest)).scalar_one_or_none()
            if latest_version is None:
                return None
            node_stmt = node_stmt.where(GraphNodeRow.version == latest_version)
            edge_stmt = edge_stmt.where(GraphEdgeRow.version == latest_version)

        node_rows = (await s.execute(node_stmt)).scalars().all()
        edge_rows = (await s.execute(edge_stmt)).scalars().all()
        if not node_rows:
            return None

        nodes = [
            Node(
                id=r.node_id,
                type=NodeType(r.type),
                label=r.label,
                attributes=r.attributes or {},
                is_recurring_symbol=bool(r.is_recurring_symbol),
                matched_totem_id=r.matched_totem_id,
                matched_totem_similarity=r.matched_totem_similarity,
            )
            for r in node_rows
        ]
        edges = [
            Edge(
                id=r.edge_id, from_id=r.from_id, to_id=r.to_id,
                type=r.type, weight=r.weight, metadata=r.metadata_ or {},
            )
            for r in edge_rows
        ]
        return DreamGraph(
            dream_id=dream_id,
            user_id=node_rows[0].user_id,
            version=node_rows[0].version,
            nodes=nodes,
            edges=edges,
        )


# ---------------------------------------------------------------------------
# Totem embedding memory
# ---------------------------------------------------------------------------

class NearestMatch(BaseModel):
    node_id: str
    dream_id: str
    similarity: float


async def store_node_embedding(
    user_id: str, dream_id: str, version: int, node: Node, embedding: list[float]
) -> None:
    """Backfills the embedding column, plus whatever totem-match result
    link_recurring_symbols already computed on `node` (is_recurring_symbol,
    matched_totem_id, matched_totem_similarity) on the row persist_graph
    already wrote. Call this right after persist_graph, or fold it into
    persist_graph if you'd rather embed everything up front — kept separate
    here so totem embedding failures don't block the rest of the graph from
    saving.

    Requires the row to already exist (persist_graph must run first) — this
    is an UPDATE, not an upsert, and silently no-ops otherwise.
    """
    async with _Session() as s:
        stmt = select(GraphNodeRow).where(
            GraphNodeRow.dream_id == dream_id,
            GraphNodeRow.version == version,
            GraphNodeRow.node_id == node.id,
        )
        row = (await s.execute(stmt)).scalar_one_or_none()
        if row:
            row.embedding = embedding
            row.is_recurring_symbol = int(node.is_recurring_symbol)
            row.matched_totem_id = node.matched_totem_id
            row.matched_totem_similarity = node.matched_totem_similarity
            await s.commit()


async def find_nearest_node_embedding(
    user_id: str,
    embedding: list[float],
    node_type: NodeType,
    exclude_dream_id: str,
) -> Optional[NearestMatch]:
    """Cosine-similarity search over this user's past node embeddings only —
    totem matching is scoped per-user, never across users.

    No vector index here (SQLite has none built in) — pulls every candidate
    embedding for this user+node_type and ranks in Python. Fine at hackathon
    scale (a handful of dreams per user); revisit if that ever changes.
    """
    async with _Session() as s:
        stmt = select(
            GraphNodeRow.node_id, GraphNodeRow.dream_id, GraphNodeRow.embedding
        ).where(
            GraphNodeRow.user_id == user_id,
            GraphNodeRow.type == node_type.value,
            GraphNodeRow.dream_id != exclude_dream_id,
            GraphNodeRow.embedding.isnot(None),
        )
        rows = (await s.execute(stmt)).all()
        if not rows:
            return None

        query_vec = np.asarray(embedding, dtype=float)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return None

        best: Optional[NearestMatch] = None
        for node_id, matched_dream_id, stored_embedding in rows:
            if not stored_embedding:
                continue
            candidate = np.asarray(stored_embedding, dtype=float)
            candidate_norm = np.linalg.norm(candidate)
            if candidate_norm == 0:
                continue
            similarity = float(np.dot(query_vec, candidate) / (query_norm * candidate_norm))
            if best is None or similarity > best.similarity:
                best = NearestMatch(node_id=node_id, dream_id=matched_dream_id, similarity=similarity)

        return best
