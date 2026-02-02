from __future__ import annotations

from enum import StrEnum, auto


class LocalProviderType(StrEnum):
    """Enum of supported local LLM backend provider types."""

    HUGGING_FACE = auto()
    LLAMA_CPP = auto()
    OLLAMA = auto()
