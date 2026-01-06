"""Database models for LocKno."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Sender(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatMessage(db.Model):
    __tablename__ = "messages"
    __table_args__ = {
        db.Index("idx_messages_session_id_timestamp", "session_id", "timestamp"),
    }

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(36), index=True, nullable=False)
    sender = db.Column(db.Enum(Sender), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "sender": self.sender.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class AppConfig(db.Model):
    __tablename__ = "app_config"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    provider = db.Column(db.String(64), nullable=False)
    model_name = db.Column(db.String(128), nullable=False)
    model_type = db.Column(db.String(32), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider,
            "model_name": self.model_name,
            "model_type": self.model_type,
        }
