"""
Module 2 — Graph builder.

Public contract:

    await build_graph(dream_id, user_id, story) -> DreamGraph

Takes Module 1's Story output and produces the typed node/edge graph.
"""

from __future__ import annotations

import re
from shared.models import Story
from .models import DreamGraph, Edge, EdgeType, Node, NodeType


def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


async def build_graph(
    dream_id: str,
    user_id: str,
    story: Story,
    version: int = 1,
) -> DreamGraph:
    nodes: list[Node] = []
    edges: list[Edge] = []

    # 1. Character Nodes
    for char in story.characters:
        nodes.append(
            Node(
                id=char.id,
                type=NodeType.character,
                label=char.name,
                attributes={"role": char.role},
                is_recurring_symbol=False,
            )
        )

    # Keep track of unique locations and emotions to create nodes for them
    location_ids: dict[str, str] = {}
    emotion_ids: dict[str, str] = {}

    # 2. Scene/Event, Location, and Emotion Nodes + Edges
    for scene in story.scenes:
        event_id = f"event::s{scene.id}"
        nodes.append(
            Node(
                id=event_id,
                type=NodeType.event,
                label=f"Scene {scene.id}: {scene.setting}",
                attributes={"emotional_tone": scene.emotional_tone},
            )
        )

        # Location Node
        loc_key = slugify(scene.setting)
        loc_id = location_ids.setdefault(scene.setting, f"location::{loc_key}")
        if loc_id not in (n.id for n in nodes):
            nodes.append(
                Node(
                    id=loc_id,
                    type=NodeType.location,
                    label=scene.setting,
                )
            )
        edges.append(_edge(event_id, loc_id, EdgeType.located_at))

        # Emotion Node
        emo_key = slugify(scene.emotional_tone)
        emo_id = emotion_ids.setdefault(scene.emotional_tone, f"emotion::{emo_key}")
        if emo_id not in (n.id for n in nodes):
            nodes.append(
                Node(
                    id=emo_id,
                    type=NodeType.emotion,
                    label=scene.emotional_tone,
                )
            )

        # Characters present in this scene (who speak lines)
        speakers = {line.speaker for line in scene.lines if line.speaker}
        for speaker_id in speakers:
            # Verify character exists
            if any(char.id == speaker_id for char in story.characters):
                edges.append(_edge(speaker_id, event_id, EdgeType.appears_in))
                edges.append(_edge(speaker_id, emo_id, EdgeType.feels))

    # 3. happens_before chain between consecutive events
    ordered_scenes = sorted(story.scenes, key=lambda s: s.id)
    for s1, s2 in zip(ordered_scenes, ordered_scenes[1:]):
        edges.append(
            _edge(f"event::s{s1.id}", f"event::s{s2.id}", EdgeType.happens_before)
        )

    return DreamGraph(
        dream_id=dream_id, user_id=user_id, version=version, nodes=nodes, edges=edges
    )


def _edge(from_id: str, to_id: str, type_: EdgeType) -> Edge:
    return Edge(id=f"{from_id}->{to_id}:{type_.value}", from_id=from_id, to_id=to_id, type=type_)
