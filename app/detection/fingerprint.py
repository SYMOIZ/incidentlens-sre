"""Fingerprint helpers — group related error logs without storing PII-heavy raw text keys."""

from __future__ import annotations

import hashlib
import re

from app.models.schemas import LogEntry

# Collapse volatile tokens so "timeout id=abc" and "timeout id=xyz" share a fingerprint.
_HEX_ID = re.compile(r"\b[0-9a-f]{8,}\b", re.IGNORECASE)
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_NUMBERS = re.compile(r"\b\d+\b")
_WHITESPACE = re.compile(r"\s+")


def normalize_message(message: str) -> str:
    text = message.strip().lower()
    text = _UUID.sub("<uuid>", text)
    text = _HEX_ID.sub("<id>", text)
    text = _NUMBERS.sub("<n>", text)
    return _WHITESPACE.sub(" ", text)


def fingerprint_for_log(entry: LogEntry) -> str:
    material = f"{entry.service}|{entry.level}|{normalize_message(entry.message)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
