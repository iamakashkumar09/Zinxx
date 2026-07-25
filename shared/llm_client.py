"""Shared Groq client factory. Chat-completion calls (Module 1 extraction, Module 8
performance direction) run on OpenAI now — see shared/openai_client.py. This client is
kept for Module 1's optional voice transcription (module1_dream_understanding/
transcription.py), which uses Groq's free-tier hosted Whisper.
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
