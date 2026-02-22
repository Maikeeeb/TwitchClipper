"""
Test Plan
- Partitions: happy path done, failed job status, argument validation
- Boundaries: minimal required args and required --vod-url enforcement
- Failure modes: API-reported failure causes non-zero exit
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is first on path so cli.main resolves.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from cli.main import main


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


def test_cli_vod_highlights_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validation: CLI submits job, drives run-next loop, exits 0 on done."""
    post_calls: list[str] = []
    statuses = iter(["running", "done"])

    def _fake_post(url: str, **kwargs):
        post_calls.append(url)
        if url.endswith("/jobs/vod-highlights"):
            return _FakeResponse({"job_id": "job-1"})
        if url.endswith("/jobs/run-next"):
            return _FakeResponse({"processed": 1, "status": "done", "job_id": "job-1"})
        raise AssertionError(f"unexpected POST url: {url}")

    def _fake_get(url: str, **kwargs):
        if not url.endswith("/jobs/job-1"):
            raise AssertionError(f"unexpected GET url: {url}")
        status = next(statuses)
        if status == "done":
            return _FakeResponse(
                {
                    "status": "done",
                    "result": {
                        "montage_path": "/tmp/montage.mp4",
                        "clips_dir": "/tmp/clips",
                    },
                }
            )
        return _FakeResponse({"status": "running", "result": None})

    monkeypatch.setattr("requests.post", _fake_post)
    monkeypatch.setattr("requests.get", _fake_get)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    exit_code = main(
        [
            "vod-highlights",
            "--vod-url",
            "https://www.twitch.tv/videos/123",
            "--api-base-url",
            "http://api",
        ]
    )
    assert exit_code == 0
    assert any(url.endswith("/jobs/vod-highlights") for url in post_calls)


def test_cli_vod_highlights_failed_job_exits_non_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defect: failed job status returns exit code 1."""
    def _fake_post(url: str, **kwargs):
        if url.endswith("/jobs/vod-highlights"):
            return _FakeResponse({"job_id": "job-2"})
        if url.endswith("/jobs/run-next"):
            return _FakeResponse({"processed": 1, "status": "failed", "job_id": "job-2"})
        raise AssertionError(f"unexpected POST url: {url}")

    def _fake_get(url: str, **kwargs):
        if not url.endswith("/jobs/job-2"):
            raise AssertionError(f"unexpected GET url: {url}")
        return _FakeResponse({"status": "failed", "error": "pipeline failed", "result": None})

    monkeypatch.setattr("requests.post", _fake_post)
    monkeypatch.setattr("requests.get", _fake_get)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    exit_code = main(
        [
            "vod-highlights",
            "--vod-url",
            "https://www.twitch.tv/videos/123",
            "--api-base-url",
            "http://api",
        ]
    )
    assert exit_code == 1


def test_cli_vod_highlights_requires_vod_url() -> None:
    """Boundary: argparse rejects missing required --vod-url."""
    with pytest.raises(SystemExit):
        main(["vod-highlights"])
