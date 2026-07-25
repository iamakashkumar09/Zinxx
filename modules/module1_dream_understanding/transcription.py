"""Optional voice input for Module 1. Lets a user speak their dream instead of typing it.

Uses OpenAI's Whisper model (whisper-1). Output is plain text that flows into
story_extraction.py exactly like typed input would — this module has no other effect
on the Story schema.
"""

from shared.openai_client import get_client

TRANSCRIBE_MODEL = "whisper-1"


def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    if not file_bytes:
        raise ValueError("No audio data received.")
    client = get_client()
    transcript = client.audio.transcriptions.create(
        file=(filename, file_bytes),
        model=TRANSCRIBE_MODEL,
    )
    return (transcript.text or "").strip()
