"""
Local chat log import utilities for offline VOD analysis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.vod_models import ChatMessage


def _parse_chat_obj(obj: dict[str, Any], idx: int) -> ChatMessage:
    """
    Parse a single chat object into ChatMessage with indexed error context.
    """
    if "timestamp_s" not in obj:
        raise ValueError(f"chat record at index {idx} missing required key 'timestamp_s'")
    if "message" not in obj:
        raise ValueError(f"chat record at index {idx} missing required key 'message'")

    timestamp = obj["timestamp_s"]
    if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
        raise ValueError(
            f"chat record at index {idx} has invalid 'timestamp_s' type; expected number"
        )

    message = obj["message"]
    if not isinstance(message, str):
        raise ValueError(f"chat record at index {idx} has invalid 'message' type; expected string")

    try:
        return ChatMessage(timestamp_s=float(timestamp), message=message)
    except ValueError as exc:
        raise ValueError(f"chat record at index {idx} is invalid: {exc}") from exc


def _load_jsonl_messages(text: str) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_no}: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"line {line_no} must be a JSON object")
        messages.append(_parse_chat_obj(parsed, line_no))
    return messages


def _load_json_array_messages(text: str) -> list[ChatMessage]:
    try:
        parsed_json = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc

    if not isinstance(parsed_json, list):
        raise ValueError("JSON chat file must contain an array of objects")

    messages: list[ChatMessage] = []
    for idx, item in enumerate(parsed_json):
        if not isinstance(item, dict):
            raise ValueError(f"chat record at index {idx} must be an object")
        messages.append(_parse_chat_obj(item, idx))
    return messages


def load_chat_messages(path: str) -> list[ChatMessage]:
    """
    Load chat messages from local .jsonl or .json file.
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix not in {".jsonl", ".json"}:
        raise ValueError("unsupported chat file extension; expected .jsonl or .json")

    text = file_path.read_text(encoding="utf-8")
    if text.strip() == "":
        return []

    if suffix == ".jsonl":
        return _load_jsonl_messages(text)

    return _load_json_array_messages(text)
