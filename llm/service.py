"""High-level LLM service that delegates to provider adapters."""
from __future__ import annotations

from typing import List

from llm.base import LLMAdapter
from models import ChatMessage


class LLMService:
    """Routes LLM requests to the configured adapter."""

    def __init__(self, adapter: LLMAdapter):
        self._adapter = adapter

    def chat(self, messages: List[ChatMessage]) -> ChatMessage:
        return self._adapter.chat(messages)

    def embed(self, texts: List[str]) -> List[List[float]]: 
        return self._adapter.embed(texts)

    def set_adapter(self, adapter: LLMAdapter) -> None:
        self._adapter = adapter
