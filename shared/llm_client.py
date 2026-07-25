"""Shared Groq client factory — used by Module 1 (story_intelligence) and Module 2
(audio_direction), both of which make Groq chat-completion calls. Lives in shared/ so
neither module depends on the other's internals.
"""

from groq import Groq

from shared.config import GROQ_API_KEY

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env at the project root "
                "and fill in your key (get one free at console.groq.com/keys)."
            )
        _client = Groq(api_key=GROQ_API_KEY)
    return _client
