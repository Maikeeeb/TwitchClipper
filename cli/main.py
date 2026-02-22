from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import requests


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI client for TwitchClipper API jobs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    vod = subparsers.add_parser(
        "vod-highlights",
        help="Submit a VOD highlights pipeline job via API and wait for completion.",
    )
    vod.add_argument("--vod-url", required=True, help="Twitch VOD URL or local file path")
    vod.add_argument("--output-dir", default=".", help="Output directory for job artifacts")
    vod.add_argument(
        "--keyword",
        dest="keywords",
        action="append",
        default=[],
        help="Keyword used in ranking (repeatable).",
    )
    vod.add_argument("--chat-path", default=None, help="Optional pre-fetched local chat JSONL path")
    vod.add_argument("--min-count", type=int, default=1)
    vod.add_argument("--spike-window-seconds", type=int, default=30)
    vod.add_argument("--segment-padding-seconds", type=int, default=20)
    vod.add_argument("--max-segment-seconds", type=float, default=120)
    vod.add_argument("--diversity-windows", type=int, default=8)
    vod.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    vod.add_argument("--poll-interval-seconds", type=float, default=1.0)
    vod.add_argument("--run-next-interval-seconds", type=float, default=0.2)
    vod.add_argument("--timeout-seconds", type=int, default=3600)
    return parser


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def _submit_vod_highlights(base_url: str, payload: dict[str, Any]) -> str:
    response = requests.post(
        _join_url(base_url, "/jobs/vod-highlights"),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    job_id = data.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise RuntimeError("API response missing valid job_id")
    return job_id


def _run_next(base_url: str) -> dict[str, Any]:
    response = requests.post(_join_url(base_url, "/jobs/run-next"), timeout=30)
    response.raise_for_status()
    return response.json()


def _get_job(base_url: str, job_id: str) -> dict[str, Any]:
    response = requests.get(_join_url(base_url, f"/jobs/{job_id}"), timeout=30)
    response.raise_for_status()
    return response.json()


def _handle_vod_highlights(args: argparse.Namespace) -> int:
    payload = {
        "vod_url": args.vod_url,
        "output_dir": args.output_dir,
        "keywords": args.keywords,
        "chat_path": args.chat_path,
        "min_count": args.min_count,
        "spike_window_seconds": args.spike_window_seconds,
        "segment_padding_seconds": args.segment_padding_seconds,
        "max_segment_seconds": args.max_segment_seconds,
        "diversity_windows": args.diversity_windows,
    }

    job_id = _submit_vod_highlights(args.api_base_url, payload)
    print(f"Submitted job_id={job_id}")

    started = time.time()
    while True:
        if time.time() - started > float(args.timeout_seconds):
            print("Timed out waiting for job completion.", file=sys.stderr)
            return 2

        _run_next(args.api_base_url)
        job = _get_job(args.api_base_url, job_id)
        status = str(job.get("status", "")).lower()
        print(f"status={status}")

        if status == "done":
            result = job.get("result") or {}
            print(json.dumps(result, indent=2))
            return 0

        if status == "failed":
            error = job.get("error") or "unknown error"
            print(f"Job failed: {error}", file=sys.stderr)
            return 1

        time.sleep(float(args.run_next_interval_seconds))
        time.sleep(float(args.poll_interval_seconds))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "vod-highlights":
        return _handle_vod_highlights(args)
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
