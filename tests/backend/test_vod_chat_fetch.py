"""
Test Plan
- Partitions: happy path multi-page cursor flow, empty chat, range-filtered subset, JSONL write
- Boundaries: end_offset_s stopping behavior, required JSONL keys presence
- Failure modes: non-Twitch/non-id input validation and deterministic no-network behavior via mocks
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests

from backend.vod_chat_fetch import (
    fetch_vod_chat_messages_web,
    fetch_vod_chat_to_jsonl,
    resolve_vod_id,
    write_chat_jsonl,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def _comments_payload(edges: list[dict[str, Any]], has_next_page: bool) -> dict[str, Any]:
    return {
        "data": {
            "video": {
                "comments": {
                    "edges": edges,
                    "pageInfo": {"hasNextPage": has_next_page},
                }
            }
        }
    }


def _edge(cursor: str, comment_id: str, offset_s: float, user_name: str, text: str) -> dict[str, Any]:
    return {
        "cursor": cursor,
        "node": {
            "id": comment_id,
            "createdAt": "2025-01-01T00:00:00Z",
            "contentOffsetSeconds": offset_s,
            "commenter": {
                "id": f"user-{user_name}",
                "displayName": user_name,
                "login": user_name.lower(),
            },
            "message": {
                "fragments": [{"text": text}],
                "userBadges": [{"id": "subscriber", "version": "1"}],
            },
        },
    }


def test_resolve_vod_id_accepts_numeric_and_url() -> None:
    # Covers: TODO-VOD-012
    assert resolve_vod_id("2699448530") == "2699448530"
    assert (
        resolve_vod_id("https://www.twitch.tv/videos/2699448530?filter=archives")
        == "2699448530"
    )


def test_resolve_vod_id_rejects_invalid_input() -> None:
    # Covers: TODO-VOD-012
    with pytest.raises(ValueError, match="Twitch VOD URL or numeric VOD id"):
        resolve_vod_id("https://example.com/videos/123")


def test_fetch_vod_chat_messages_web_multi_page_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: TODO-VOD-012
    responses = [
        _FakeResponse(
            200,
            _comments_payload(
                [
                    _edge("cursor-1", "c1", 1.0, "Alpha", "first"),
                    _edge("cursor-2", "c2", 2.0, "Beta", "second"),
                ],
                has_next_page=True,
            ),
        ),
        _FakeResponse(
            200,
            _comments_payload(
                [_edge("cursor-3", "c3", 3.0, "Gamma", "third")],
                has_next_page=False,
            ),
        ),
    ]
    recorded_payloads: list[dict[str, Any]] = []

    def _fake_post(
        self: requests.Session,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> _FakeResponse:
        assert "Client-Id" in headers
        assert url.endswith("/gql")
        assert timeout == 20
        recorded_payloads.append(json)
        return responses.pop(0)

    monkeypatch.setattr(requests.Session, "post", _fake_post)

    messages = list(fetch_vod_chat_messages_web("2699448530", page_size=2, max_pages=5))
    assert [msg["message"] for msg in messages] == ["first", "second", "third"]
    assert messages[0]["vod_id"] == "2699448530"
    assert messages[1]["user_name"] == "Beta"
    assert "raw" in messages[2]
    assert recorded_payloads[0]["variables"]["contentOffsetSeconds"] == pytest.approx(0.0)
    assert recorded_payloads[1]["variables"]["cursor"] == "cursor-2"


def test_fetch_vod_chat_messages_web_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: TODO-VOD-012
    def _fake_post(
        self: requests.Session,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> _FakeResponse:
        return _FakeResponse(200, _comments_payload([], has_next_page=False))

    monkeypatch.setattr(requests.Session, "post", _fake_post)
    messages = list(fetch_vod_chat_messages_web("2699448530"))
    assert messages == []


def test_fetch_vod_chat_messages_web_range_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: TODO-VOD-012
    response = _FakeResponse(
        200,
        _comments_payload(
            [
                _edge("cursor-1", "c1", 10.0, "A", "ten"),
                _edge("cursor-2", "c2", 20.0, "B", "twenty"),
                _edge("cursor-3", "c3", 30.0, "C", "thirty"),
            ],
            has_next_page=False,
        ),
    )

    def _fake_post(
        self: requests.Session,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> _FakeResponse:
        return response

    monkeypatch.setattr(requests.Session, "post", _fake_post)

    messages = list(
        fetch_vod_chat_messages_web(
            "2699448530",
            start_offset_s=15.0,
            end_offset_s=20.0,
        )
    )
    assert len(messages) == 1
    assert messages[0]["offset_s"] == pytest.approx(20.0)
    assert messages[0]["message"] == "twenty"


def test_write_chat_jsonl_writes_required_shape(tmp_path: Path) -> None:
    # Covers: TODO-VOD-012
    out_file = tmp_path / "chat.jsonl"
    messages = [
        {
            "vod_id": "2699448530",
            "offset_s": 1.0,
            "created_at": "2025-01-01T00:00:00Z",
            "user_name": "UserOne",
            "message": "hello",
            "comment_id": "c1",
        },
        {
            "vod_id": "2699448530",
            "offset_s": 2.5,
            "created_at": "2025-01-01T00:00:01Z",
            "user_name": "UserTwo",
            "message": "world",
        },
    ]

    summary = write_chat_jsonl(messages, out_file)
    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert summary["messages_written"] == 2
    assert summary["first_offset_s"] == pytest.approx(1.0)
    assert summary["last_offset_s"] == pytest.approx(2.5)
    assert len(lines) == 2
    for line in lines:
        parsed = json.loads(line)
        assert parsed["vod_id"] == "2699448530"
        assert "offset_s" in parsed
        assert "created_at" in parsed
        assert "user_name" in parsed
        assert "message" in parsed


def test_fetch_vod_chat_to_jsonl_orchestrates_fetch_and_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Covers: TODO-VOD-012
    response = _FakeResponse(
        200,
        _comments_payload([_edge("cursor-1", "c1", 4.0, "Solo", "one-line")], False),
    )

    def _fake_post(
        self: requests.Session,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> _FakeResponse:
        return response

    monkeypatch.setattr(requests.Session, "post", _fake_post)
    output = tmp_path / "vod_chat.jsonl"
    summary = fetch_vod_chat_to_jsonl("https://www.twitch.tv/videos/2699448530", output)
    assert summary["vod_id"] == "2699448530"
    assert summary["messages_written"] == 1
    assert output.exists()
