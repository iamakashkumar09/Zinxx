"""Module 2 — Dream Graph. NOT IMPLEMENTED in this build (hackathon scope).

Per Architecture.md: a persistent structured representation (Character, Location,
Object/Totem, Emotion, Event, Transition nodes with typed edges) stored in Postgres +
pgvector, so the system can recognize recurring totems/characters across sessions via
embedding similarity search.

Why skipped: this build is stateless and single-pass — Module 1 (dream_understanding)
produces a Story directly with no persistent storage or cross-session memory. Adding this
would require a database + embeddings pipeline, which is out of scope for the free-tier,
single-request hackathon build.

If you pick this up: it would sit between Module 1 and Module 3 (narrative_reconstruction),
storing what Module 1 extracts and letting Module 3 query it for continuity.
"""


def process(*args, **kwargs):
    raise NotImplementedError(
        "Module 2 (Dream Graph) is not implemented in this build. "
        "See this module's docstring for the intended design."
    )
