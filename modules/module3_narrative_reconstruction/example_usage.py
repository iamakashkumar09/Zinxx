"""
Module 3 — Narrative Reconstruction Engine
example_usage.py

Runnable demo — no API key required (uses mock_mode). This is the fastest way to
sanity check the module after making changes:

    python -m modules.module3_narrative_reconstruction.example_usage

The sample graph is built using Module 2's canonical Node/Edge/NodeType/EdgeType
types — the same types Module 3 now consumes for real.
"""

from modules.module3_narrative_reconstruction import (
    NarrativeReconstructionEngine,
    NarrativeLLMClient,
    DreamGraph,
    Node,
    Edge,
    NodeType,
    EdgeType,
    ConversationTurn,
    SessionMeta,
    ReconstructionConfig,
    ReconstructionInput,
)


def build_sample_graph() -> DreamGraph:
    """Build a small DreamGraph using Module 2's canonical Pydantic models."""
    nodes = [
        Node(id="char_1", type=NodeType.character, label="Mother",
             attributes={"note": "appeared with no face"}),
        Node(id="loc_1",  type=NodeType.location,  label="Childhood kitchen"),
        Node(id="obj_1",  type=NodeType.object_totem, label="Red door",
             attributes={"role": "totem"}, is_recurring_symbol=True),
        Node(id="emo_1",  type=NodeType.emotion,    label="dread"),
    ]
    edges = [
        Edge(id="char_1->emo_1:feels", from_id="char_1", to_id="emo_1", type=EdgeType.feels),
        Edge(id="char_1->obj_1:owns",  from_id="char_1", to_id="obj_1",  type=EdgeType.owns),
    ]
    return DreamGraph(
        dream_id="graph_demo_1",
        user_id="user_demo",
        version=1,
        nodes=nodes,
        edges=edges,
    )


def main():
    graph = build_sample_graph()

    context = [
        ConversationTurn("user",      "I was in my childhood kitchen but it felt wrong."),
        ConversationTurn("assistant", "Wrong how — the layout, or something else?"),
        ConversationTurn("user",      "My mother was there but I couldn't see her face."),
    ]
    session = SessionMeta(dream_id="dream_1", user_id="user_demo", session_id="sess_1")
    config  = ReconstructionConfig(model_tier="draft", preserve_dream_logic=True, debug=True)

    # Use the new convenience builder (Module 2 → Module 3 bridge)
    request = NarrativeReconstructionEngine.input_from_graph(
        graph=graph,
        session_meta=session,
        conversation_context=context,
        config=config,
    )

    engine = NarrativeReconstructionEngine(llm_client=NarrativeLLMClient(mock_mode=True))
    output = engine.reconstruct(request)

    print(f"narrative_id: {output.narrative_id}")
    print(f"beats: {len(output.beats)}")
    for beat in output.beats:
        print(f"  [{beat.order}] {beat.narrative_text}")
        for gf in beat.gap_fills:
            print(f"      gap-fill (conf={gf.confidence}): {gf.fill_content}")
    print(f"warnings: {output.warnings}")
    print(f"graph_updates: {output.graph_updates}")
    print(f"provenance_map: {output.provenance_map}")


if __name__ == "__main__":
    main()
