"""Helper utilities for handling document uploads."""
from __future__ import annotations

import hashlib
import os

from werkzeug.datastructures import FileStorage


ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/markdown",
    "text/x-markdown",
    "text/plain",
}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}
MAX_DOCUMENT_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB limit for now


class DocumentUploadError(Exception):
    """Wraps validation failures for document uploads."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def extract_upload_from_request(upload: FileStorage | None) -> FileStorage:
    """Validate the uploaded file presence/filename."""

    if upload is None:
        raise DocumentUploadError("file is required")
    filename = (upload.filename or "").strip()
    if not filename:
        raise DocumentUploadError("filename is required")
    return upload


def prepare_document_payload(upload: FileStorage):
    """Validate file size/type and build Document constructor payload."""

    filename = (upload.filename or "").strip()
    mime_type = (upload.mimetype or "").lower()
    _, ext = os.path.splitext(filename.lower())

    if ext not in ALLOWED_DOCUMENT_EXTENSIONS and mime_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        raise DocumentUploadError("unsupported file type")

    data = upload.read()
    if not data:
        raise DocumentUploadError("file is empty")
    if len(data) > MAX_DOCUMENT_SIZE_BYTES:
        raise DocumentUploadError("file exceeds size limit")

    checksum = hashlib.sha256(data).hexdigest()
    resolved_mime = mime_type or "application/octet-stream"

    return {
        "filename": filename,
        "mime_type": resolved_mime,
        "size_bytes": len(data),
        "checksum": checksum,
        "storage_data": data,
    }


__all__ = [
    "ALLOWED_DOCUMENT_EXTENSIONS",
    "ALLOWED_DOCUMENT_MIME_TYPES",
    "MAX_DOCUMENT_SIZE_BYTES",
    "DocumentUploadError",
    "extract_upload_from_request",
    "prepare_document_payload",
]
