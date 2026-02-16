"""
Test Plan
- Partitions: JSONL vs JSON-array happy path and malformed input paths
- Boundaries: empty file, missing fields, unsupported extension
- Failure modes: invalid JSON, invalid record values, invalid top-level JSON shape

Covers: TODO-VOD-005
"""

import json
from pathlib import Path

import pytest

from backend.chat_import import load_chat_messages


def test_load_chat_messages_jsonl_empty_file_returns_empty(tmp_path: Path) -> None:
    """Empty JSONL file returns an empty message list."""
    path = tmp_path / "chat.jsonl"
    path.write_text("", encoding="utf-8")
    assert load_chat_messages(str(path)) == []


def test_load_chat_messages_jsonl_parses_messages(tmp_path: Path) -> None:
    """JSONL records parse into ChatMessage objects in file order."""
    path = tmp_path / "chat.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"timestamp_s": 1, "message": "hello", "extra": "ignored"}),
                json.dumps({"timestamp_s": 2.5, "message": "pog"}),
            ]
        ),
        encoding="utf-8",
    )
    messages = load_chat_messages(str(path))
    assert [m.timestamp_s for m in messages] == pytest.approx([1.0, 2.5])
    assert [m.message for m in messages] == ["hello", "pog"]


def test_load_chat_messages_jsonl_invalid_json_raises(tmp_path: Path) -> None:
    """Malformed JSONL line returns a line-specific error."""
    path = tmp_path / "chat.jsonl"
    path.write_text('{"timestamp_s": 1, "message": "ok"}\n{"timestamp_s": ', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_chat_messages(str(path))


def test_load_chat_messages_jsonl_missing_fields_raises(tmp_path: Path) -> None:
    """Missing required fields in JSONL object is rejected."""
    path = tmp_path / "chat.jsonl"
    path.write_text(json.dumps({"timestamp_s": 1.0}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required key 'message'"):
        load_chat_messages(str(path))


def test_load_chat_messages_jsonl_negative_timestamp_raises(tmp_path: Path) -> None:
    """ChatMessage validation rejects negative timestamps."""
    path = tmp_path / "chat.jsonl"
    path.write_text(json.dumps({"timestamp_s": -1, "message": "bad"}), encoding="utf-8")
    with pytest.raises(ValueError, match="index 1"):
        load_chat_messages(str(path))


def test_load_chat_messages_jsonl_empty_message_raises(tmp_path: Path) -> None:
    """ChatMessage validation rejects empty messages."""
    path = tmp_path / "chat.jsonl"
    path.write_text(json.dumps({"timestamp_s": 1, "message": "   "}), encoding="utf-8")
    with pytest.raises(ValueError, match="index 1"):
        load_chat_messages(str(path))


def test_load_chat_messages_json_array_parses_messages(tmp_path: Path) -> None:
    """JSON array format parses valid chat objects."""
    path = tmp_path / "chat.json"
    path.write_text(
        json.dumps(
            [
                {"timestamp_s": 0, "message": "start"},
                {"timestamp_s": 9.25, "message": "wow", "foo": 123},
            ]
        ),
        encoding="utf-8",
    )
    messages = load_chat_messages(str(path))
    assert [m.timestamp_s for m in messages] == pytest.approx([0.0, 9.25])
    assert [m.message for m in messages] == ["start", "wow"]


def test_load_chat_messages_json_array_not_array_raises(tmp_path: Path) -> None:
    """Top-level JSON must be an array for .json format."""
    path = tmp_path / "chat.json"
    path.write_text(json.dumps({"timestamp_s": 1, "message": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="array"):
        load_chat_messages(str(path))


def test_load_chat_messages_unsupported_extension_raises(tmp_path: Path) -> None:
    """Unsupported file extension fails fast with clear error."""
    path = tmp_path / "chat.txt"
    path.write_text("ignored", encoding="utf-8")
    with pytest.raises(ValueError, match="expected \\.jsonl or \\.json"):
        load_chat_messages(str(path))
