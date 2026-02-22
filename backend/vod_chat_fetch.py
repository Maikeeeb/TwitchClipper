"""
Best-effort Twitch web VOD chat fetcher.

This module intentionally uses Twitch web endpoints (GraphQL used by the browser app),
not official Helix APIs. The endpoint shape can change at any time.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests

GQL_ENDPOINT = "https://gql.twitch.tv/gql"
# Public web client identifier used by the Twitch website client, not a developer app key.
WEB_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
REQUIRED_JSONL_KEYS = ("vod_id", "offset_s", "created_at", "user_name", "message")


class TwitchWebChatError(RuntimeError):
    """Raised when Twitch web chat replay cannot be fetched safely."""


def resolve_vod_id(vod_url_or_id: str) -> str:
    """Resolve a Twitch VOD id from a numeric id or twitch.tv/videos URL."""
    candidate = vod_url_or_id.strip()
    if not candidate:
        raise ValueError("vod_url_or_id must not be empty")
    if candidate.isdigit():
        return candidate

    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        host = parsed.netloc.lower()
        if "twitch.tv" not in host:
            raise ValueError("vod_url_or_id must be a Twitch VOD URL or numeric VOD id")
        match = re.search(r"/videos/(\d+)", parsed.path)
        if match:
            return match.group(1)
        raise ValueError("could not parse VOD id from Twitch URL path")

    match = re.search(r"(?:^|/)videos/(\d+)(?:$|[/?#])", candidate)
    if match:
        return match.group(1)
    raise ValueError("vod_url_or_id must be a Twitch VOD URL or numeric VOD id")


def build_gql_payload(
    vod_id: str,
    *,
    cursor: str | None = None,
    content_offset_seconds: float | None = None,
    page_size: int = 50,
) -> dict[str, Any]:
    """
    Build the Twitch web GraphQL payload for VOD comments.

    If Twitch changes the expected payload schema, update this function.
    """
    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be between 1 and 100")
    if cursor is None and content_offset_seconds is None:
        raise ValueError("content_offset_seconds is required when cursor is not provided")

    offset_int = None
    if content_offset_seconds is not None:
        offset_int = max(0, int(content_offset_seconds))

    variables: dict[str, Any] = {
        "videoID": str(vod_id),
        "first": int(page_size),
        "cursor": cursor,
        "contentOffsetSeconds": offset_int,
    }
    query = """
query VideoCommentsByOffsetOrCursor(
  $videoID: ID!,
  $cursor: Cursor,
  $contentOffsetSeconds: Int,
  $first: Int!
) {
  video(id: $videoID) {
    comments(
      first: $first,
      after: $cursor,
      contentOffsetSeconds: $contentOffsetSeconds
    ) {
      edges {
        cursor
        node {
          id
          createdAt
          contentOffsetSeconds
          commenter {
            id
            login
            displayName
          }
          message {
            fragments {
              text
            }
            userBadges {
              id
              setID
              version
            }
          }
        }
      }
      pageInfo {
        hasNextPage
      }
    }
  }
}
""".strip()
    return {
        "operationName": "VideoCommentsByOffsetOrCursor",
        "query": query,
        "variables": variables,
    }


def _extract_message_text(node: dict[str, Any]) -> str:
    message_obj = node.get("message")
    if isinstance(message_obj, dict):
        body = message_obj.get("body")
        if isinstance(body, str):
            return body
        fragments = message_obj.get("fragments")
        if isinstance(fragments, list):
            text_parts: list[str] = []
            for fragment in fragments:
                if isinstance(fragment, dict):
                    text = fragment.get("text")
                    if isinstance(text, str):
                        text_parts.append(text)
            if text_parts:
                return "".join(text_parts)
    legacy_body = node.get("message", "")
    if isinstance(legacy_body, str):
        return legacy_body
    return ""


def _normalize_comment(vod_id: str, node: dict[str, Any]) -> dict[str, Any]:
    commenter = node.get("commenter")
    commenter_dict = commenter if isinstance(commenter, dict) else {}
    message_obj = node.get("message")
    message_dict = message_obj if isinstance(message_obj, dict) else {}

    user_name = commenter_dict.get("displayName") or commenter_dict.get("login") or ""
    normalized: dict[str, Any] = {
        "vod_id": str(vod_id),
        "offset_s": float(node.get("contentOffsetSeconds", 0.0)),
        "created_at": str(node.get("createdAt", "")),
        "user_name": str(user_name),
        "message": _extract_message_text(node),
    }

    user_id = commenter_dict.get("id")
    if user_id is not None:
        normalized["user_id"] = str(user_id)
    comment_id = node.get("id")
    if comment_id is not None:
        normalized["comment_id"] = str(comment_id)
    badges = message_dict.get("userBadges")
    if isinstance(badges, list):
        normalized["badges"] = badges
    fragments = message_dict.get("fragments")
    if isinstance(fragments, list):
        normalized["fragments"] = fragments
    normalized["raw"] = node
    return normalized


def _extract_edges(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    data_obj = payload.get("data")
    if not isinstance(data_obj, dict):
        raise TwitchWebChatError(
            "Twitch web chat endpoint changed: missing 'data'. "
            "Update build_gql_payload()."
        )
    video_obj = data_obj.get("video")
    if video_obj is None:
        return [], False
    if not isinstance(video_obj, dict):
        raise TwitchWebChatError(
            "Twitch web chat endpoint changed: 'video' shape is unexpected. "
            "Update build_gql_payload()."
        )
    comments_obj = video_obj.get("comments")
    if comments_obj is None:
        return [], False
    if not isinstance(comments_obj, dict):
        raise TwitchWebChatError(
            "Twitch web chat endpoint changed: 'comments' shape is unexpected. "
            "Update build_gql_payload()."
        )
    edges = comments_obj.get("edges")
    if edges is None:
        return [], False
    if not isinstance(edges, list):
        raise TwitchWebChatError(
            "Twitch web chat endpoint changed: 'edges' shape is unexpected. "
            "Update build_gql_payload()."
        )
    page_info = comments_obj.get("pageInfo")
    has_next_page = False
    if isinstance(page_info, dict):
        has_next_page = bool(page_info.get("hasNextPage"))
    return [edge for edge in edges if isinstance(edge, dict)], has_next_page


def _has_integrity_error(payload: dict[str, Any]) -> bool:
    errors = payload.get("errors")
    if not isinstance(errors, list):
        return False
    for error in errors:
        if not isinstance(error, dict):
            continue
        message = error.get("message")
        if isinstance(message, str) and "failed integrity check" in message.lower():
            return True
    return False


def _has_transient_graphql_error(payload: dict[str, Any]) -> bool:
    """Return True for retryable GraphQL errors (for example, service timeout)."""
    errors = payload.get("errors")
    if not isinstance(errors, list):
        return False
    for error in errors:
        if not isinstance(error, dict):
            continue
        message = error.get("message")
        if not isinstance(message, str):
            continue
        lower = message.lower()
        if "service timeout" in lower or "timed out" in lower:
            return True
    return False


def _raise_graphql_error(payload: dict[str, Any]) -> None:
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors:
        return
    first_message = None
    first = errors[0]
    if isinstance(first, dict):
        message = first.get("message")
        if isinstance(message, str):
            first_message = message
    details = f" First error: {first_message}" if first_message else ""
    raise TwitchWebChatError(
        "Twitch web chat endpoint returned GraphQL errors. "
        "If payload format changed, update build_gql_payload()." + details
    )


def _post_gql_with_retries(
    *,
    session: requests.Session,
    payload: dict[str, Any],
    retries_5xx: int = 2,
) -> dict[str, Any]:
    headers = {
        "Client-Id": WEB_CLIENT_ID,
        "Content-Type": "application/json",
    }
    last_exception: Exception | None = None
    for attempt in range(retries_5xx + 1):
        try:
            response = session.post(
                GQL_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=20,
            )
        except requests.RequestException as exc:
            last_exception = exc
            if attempt >= retries_5xx:
                break
            time.sleep(0.25 * (attempt + 1))
            continue

        if response.status_code == 429:
            raise TwitchWebChatError(
                "Rate limited by Twitch web chat endpoint. Please retry later."
            )
        if 500 <= response.status_code <= 599:
            if attempt >= retries_5xx:
                raise TwitchWebChatError(
                    "Twitch web chat endpoint failed repeatedly with server errors."
                )
            time.sleep(0.25 * (attempt + 1))
            continue
        if response.status_code >= 400:
            raise TwitchWebChatError(
                f"Twitch web chat endpoint returned HTTP {response.status_code}."
            )
        try:
            payload_json = response.json()
        except ValueError as exc:
            raise TwitchWebChatError(
                "Twitch web chat endpoint changed: response is not valid JSON. "
                "Update build_gql_payload()."
            ) from exc
        if isinstance(payload_json, list):
            if not payload_json:
                return {}
            first = payload_json[0]
            if isinstance(first, dict):
                return first
            raise TwitchWebChatError(
                "Twitch web chat endpoint changed: list payload shape is unexpected. "
                "Update build_gql_payload()."
            )
        if isinstance(payload_json, dict):
            return payload_json
        raise TwitchWebChatError(
            "Twitch web chat endpoint changed: payload type is unexpected. "
            "Update build_gql_payload()."
        )

    raise TwitchWebChatError(f"Failed to reach Twitch web chat endpoint: {last_exception}")


def fetch_vod_chat_messages_web(
    vod_id: str,
    *,
    session: requests.Session | None = None,
    start_offset_s: float | None = None,
    end_offset_s: float | None = None,
    page_size: int = 50,
    max_pages: int | None = None,
) -> Iterable[dict[str, Any]]:
    """Fetch and yield normalized VOD chat messages from Twitch web GraphQL."""
    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be between 1 and 100")
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be >= 1")
    if start_offset_s is not None and start_offset_s < 0:
        raise ValueError("start_offset_s must be >= 0")
    if end_offset_s is not None and end_offset_s < 0:
        raise ValueError("end_offset_s must be >= 0")
    if (
        start_offset_s is not None
        and end_offset_s is not None
        and end_offset_s < start_offset_s
    ):
        raise ValueError("end_offset_s must be >= start_offset_s")

    start_value = float(start_offset_s) if start_offset_s is not None else 0.0
    active_session = session or requests.Session()
    cursor: str | None = None
    current_offset = start_value
    use_cursor = True

    pages_fetched = 0
    while True:
        if max_pages is not None and pages_fetched >= max_pages:
            break
        payload = build_gql_payload(
            vod_id,
            cursor=cursor if use_cursor and cursor is not None else None,
            content_offset_seconds=(
                current_offset if (not use_cursor or cursor is None) else None
            ),
            page_size=page_size,
        )
        gql_payload: dict[str, Any] | None = None
        page_error: TwitchWebChatError | None = None
        for page_attempt in range(4):
            candidate = _post_gql_with_retries(session=active_session, payload=payload)
            if "errors" not in candidate:
                gql_payload = candidate
                break
            if use_cursor and cursor is not None and _has_integrity_error(candidate):
                gql_payload = candidate
                break
            if _has_transient_graphql_error(candidate) and page_attempt < 3:
                time.sleep(0.25 * (page_attempt + 1))
                continue
            page_error = TwitchWebChatError(
                "Twitch web chat endpoint returned GraphQL errors. "
                "If payload format changed, update build_gql_payload()."
            )
            gql_payload = candidate
            break

        if gql_payload is None:
            if page_error is not None:
                raise page_error
            raise TwitchWebChatError("Unexpected empty GraphQL payload during page retry loop.")

        if "errors" in gql_payload:
            if use_cursor and cursor is not None and _has_integrity_error(gql_payload):
                use_cursor = False
                continue
            _raise_graphql_error(gql_payload)

        edges, has_next_page = _extract_edges(gql_payload)
        if not edges:
            break

        last_cursor: str | None = None
        should_stop = False
        page_max_offset = current_offset
        for edge in edges:
            edge_cursor = edge.get("cursor")
            if isinstance(edge_cursor, str):
                last_cursor = edge_cursor
            node = edge.get("node")
            if not isinstance(node, dict):
                continue
            normalized = _normalize_comment(vod_id, node)
            offset_s = float(normalized["offset_s"])
            page_max_offset = max(page_max_offset, offset_s)
            if start_offset_s is not None and offset_s < float(start_offset_s):
                continue
            if end_offset_s is not None and offset_s > float(end_offset_s):
                should_stop = True
                break
            yield normalized

        if should_stop:
            break
        if not has_next_page:
            break

        next_offset = max(current_offset + 1.0, float(int(page_max_offset) + 1))
        if use_cursor and last_cursor:
            cursor = last_cursor
            current_offset = next_offset
            pages_fetched += 1
            continue

        use_cursor = False
        current_offset = next_offset
        pages_fetched += 1


def write_chat_jsonl(messages: Iterable[dict[str, Any]], out_path: Path) -> dict[str, Any]:
    """Write normalized chat messages to JSONL and return a compact summary."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    messages_written = 0
    first_offset_s: float | None = None
    last_offset_s: float | None = None
    vod_id: str | None = None

    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for message in messages:
            missing = [key for key in REQUIRED_JSONL_KEYS if key not in message]
            if missing:
                raise ValueError(f"message missing required keys for JSONL output: {missing}")
            offset_s = float(message["offset_s"])
            if first_offset_s is None:
                first_offset_s = offset_s
            last_offset_s = offset_s
            vod_id = str(message["vod_id"])
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")
            messages_written += 1

    return {
        "vod_id": vod_id,
        "messages_written": messages_written,
        "first_offset_s": first_offset_s,
        "last_offset_s": last_offset_s,
        "out_path": str(out_path),
    }


def fetch_vod_chat_to_jsonl(
    vod_url_or_id: str,
    out_path: Path,
    *,
    session: requests.Session | None = None,
    start_offset_s: float | None = None,
    end_offset_s: float | None = None,
    page_size: int = 50,
    max_pages: int | None = None,
) -> dict[str, Any]:
    """Resolve VOD id, fetch Twitch web chat replay, and write normalized JSONL."""
    vod_id = resolve_vod_id(vod_url_or_id)
    messages = fetch_vod_chat_messages_web(
        vod_id,
        session=session,
        start_offset_s=start_offset_s,
        end_offset_s=end_offset_s,
        page_size=page_size,
        max_pages=max_pages,
    )
    summary = write_chat_jsonl(messages, out_path)
    summary["vod_id"] = vod_id
    return summary


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Twitch VOD chat replay into JSONL.")
    parser.add_argument("--vod", required=True, help="Twitch VOD id or URL")
    parser.add_argument("--out", required=True, help="Output JSONL file path")
    parser.add_argument("--start-offset-s", type=float, default=None)
    parser.add_argument("--end-offset-s", type=float, default=None)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional page cap (default: unlimited).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for best-effort Twitch web chat replay fetch."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if os.getenv("RUN_TWITCH_WEB_FETCH") != "1":
        parser.error(
            "Real Twitch web chat fetch is disabled by default. "
            "Set RUN_TWITCH_WEB_FETCH=1 to allow manual web fetch."
        )

    summary = fetch_vod_chat_to_jsonl(
        args.vod,
        Path(args.out),
        start_offset_s=args.start_offset_s,
        end_offset_s=args.end_offset_s,
        page_size=args.page_size,
        max_pages=args.max_pages,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
