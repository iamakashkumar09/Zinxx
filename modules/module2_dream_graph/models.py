"""
Module 2 — Dream Graph data model.

Six node types (per spec): Character, Location, Object/Totem, Emotion, Event, Transition.
Typed edges: feels, owns, transforms_into, happens_before, located_at, appears_in.

This is the shape everyone downstream (Module 3, Dream Layer Engine) reads.
Change it and tell the team — Module 1's output feeds builder.py which
produces this shape.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    character = "character"
    location = "location"
    object_totem = "object_totem"
    emotion = "emotion"
    event = "event"          # one per scene
    transition = "transition"  # cut / morph / fade between two events


class EdgeType(str, Enum):
    feels = "feels"                    # character -> emotion
    owns = "owns"                      # character -> object_totem
    transforms_into = "transforms_into"  # entity -> entity (morph)
    happens_before = "happens_before"  # event -> event
    located_at = "located_at"          # event -> location
    appears_in = "appears_in"          # character/object_totem -> event


class Node(BaseModel):
    id: str
    type: NodeType
    label: str
    attributes: dict[str, str] = Field(default_factory=dict)
    is_recurring_symbol: bool = False
    # set by totems.py after embedding similarity search against past dreams
    # for the same user — points at the earliest matching node's id
    matched_totem_id: Optional[str] = None
    matched_totem_similarity: Optional[float] = None


class Edge(BaseModel):
    id: str
    from_id: str
    to_id: str
    type: EdgeType
    weight: float = 1.0
    metadata: dict[str, str] = Field(default_factory=dict)


class DreamGraph(BaseModel):
    dream_id: str
    user_id: str
    version: int = 1
    nodes: list[Node]
    edges: list[Edge]

    def nodes_by_type(self, t: NodeType) -> list[Node]:
        return [n for n in self.nodes if n.type == t]

    def totems(self) -> list[Node]:
        return [n for n in self.nodes if n.type == NodeType.object_totem]

    def recurring_totems(self) -> list[Node]:
        return [n for n in self.totems() if n.matched_totem_id is not None]

    def node(self, node_id: str) -> Optional[Node]:
        return next((n for n in self.nodes if n.id == node_id), None)
