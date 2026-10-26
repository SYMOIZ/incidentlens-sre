"""Pure detection logic — no I/O. Callers supply counts / baselines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.schemas import LogEntry, Severity

ERROR_LEVELS = frozenset({"ERROR", "CRITICAL", "FATAL"})


@dataclass(frozen=True, slots=True)
class DetectionHit:
    fingerprint: str
    title: str
    severity: Severity
    service: str
    sample_message: str
    count: int
    reason: str
    first_seen: datetime
    last_seen: datetime


def is_error_level(level: str) -> bool:
    return level.upper() in ERROR_LEVELS


def severity_from_signals(
    *,
    level: str,
    window_count: int,
    repeat_threshold: int,
    rate_elevated: bool,
) -> Severity:
    """Map level + volume + rate signals to a severity bucket."""
    upper = level.upper()
    if upper == "CRITICAL" or upper == "FATAL":
        return Severity.CRITICAL
    if rate_elevated and window_count >= repeat_threshold:
        return Severity.HIGH
    if window_count >= repeat_threshold * 2:
        return Severity.HIGH
    if window_count >= repeat_threshold or upper == "ERROR":
        return Severity.MEDIUM
    return Severity.LOW


def baseline_elevated(
    recent_count: int,
    baseline_avg: float,
    *,
    multiplier: float,
    min_samples: int,
    baseline_samples: int,
) -> bool:
    """True when recent error volume exceeds baseline * multiplier (cold-start safe)."""
    if baseline_samples < min_samples:
        return False
    if baseline_avg <= 0:
        return recent_count >= min_samples
    return recent_count >= baseline_avg * multiplier


class DetectionEngine:
    """Evaluates whether a fingerprint should open/update an incident."""

    def __init__(
        self,
        *,
        repeat_threshold: int = 3,
        baseline_multiplier: float = 3.0,
        baseline_min_samples: int = 20,
    ) -> None:
        self.repeat_threshold = repeat_threshold
        self.baseline_multiplier = baseline_multiplier
        self.baseline_min_samples = baseline_min_samples

    def evaluate(
        self,
        entry: LogEntry,
        fingerprint: str,
        *,
        window_count: int,
        baseline_avg: float,
        baseline_samples: int,
        first_seen: datetime | None = None,
        last_seen: datetime | None = None,
    ) -> DetectionHit | None:
        if not is_error_level(entry.level):
            return None

        rate_elevated = baseline_elevated(
            window_count,
            baseline_avg,
            multiplier=self.baseline_multiplier,
            min_samples=self.baseline_min_samples,
            baseline_samples=baseline_samples,
        )
        repeated = window_count >= self.repeat_threshold

        if not repeated and not rate_elevated:
            return None

        reasons: list[str] = []
        if repeated:
            reasons.append(f"repeated_errors:{window_count}>={self.repeat_threshold}")
        if rate_elevated:
            reasons.append(
                f"baseline_rate:{window_count:.0f}>={baseline_avg * self.baseline_multiplier:.1f}"
            )

        now = entry.timestamp or datetime.now(UTC)
        severity = severity_from_signals(
            level=entry.level,
            window_count=window_count,
            repeat_threshold=self.repeat_threshold,
            rate_elevated=rate_elevated,
        )
        title = f"{entry.service}: {entry.message[:80]}"
        return DetectionHit(
            fingerprint=fingerprint,
            title=title,
            severity=severity,
            service=entry.service,
            sample_message=entry.message,
            count=window_count,
            reason=";".join(reasons),
            first_seen=first_seen or now,
            last_seen=last_seen or now,
        )
