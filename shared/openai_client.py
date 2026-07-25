"""Shared OpenAI client factory — used by Module 1 (story extraction, totem embeddings)
and Module 8 (performance direction), which make OpenAI calls. Lives in shared/ so no
module depends on another's internals.

Both get_client() and get_async_client() are lazy singletons, built on first use rather
than at import time. This matters: building the client eagerly at module import time
(reading OPENAI_API_KEY straight from os.environ) crashes any script that imports the
module before shared.config's load_dotenv() has run — a real, reproducible bug in an
earlier version of this file's sibling in module2_dream_graph/totems.py.
"""

from openai import AsyncOpenAI, OpenAI

from shared.config import OPENAI_API_KEY

_client: OpenAI | None = None
_async_client: AsyncOpenAI | None = None

_MISSING_KEY_MSG = (
    "OPENAI_API_KEY is not set. Copy .env.example to .env at the project root "
    "and fill in your key (platform.openai.com/api-keys)."
)


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(_MISSING_KEY_MSG)
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def get_async_client() -> AsyncOpenAI:
    global _async_client
    if _async_client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(_MISSING_KEY_MSG)
        _async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _async_client
