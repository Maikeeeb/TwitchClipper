"""
Test Plan
- Partitions: package-level and module-level model imports
- Boundaries: ensure re-export symbols are importable without runtime setup
- Failure modes: circular import regressions in backend.models surface
"""


def test_models_package_re_exports_core_types() -> None:
    """Importing core symbols from backend.models should succeed."""
    from backend.models import ClipRef, Job, Segment

    assert ClipRef is not None
    assert Job is not None
    assert Segment is not None


def test_models_submodule_exports_jobstatus() -> None:
    """Importing JobStatus from backend.models.jobs should succeed."""
    from backend.models.jobs import JobStatus

    assert JobStatus is not None
