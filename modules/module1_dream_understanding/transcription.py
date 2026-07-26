"""Optional voice input for Module 1 (Architecture.md calls out gpt-4o-mini-transcribe for
this — "a nice demo moment"). Lets a user speak their dream instead of typing it.

Uses Groq's hosted Whisper (whisper-large-v3-turbo — fast, free-tier) instead of OpenAI's
transcription models. Output is plain text that flows into story_extraction.py exactly
like typed input would — this module has no other effect on the Story schema.
"""

from shared.llm_client import get_client

TRANSCRIBE_MODEL = "whisper-large-v3-turbo"


def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    if not file_bytes:
        raise ValueError("No audio data received.")
    client = get_client()
    transcript = client.audio.transcriptions.create(
        file=(filename, file_bytes),
        model=TRANSCRIBE_MODEL,
    )
    return (transcript.text or "").strip()
