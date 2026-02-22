# Covers: TODO-VOD-011
"""
Test Plan
Partitions:
- Happy path end-to-end job flow
- With fake local chat input
- Using synthetic mp4
Boundaries:
- Job initially QUEUED
- RUNNING during worker execution
- DONE when montage produced
Failure modes:
- Missing result paths
- Status never transitions
- Clips dir empty
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure project root is first on path so api.app resolves (pytest may prepend test dir)
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from api.app import create_app, get_now


def _fixed_now() -> datetime:
    return datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _write_fake_vod(path: Path) -> None:
    """Create a tiny local .mp4 placeholder for offline local-path download."""
    path.write_bytes(b"not-a-real-video-but-sufficient-for-local-copy-test")


def _write_fake_chat_jsonl(path: Path) -> None:
    """Generate deterministic chat with quiet + burst windows to force spike detection."""
    base = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    records: list[dict[str, object]] = []

    # Quiet from 0-20s.
    for second in range(0, 21, 2):
        records.append(
            {
                "vod_id": "999999",
                "offset_s": float(second),
                "timestamp_s": float(second),
                "created_at": (base + timedelta(seconds=second)).isoformat(),
                "user_name": "quiet_user",
                "message": "quiet",
            }
        )

    # Burst around 30s.
    for idx in range(45):
        offset = 30.0 + (idx % 3) * 0.25
        records.append(
            {
                "vod_id": "999999",
                "offset_s": offset,
                "timestamp_s": offset,
                "created_at": (base + timedelta(seconds=int(offset))).isoformat(),
                "user_name": f"burst_a_{idx}",
                "message": "wow insane play",
            }
        )

    # Quiet 40-60s.
    for second in range(40, 61, 5):
        records.append(
            {
                "vod_id": "999999",
                "offset_s": float(second),
                "timestamp_s": float(second),
                "created_at": (base + timedelta(seconds=second)).isoformat(),
                "user_name": "quiet_user",
                "message": "calm",
            }
        )

    # Burst around 70s.
    for idx in range(45):
        offset = 70.0 + (idx % 4) * 0.2
        records.append(
            {
                "vod_id": "999999",
                "offset_s": offset,
                "timestamp_s": offset,
                "created_at": (base + timedelta(seconds=int(offset))).isoformat(),
                "user_name": f"burst_b_{idx}",
                "message": "insane wow moment",
            }
        )

    lines = [json.dumps(record) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_vod_highlights_job_e2e_offline(tmp_path, monkeypatch) -> None:
    """
    End-to-end via API + worker dev flow:
    submit vod_highlights -> run-next -> done with materialized output files.
    """

    # Heavy video stages are mocked to keep this test fully offline and deterministic.
    def _mock_cut_segments(vod_path, segments, *, output_dir, max_segments=None, **_kwargs):
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        selected = segments if max_segments is None else segments[: int(max_segments)]
        out_paths: list[str] = []
        for idx, _segment in enumerate(selected):
            p = output / f"segment_{idx:03d}.mp4"
            p.write_bytes(b"fake-clip")
            out_paths.append(str(p))
        return out_paths

    def _mock_compile_vod_montage(segment_paths, *, output_path, **_kwargs):
        if not segment_paths:
            raise ValueError("segment_paths must not be empty")
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"fake-montage")
        return str(out)

    monkeypatch.setattr("backend.vod_cut.cut_segments", _mock_cut_segments)
    monkeypatch.setattr("backend.vod_montage.compile_vod_montage", _mock_compile_vod_montage)

    app = create_app()
    app.dependency_overrides[get_now] = _fixed_now
    client = TestClient(app)

    output_dir = tmp_path / "vod_job_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    local_vod = tmp_path / "test_vod.mp4"
    chat_path = tmp_path / "fake_chat.jsonl"
    _write_fake_vod(local_vod)
    _write_fake_chat_jsonl(chat_path)

    submit_payload = {
        "type": "vod_highlights",
        "params": {
            "vod_url": str(local_vod),
            "output_dir": str(output_dir),
            "chat_path": str(chat_path),
            "keywords": ["wow", "insane"],
        },
    }

    submit_resp = client.post("/jobs", json=submit_payload)
    assert submit_resp.status_code == 200
    job_id = submit_resp.json()["job_id"]

    queued_resp = client.get(f"/jobs/{job_id}")
    assert queued_resp.status_code == 200
    queued_job = queued_resp.json()
    assert queued_job["status"] == "queued"
    assert queued_job["started_at"] is None
    assert queued_job["finished_at"] is None

    run_resp = client.post("/jobs/run-next")
    assert run_resp.status_code == 200
    assert run_resp.json()["processed"] == 1
    assert run_resp.json()["job_id"] == job_id

    done_job = None
    for _ in range(3):
        poll_resp = client.get(f"/jobs/{job_id}")
        assert poll_resp.status_code == 200
        job_data = poll_resp.json()
        if job_data["status"] == "done":
            done_job = job_data
            break
    assert done_job is not None
    assert done_job["status"] == "done"
    assert done_job["started_at"] is not None
    assert done_job["finished_at"] is not None

    result = done_job["result"]
    assert isinstance(result, dict)
    for key in (
        "vod_path",
        "chat_path",
        "segments_count",
        "clips_count",
        "montage_path",
        "clips_dir",
    ):
        assert key in result

    assert Path(result["vod_path"]).exists()
    assert Path(result["chat_path"]).exists()
    assert Path(result["montage_path"]).exists()
    assert Path(result["clips_dir"]).exists()

    assert result["segments_count"] > 0
    assert result["clips_count"] > 0
    assert len(list(Path(result["clips_dir"]).glob("*.mp4"))) >= 1
