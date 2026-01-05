"""Base interfaces for LLM adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from models import ChatMessage


class LLMAdapter(ABC):
    """Defines the expected LLM operations for adapters."""

    @abstractmethod
    def chat(self, messages: List[ChatMessage]) -> ChatMessage:
        """Execute a chat completion request."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for given texts."""
