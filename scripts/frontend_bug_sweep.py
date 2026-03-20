"""
Preflight + strict oracle runner for the desktop bug sweep.

This script focuses on deterministic API/runtime checks that support unattended
desktop testing workflows.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


API_BASE_URL = os.getenv("TC_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
HAPPY_VOD_URL = "https://www.twitch.tv/videos/2713566602"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    url = f"{API_BASE_URL}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else None
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed = json.loads(body) if body else None
        return exc.code, parsed


def _check_health() -> CheckResult:
    status, body = _request("GET", "/health")
    if status != 200:
        return CheckResult("health", False, f"expected 200, got {status}")
    if not isinstance(body, dict) or body.get("ok") is not True:
        return CheckResult("health", False, f"unexpected payload: {body}")
    return CheckResult("health", True, "ok")


def _check_jobs_list() -> CheckResult:
    status, body = _request("GET", "/jobs?limit=1")
    if status != 200:
        return CheckResult("jobs_list", False, f"expected 200, got {status}")
    if not isinstance(body, list):
        return CheckResult("jobs_list", False, f"expected list payload, got: {body}")
    return CheckResult("jobs_list", True, "ok")


def _queued_or_running_jobs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    status_q, queued = _request("GET", "/jobs?status=queued&limit=500")
    status_r, running = _request("GET", "/jobs?status=running&limit=500")
    if status_q != 200 or not isinstance(queued, list):
        raise RuntimeError(f"failed to read queued jobs (status={status_q})")
    if status_r != 200 or not isinstance(running, list):
        raise RuntimeError(f"failed to read running jobs (status={status_r})")
    return queued, running


def _submit_vod(vod_url: str, output_dir: str = "vod_output") -> tuple[int, Any]:
    payload = {
        "vod_url": vod_url,
        "output_dir": output_dir,
    }
    return _request("POST", "/jobs/vod-highlights", payload)


def _submit_clip() -> tuple[int, Any]:
    payload = {"streamer_names": ["zubatlel"]}
    return _request("POST", "/jobs/clip-montage", payload)


def _run_next() -> tuple[int, Any]:
    return _request("POST", "/jobs/run-next", {})


def _get_job(job_id: str) -> tuple[int, Any]:
    return _request("GET", f"/jobs/{job_id}")


def _strict_invalid_url_case(case_name: str, vod_url: str, expected_error: str) -> CheckResult:
    submit_status, submit_body = _submit_vod(vod_url)
    if submit_status != 200 or not isinstance(submit_body, dict) or "job_id" not in submit_body:
        return CheckResult(
            case_name,
            False,
            f"submit failed: status={submit_status}, body={submit_body}",
        )
    job_id = str(submit_body["job_id"])

    run_status, run_body = _run_next()
    if run_status != 200:
        return CheckResult(case_name, False, f"run-next failed: status={run_status}, body={run_body}")

    job_status, job_body = _get_job(job_id)
    if job_status != 200 or not isinstance(job_body, dict):
        return CheckResult(
            case_name,
            False,
            f"get-job failed: status={job_status}, body={job_body}",
        )

    actual_status = job_body.get("status")
    actual_error = job_body.get("error")
    if actual_status != "failed":
        return CheckResult(case_name, False, f"expected failed status, got: {actual_status}")
    if actual_error != expected_error:
        return CheckResult(
            case_name,
            False,
            f"expected error '{expected_error}', got '{actual_error}'",
        )
    return CheckResult(case_name, True, "strict oracle matched")


def main() -> int:
    results: list[CheckResult] = []

    try:
        results.append(_check_health())
        results.append(_check_jobs_list())

        queued, running = _queued_or_running_jobs()
        if queued or running:
            pending_count = len(queued) + len(running)
            results.append(
                CheckResult(
                    "queue_cleanliness",
                    False,
                    f"expected no queued/running jobs before strict oracle; found {pending_count}",
                )
            )
        else:
            results.append(CheckResult("queue_cleanliness", True, "ok"))

            results.append(
                _strict_invalid_url_case(
                    "malformed-url",
                    "not-a-url",
                    "Invalid input string: not-a-url",
                )
            )
            results.append(
                _strict_invalid_url_case(
                    "non-video-twitch-url",
                    "https://www.twitch.tv/somechannel",
                    "Invalid input string: https://www.twitch.tv/somechannel",
                )
            )
            results.append(
                _strict_invalid_url_case(
                    "unreachable-host-guarded",
                    "https://invalid.invalid/videos/2713566602",
                    "Invalid input string: https://invalid.invalid/videos/2713566602",
                )
            )

        happy_status, happy_body = _submit_vod(HAPPY_VOD_URL)
        happy_ok = happy_status == 200 and isinstance(happy_body, dict) and "job_id" in happy_body
        results.append(
            CheckResult(
                "submit-happy-vod",
                happy_ok,
                "ok" if happy_ok else f"submit failed: status={happy_status}, body={happy_body}",
            )
        )

        clip_status, clip_body = _submit_clip()
        clip_ok = clip_status == 200 and isinstance(clip_body, dict) and "job_id" in clip_body
        results.append(
            CheckResult(
                "submit-clip-montage",
                clip_ok,
                "ok" if clip_ok else f"submit failed: status={clip_status}, body={clip_body}",
            )
        )
    except Exception as exc:  # pragma: no cover - defensive fallback for operator visibility
        results.append(CheckResult("runner", False, f"unexpected exception: {exc}"))

    print(f"API base URL: {API_BASE_URL}")
    print("----")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")

    failed = [result for result in results if not result.passed]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
