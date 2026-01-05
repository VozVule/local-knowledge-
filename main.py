from __future__ import annotations

import os
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError
from llm.adapters.ollama import OllamaAdapter
from llm.service import LLMService
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

### This is only for local dev iteration purposes.
ollama_adapter = OllamaAdapter(
    base_url="???",
    chat_model="llama3.2:3b",
    embedding_model="nomic-embed-text:latest"
)

llm_service = LLMService(adapter=ollama_adapter)
### End local dev setup.

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
        # also need to inject a system prompt
        system_prompt = ChatMessage(
            session_id=session_id,
            sender = Sender.SYSTEM,
            message = "You are a helpful personal assistant. Answer the user's questions as best as you can." \
            "If you don't know the answer just say you don't know. You will be provided with personalized context from RAG techniques." \
            "Use that context to help yourself create better answers. And always preffeer that context over your own knowledge." \
            "Be realistic and not too suggar coated in the way you answer questions."
        )
        try:
            db.session.add(system_prompt)
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            return jsonify({"error": "failed to create session", "details": str(exc)}), 500

    # retrieve and package the full session chat history and send to LLM 
    messages = get_chat_for_session(session_id)
    record = ChatMessage(session_id=session_id, sender=Sender.USER, message=message)
    messages.append(record)
    reply_message = llm_service.chat(messages=messages)

    try:
        db.session.add(record)
        db.session.add(reply_message)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        return jsonify({"error": "failed to store message", "details": str(exc)}), 500

    response = {
        "session_id": session_id,
        "reply": reply_message.message,
    }
    return jsonify(response)


@app.get("/api/chat/<session_id>")
def get_chat_history(session_id):
    messages = get_chat_for_session(session_id)
    if not messages:
        return jsonify({"error": "session not found"}), 404
    serialized = [message.to_dict() for message in messages]
    return jsonify({"session_id": session_id, "messages": serialized})


def get_chat_for_session(session_id: str) -> list[ChatMessage]:
    return (
        ChatMessage.query.filter_by(session_id=session_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )

@app.route("/")
def index():
    return "Flask setup works"


if __name__ == "__main__":
    app.run()
