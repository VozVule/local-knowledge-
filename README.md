# LocKno - a local knowledge LLM setup

## Overview

LocKno is a side project aimed at building an environment where a local or cloud-hosted LLM can safely and selectively access user-approved documents on the local machine in order to provide more accurate answers.

The system uses Retrieval-Augmented Generation (RAG) to ground model responses in verified, user-supplied data rather than relying solely on the model’s pretrained knowledge.

## Contents of the project

### Conversational interface

Provides an API interface which allows the caller to interact with the LLM.
The API should also accept a session(cookie) identifier of some sort so that the user can run multiple isolated chats in parallel.

### Persistance of chats (WIP)

The system also persists data in a local DB (maybe extend to also include a cloud-hosted DB?) with conversation details -> **TO BE DESIGNED**

### Controlled local knowledge access

The system allows the user to define the documents that are available for the LLM when building a response.
The user should explicitly select files/folders that are allowed to be accessed by the LLM.
**TODO: Think about indexing/sharding for performance optimization**

### Implement Retreival-augmented generation

Has a RAG pipeline that enhances(augments) user's queries with the relevant context from allowed documents.
With this larger context LLM should generate better responses, while prioritizing this retreived context over it's trained knoweldge.
The System is also available of referencing the source files where the LLM got the information for it's responses.

### Plugable backend apapters

The system has a plugable backend so that there is possible swapping of local/cloud-hosted models.

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
