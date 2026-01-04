from __future__ import annotations

import os
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError

from models import ChatMessage, Sender, db


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "lockno.db")

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)


@app.post("/api/chat")
def send_chat_message():
    body = request.get_json(silent=False)
    if body is None or not isinstance(body, dict):
        return jsonify({"error": "JSON body is required"}), 400

    raw_session = body.get("session_id")
    session_id = raw_session.strip() if isinstance(raw_session, str) else ""
    raw_message = body.get("message")
    message = raw_message.strip() if isinstance(raw_message, str) else ""

    if not message:
        return jsonify({"error": "message is required"}), 400

    if session_id:
        existing = ChatMessage.query.filter_by(session_id=session_id).first()
        if not existing:
            return jsonify({"error": "session not found"}), 404
    else:
        session_id = uuid.uuid4().hex

    record = ChatMessage(session_id=session_id, sender=Sender.USER, message=message)
    # send out the session to the LLM-api (needs to be implemented at some point)
    reply_text = f"Placeholder for a reply: {message}"
    assistant_record = ChatMessage(
        session_id=session_id,
        sender=Sender.ASSISTANT,
        message=reply_text,
    )
    try:
        db.session.add(record)
        db.session.add(assistant_record)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        return jsonify({"error": "failed to store message", "details": str(exc)}), 500

    response = {
        "session_id": session_id,
        "reply": reply_text,
    }
    return jsonify(response)


@app.get("/api/chat/<session_id>")
def get_chat_history(session_id):
    messages = (
        ChatMessage.query.filter_by(session_id=session_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )
    if not messages:
        return jsonify({"error": "session not found"}), 404
    serialized = [message.to_dict() for message in messages]
    return jsonify({"session_id": session_id, "messages": serialized})


@app.route("/")
def index():
    return "Flask setup works"


if __name__ == "__main__":
    app.run()
