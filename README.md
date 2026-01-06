# LocKno - a local knowledge LLM setup

## Overview

LocKno is a lightweight chat backend that exposes a simple HTTP API, persists
conversation history, and talks to local or remote LLMs through pluggable
adapters. The current implementation ships with an Ollama adapter so you can
spin up a chat experience immediately while leaving room to grow into RAG flows
or other providers later on.

## Features

- Chat API (`POST /api/chat`, `GET /api/chat/<session_id>`) that tracks
  per-session histories and seeds a default system prompt.
- Config endpoints (`/api/config/llm`) backed by a JSON file + SQLite table so
  you can enumerate allowed providers/models and switch the active adapter at
  runtime.
- Adapter abstraction (`llm.service`, `llm.adapters.*`) that lets you plug in
  additional providers without touching the API or persistence layers.
- Out-of-the-box Ollama support using the official Python SDK, configurable via
  environment variables (`OLLAMA_BASE_URL`, `OLLAMA_API_KEY`).
- Persistence powered by SQLAlchemy + Flask-Migrate, with SQLite as the default
  backend but swappable for Postgres/MySQL by changing `DATABASE_URL`.

## Roadmap

- Document selection, ingestion, and embedding storage for Retrieval-Augmented
  Generation (RAG).
- Embedding API in the Ollama adapter and downstream storage/retrieval logic.
- Authorization/header management for remote LLM hosts.
- Structured logging, rate limiting, and additional error handling once more
  clients/providers are added.

## Getting started

1. Create a virtual environment and install dependencies with `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and adjust `DATABASE_URL` if you want to use a
   different database backend/filename. Override `LOCKNO_CONFIG` to point at a
   custom `config.json`, and `OLLAMA_BASE_URL` if the local Ollama service runs
   on a non-default host.
3. Review `config.json` for the list of supported LLM providers/models. The
   default points at the local Ollama model `llama3.2:3b`.
4. Initialize the migration folder (first run only) with `flask --app main db init`.
5. Whenever models change run `flask --app main db migrate` followed by
   `flask --app main db upgrade` to apply schema updates.
6. Start the dev server via `python3 main.py`; this spins up Flask on the
   default port and connects to the local SQLite file `lockno.db`.
7. Exercise the chat/config endpoints:
   - `POST /api/chat` with `{ "session_id": "", "message": "Hello" }` to
     create a conversation (omit `session_id` to auto-generate).
   - `GET /api/chat/<session_id>` to fetch the stored message history. Each
     response includes timestamps and sender roles.
   - `GET /api/config/llm` to view all supported provider/model combinations
     loaded from `config.json`.
   - `POST /api/config/llm` with `{ "provider": "ollama", "model_name": "llama3.2:3b" }`
     to switch the live adapter (values are validated against the database).

Persistence now relies on SQLAlchemy models (`models.ChatMessage`) managed via
Flask-Migrate so swapping SQLite for MySQL/Postgres later only requires a
configuration change plus new migrations.
