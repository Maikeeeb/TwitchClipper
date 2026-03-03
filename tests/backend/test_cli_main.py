"""
Test Plan
- Partitions: clip-montage parser args, successful job completion, failed job completion
- Boundaries: optional max-clips omitted vs provided
- Failure modes: failed job returns non-zero exit code
"""

from __future__ import annotations

from argparse import Namespace

from cli import main as cli_main


def test_parser_accepts_clip_montage_options() -> None:
    # Covers: TODO-TEST-IMPORTS
    parser = cli_main._build_parser()
    args = parser.parse_args(
        [
            "clip-montage",
            "--streamer",
            "alpha",
            "--streamer",
            "beta",
            "--max-clips",
            "5",
            "--output-dir",
            "out",
        ]
    )
    assert args.command == "clip-montage"
    assert args.streamer_names == ["alpha", "beta"]
    assert args.max_clips == 5
    assert args.current_videos_dir == "out"


def test_handle_clip_montage_returns_zero_on_done(monkeypatch) -> None:
    # Covers: TODO-TEST-IMPORTS
    monkeypatch.setattr(cli_main, "_submit_clip_montage", lambda *_args, **_kwargs: "job-1")
    monkeypatch.setattr(cli_main, "_run_next", lambda *_args, **_kwargs: {"processed": 1})
    monkeypatch.setattr(
        cli_main,
        "_get_job",
        lambda *_args, **_kwargs: {"status": "done", "result": {"count": 2}},
    )
    monkeypatch.setattr(cli_main.time, "sleep", lambda *_args, **_kwargs: None)

    args = Namespace(
        streamer_names=["alpha"],
        current_videos_dir="out",
        max_clips=None,
        api_base_url="http://127.0.0.1:8000",
        poll_interval_seconds=0.0,
        run_next_interval_seconds=0.0,
        timeout_seconds=30,
    )
    assert cli_main._handle_clip_montage(args) == 0


def test_handle_clip_montage_returns_one_on_failed(monkeypatch) -> None:
    # Covers: TODO-TEST-IMPORTS
    monkeypatch.setattr(cli_main, "_submit_clip_montage", lambda *_args, **_kwargs: "job-2")
    monkeypatch.setattr(cli_main, "_run_next", lambda *_args, **_kwargs: {"processed": 1})
    monkeypatch.setattr(
        cli_main,
        "_get_job",
        lambda *_args, **_kwargs: {"status": "failed", "error": "boom"},
    )
    monkeypatch.setattr(cli_main.time, "sleep", lambda *_args, **_kwargs: None)

    args = Namespace(
        streamer_names=["alpha"],
        current_videos_dir="out",
        max_clips=3,
        api_base_url="http://127.0.0.1:8000",
        poll_interval_seconds=0.0,
        run_next_interval_seconds=0.0,
        timeout_seconds=30,
    )
    assert cli_main._handle_clip_montage(args) == 1
