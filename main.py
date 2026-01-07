from __future__ import annotations

import os
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_migrate import Migrate
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from config_loader import LLMConfig
from document_utils import (
    DocumentUploadError,
    extract_upload_from_request,
    prepare_document_payload,
)
from llm.adapters.ollama import OllamaAdapter
from llm.base import LLMError
from llm.service import LLMService
from models import AppConfig, ChatMessage, Document, Sender, db


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "lockno.db")

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
CONFIG_PATH = os.getenv("LOCKNO_CONFIG", os.path.join(BASE_DIR, "config.json"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

llm_config = LLMConfig(CONFIG_PATH)
PROVIDER_CONFIG = llm_config.providers
DEFAULT_PROVIDER = llm_config.default_provider
DEFAULT_MODEL_FOR_PROVIDER, DEFAULT_EMBEDDING_FOR_PROVIDER = llm_config.provider_defaults(DEFAULT_PROVIDER)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)


def create_adapter(
    provider: str = DEFAULT_PROVIDER,
    model_name: str = DEFAULT_MODEL_FOR_PROVIDER,
    embedding_model: str = DEFAULT_EMBEDDING_FOR_PROVIDER,
):
    provider_key = provider.strip().lower()
    provider_cfg = PROVIDER_CONFIG.get(provider_key)
    if provider_cfg is None:
        raise RuntimeError(f"Provider '{provider_key}' missing from config")

    if provider_key == "ollama":
        if not model_name:
            model_name, _ = llm_config.provider_defaults(provider_key)
        if not embedding_model:
            _, embedding_model = llm_config.provider_defaults(provider_key)
        resolved_model = model_name.strip()
        if not resolved_model:
            raise RuntimeError("Ollama model missing in config")
        resolved_embedding = (embedding_model or resolved_model).strip()
        adapter = OllamaAdapter(
            base_url=OLLAMA_BASE_URL,
            chat_model=resolved_model,
            embedding_model=resolved_embedding,
        )
        return adapter

    raise RuntimeError(f"Unsupported LLM provider: {provider_key}")


llm_service = LLMService(
    adapter=create_adapter(DEFAULT_PROVIDER, DEFAULT_MODEL_FOR_PROVIDER, DEFAULT_EMBEDDING_FOR_PROVIDER)
)

def reset_config_table() -> None:
    """Replace config table contents to match the JSON definition."""
    try:
        db.session.query(AppConfig).delete()
        for row in _iter_config_rows():
            db.session.add(row)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        app.logger.warning("Failed to seed config table: %s", exc)


def _iter_config_rows():
    for entry in llm_config.iter_models():
        yield AppConfig(
            provider=entry.provider,
            model_name=entry.name,
            model_type=entry.model_type,
        )


def ensure_config_seeded() -> None:
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table(AppConfig.__tablename__):
            return
        if db.session.query(AppConfig).count() == 0:
            reset_config_table()
    except SQLAlchemyError:
        db.session.rollback()

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
        system_prompt = ChatMessage(
            session_id=session_id,
            sender=Sender.SYSTEM,
            message=(
                "You are a helpful personal assistant. Answer the user's questions as best as you can. "
                "If you don't know the answer just say you don't know. You will be provided with personalized context from RAG techniques. "
                "Use that context to help yourself create better answers, and always prefer that context over your own knowledge. "
                "Be realistic and not too sugar coated in the way you answer questions."
            ),
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
    try:
        reply_message = llm_service.chat(messages=messages)
    except LLMError as exc:
        app.logger.error("LLM chat failed for session %s: %s", session_id, exc)
        # TODO: Decide whether to persist the user message even when the LLM call fails.
        return jsonify({"error": "llm_unavailable", "message": "The language model is unavailable."}), 502

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


@app.get("/api/config/llm")
def get_llm_config():
    entries = AppConfig.query.order_by(AppConfig.provider.asc()).all()
    if not entries:
        return jsonify({"error": "config not initialized"}), 404
    return jsonify([entry.to_dict() for entry in entries])


@app.post("/api/config/llm")
def set_llm_config():
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object expected"}), 400

    provider = (body.get("provider") or "").strip().lower()
    model_name = (body.get("model_name") or "").strip()
    if not provider or not model_name:
        return jsonify({"error": "provider and model_name are required"}), 400

    if not _model_supported(provider, model_name):
        return (
            jsonify({"error": "unsupported provider/model", "provider": provider, "model_name": model_name}),
            400,
        )

    try:
        _, provider_embedding = llm_config.provider_defaults(provider)
    except KeyError:
        provider_embedding = model_name

    try:
        new_adapter = create_adapter(provider=provider, model_name=model_name, embedding_model=provider_embedding)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400

    llm_service.set_adapter(new_adapter)
    return jsonify({"provider": provider, "model_name": model_name})


@app.post("/api/documents")
def create_document():
    try:
        upload = extract_upload_from_request(request.files.get("file"))
        document_payload = prepare_document_payload(upload)
    except DocumentUploadError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    document = Document(**document_payload)
    try:
        db.session.add(document)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        app.logger.error("Failed to store document: %s", exc)
        return jsonify({"error": "failed to store document"}), 500

    return jsonify(document.to_dict()), 201


@app.get("/api/documents")
def list_documents():
    documents = Document.query.order_by(Document.created_at.desc()).all()
    return jsonify([doc.to_dict() for doc in documents])


@app.delete("/api/documents/<int:document_id>")
def delete_document(document_id: int):
    document = Document.query.get(document_id)
    if document is None:
        return jsonify({"error": "document not found"}), 404

    try:
        db.session.delete(document)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        app.logger.error("Failed to delete document %s: %s", document_id, exc)
        return jsonify({"error": "failed to delete document"}), 500

    return jsonify({"status": "deleted", "id": document_id})


def get_chat_for_session(session_id: str) -> list[ChatMessage]:
    return (
        ChatMessage.query.filter_by(session_id=session_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )


def _model_supported(provider: str, model_name: str) -> bool:
    normalized_provider = (provider or "").strip().lower()
    return (
        AppConfig.query.filter_by(provider=normalized_provider, model_name=model_name)
        .first()
        is not None
    )

with app.app_context():
    ensure_config_seeded()

@app.route("/")
def index():
    return "Flask setup works"


if __name__ == "__main__":
    app.run()
