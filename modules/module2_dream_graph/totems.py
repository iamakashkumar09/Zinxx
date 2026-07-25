"""
Totem memory — cross-session recognition of recurring symbols.

Public contract:

    await link_recurring_symbols(graph: DreamGraph) -> DreamGraph

Embeds every character/location/object_totem node, checks it against every
past node the same user has ever had embedded, and if something similar
enough shows up, tags matched_totem_id/matched_totem_similarity on the node.
This is what lets the system say "this dream's totem is the same red door
from three sessions ago" instead of treating every dream as a blank slate.

Threshold is deliberately conservative (0.86 cosine similarity) — a false
match is worse than a missed one here, since it would wrongly imply the
user's subconscious is doing something it isn't.
"""

from __future__ import annotations

from openai import AsyncOpenAI

from .db import find_nearest_node_embedding, store_node_embedding
from .models import DreamGraph, Node, NodeType

_client = AsyncOpenAI()
_EMBED_MODEL = "text-embedding-3-small"
_MATCH_THRESHOLD = 0.86  # cosine similarity; tune once you have real data

_EMBEDDABLE_TYPES = {NodeType.character, NodeType.location, NodeType.object_totem}


async def link_recurring_symbols(graph: DreamGraph) -> DreamGraph:
    for node in graph.nodes:
        if node.type not in _EMBEDDABLE_TYPES:
            continue

        embedding = await _embed_node(node)

        match = await find_nearest_node_embedding(
            user_id=graph.user_id,
            embedding=embedding,
            node_type=node.type,
            exclude_dream_id=graph.dream_id,
        )
        if match and match.similarity >= _MATCH_THRESHOLD:
            node.matched_totem_id = match.node_id
            node.matched_totem_similarity = match.similarity
            node.is_recurring_symbol = True  # confirmed recurring, not just guessed

        # store this node's embedding so *future* dreams can match against it
        await store_node_embedding(
            user_id=graph.user_id,
            dream_id=graph.dream_id,
            version=graph.version,
            node=node,
            embedding=embedding,
        )

    return graph


async def _embed_node(node: Node) -> list[float]:
    text = f"{node.label}: {node.attributes.get('description', '')}".strip()
    resp = await _client.embeddings.create(model=_EMBED_MODEL, input=text)
    return resp.data[0].embedding
