"""Configuration helpers for LocKno."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterator, Tuple


@dataclass(frozen=True)
class ModelEntry:
    provider: str
    name: str
    model_type: str


class LLMConfig:
    """Loads provider/model configuration from a JSON file."""

    def __init__(self, path: str):
        self.path = path
        self.raw = self._load_file(path)
        self.providers: Dict[str, Dict] = {}
        for name, data in self.raw.get("providers", {}).items():
            key = (name or "").strip().lower()
            if not key:
                continue
            self.providers[key] = data or {}

        default_block = self.raw.get("default", {})
        self.default_provider = (default_block.get("provider") or "").strip().lower()
        self.default_model = (default_block.get("model") or "").strip()
        if not self.default_provider and self.providers:
            self.default_provider = next(iter(self.providers))
        if not self.default_model and self.default_provider:
            self.default_model = (self.providers.get(self.default_provider, {}).get("models", [{}])[0].get("name") or "").strip()

    @staticmethod
    def _load_file(path: str) -> Dict:
        with open(path, "r", encoding="utf-8") as config_file:
            return json.load(config_file)

    def provider_defaults(self, provider: str) -> Tuple[str, str]:
        provider_cfg = self.providers.get(provider)
        if provider_cfg is None:
            raise KeyError(provider)
        chat_model = (self.default_model if provider == self.default_provider else "").strip()
        if not chat_model:
            models = provider_cfg.get("models", [])
            chat_model = (models[0].get("name") if models else "").strip()
        embed_model = chat_model
        return chat_model, embed_model

    def iter_models(self) -> Iterator[ModelEntry]:
        for provider_name, data in self.providers.items():
            for model in data.get("models", []):
                model_name = (model.get("name") or "").strip()
                model_type = (model.get("type") or "unknown").strip()
                if not model_name:
                    continue
                yield ModelEntry(provider=provider_name, name=model_name, model_type=model_type)
