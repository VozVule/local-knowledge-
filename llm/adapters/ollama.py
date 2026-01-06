"""Ollama-specific adapter implementation (placeholder)."""
from __future__ import annotations

import logging
from typing import Dict, List

from ollama import chat, ChatResponse

from llm.base import LLMAdapter, LLMError
from models import ChatMessage, Sender


logger = logging.getLogger(__name__)

class OllamaAdapter(LLMAdapter):
    """Adapter that supports calls to any models served by Ollama.
       This adapter uses the Ollama Python library.
    """

    def __init__(self, base_url: str, chat_model: str, embedding_model: str):
        self.base_url = base_url
        self.chat_model = chat_model
        self.embedding_model = embedding_model

    """Call the configured Ollama chat model with full history and returns the response."""
    def chat(self, messages: List[ChatMessage], stream: bool = False) -> ChatMessage:
        try:
            response: ChatResponse = chat(
                model=self.chat_model,
                stream=stream,
                messages=self._convert_messages(messages),
            )
        except Exception as exc:  # pragma: no cover - network/SDK failure
            logger.exception("Ollama chat call failed")
            raise LLMError("Ollama chat call failed") from exc

        # package the response to ChatMessage, as that's systems native format of message handling
        return ChatMessage(
            session_id=messages[0].session_id if messages else "",
            sender=Sender.ASSISTANT,
            message=response.message.content,
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        """TODO: Call embedding endpoint."""
        raise NotImplementedError("embed not implemented yet")
    
    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        ollama_messages = []
        for chat_message in messages:
            if chat_message.sender == Sender.USER:
                role = "user"
            elif chat_message.sender == Sender.ASSISTANT:
                role = "assistant"
            elif chat_message.sender == Sender.SYSTEM:
                role = "system"
            else:
                raise ValueError(f"Unkown sender type: {chat_message.sender}")
            ollama_messages.append({
                "role": role,
                "content": chat_message.message # this is a string
            })
        return ollama_messages
