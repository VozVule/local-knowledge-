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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatMessage(db.Model):
    __tablename__ = "messages"
    __tableargs__ = {
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
