"""Base interfaces for LLM adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List
from models import ChatMessage


class LLMError(Exception):
    """Represents failures raised by any LLM adapter."""

    pass

class LLMAdapter(ABC):
    """Defines the expected LLM operations for adapters."""

    @abstractmethod
    def chat(self, messages: List[ChatMessage]) -> ChatMessage:
        """Execute a chat completion request."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for given texts."""
