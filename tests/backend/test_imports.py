"""
Test Plan
- Partitions: module import and callable exposure
- Boundaries: none
- Failure modes: missing attributes break import validation
"""

from backend import clips
from backend import oneVideo


def test_backend_modules_importable() -> None:
    # Covers: TODO-TEST-IMPORTS
    assert callable(clips.getclips)
    assert callable(oneVideo.compile)
