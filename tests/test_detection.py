from datetime import UTC, datetime

from app.detection.engine import DetectionEngine, baseline_elevated, severity_from_signals
from app.models.schemas import LogEntry, Severity


def test_no_hit_below_threshold():
    engine = DetectionEngine(repeat_threshold=3)
    entry = LogEntry(level="ERROR", service="api", message="boom")
    hit = engine.evaluate(
        entry,
        "fp",
        window_count=2,
        baseline_avg=0.0,
        baseline_samples=0,
        first_seen=datetime.now(UTC),
        last_seen=datetime.now(UTC),
    )
    assert hit is None


def test_repeated_errors_create_hit():
    engine = DetectionEngine(repeat_threshold=3)
    entry = LogEntry(level="ERROR", service="api", message="boom")
    hit = engine.evaluate(
        entry,
        "fp",
        window_count=3,
        baseline_avg=0.0,
        baseline_samples=0,
        first_seen=datetime.now(UTC),
        last_seen=datetime.now(UTC),
    )
    assert hit is not None
    assert hit.severity == Severity.MEDIUM
    assert "repeated_errors" in hit.reason


def test_critical_level_maps_to_critical_severity():
    sev = severity_from_signals(
        level="CRITICAL",
        window_count=3,
        repeat_threshold=3,
        rate_elevated=False,
    )
    assert sev == Severity.CRITICAL


def test_baseline_requires_min_samples():
    assert baseline_elevated(10, 1.0, multiplier=3.0, min_samples=20, baseline_samples=5) is False
    assert baseline_elevated(10, 1.0, multiplier=3.0, min_samples=20, baseline_samples=25) is True
