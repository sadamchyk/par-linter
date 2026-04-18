from __future__ import annotations

import re

from ..config import Config, parse_duration
from ..models import AlertRule, Finding, Severity
from .base import AlertCheck

_ABSENT_RE = re.compile(r"\babsent\s*\(")
_RATE_WINDOW_RE = re.compile(r"\b(?:rate|irate)\s*\([^[]+\[([^\]]+)\]\s*\)")
_ABSENT_CALL_RE = re.compile(r"\babsent\s*\(([^)]+)\)")


def _uses_absent(expr: str) -> bool:
    return bool(_ABSENT_RE.search(expr))


class MissingForCheck(AlertCheck):
    """Alert fires on first evaluation because no 'for' clause is set."""

    rule_id = "for-duration"

    def check(self, alert: AlertRule, config: Config) -> list:
        if not config.for_policy.required:
            return []
        # absent() alerts intentionally have no for – detecting a missing metric
        # should page immediately, not after a delay.
        if _uses_absent(alert.expr):
            return []

        if alert.for_duration is None:
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    alert_name=alert.name,
                    group_name=alert.group_name,
                    file_path=alert.file_path,
                    line=alert.line,
                    message="Alert has no 'for' duration and will fire on the first evaluation cycle.",
                    suggestion="Add 'for: 5m' or longer to filter transient conditions.",
                )
            ]

        duration_s = parse_duration(alert.for_duration)
        min_s = config.for_policy.min_seconds
        if duration_s < min_s:
            min_str = f"{min_s // 60}m" if min_s % 60 == 0 else f"{min_s}s"
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    alert_name=alert.name,
                    group_name=alert.group_name,
                    file_path=alert.file_path,
                    line=alert.line,
                    message=(
                        f"'for' duration '{alert.for_duration}' is shorter than "
                        f"the minimum ({min_str}). Transient conditions may trigger pages."
                    ),
                    suggestion=f"Increase 'for' to at least {min_str}.",
                )
            ]

        return []


class AbsentWithoutSelectorCheck(AlertCheck):
    """absent() with no label selectors fires whenever the metric is absent
    from ANY target, including unrelated clusters or environments."""

    rule_id = "absent-selector"

    def check(self, alert: AlertRule, config: Config) -> list:
        findings = []
        for m in _ABSENT_CALL_RE.finditer(alert.expr):
            inner = m.group(1).strip()
            if "{" not in inner:
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=Severity.WARNING,
                        alert_name=alert.name,
                        group_name=alert.group_name,
                        file_path=alert.file_path,
                        line=alert.line,
                        message=(
                            f"absent({inner}) has no label selectors. "
                            "In a multi-cluster setup this fires whenever the metric is "
                            "absent from any single target."
                        ),
                        suggestion=(
                            f"Scope the check: absent({inner}"
                            '{job="...", namespace="..."})'
                        ),
                    )
                )
        return findings


class SuspiciousRateWindowCheck(AlertCheck):
    """rate()/irate() window shorter than 2 minutes produces a noisy signal
    because it spans too few scrape samples."""

    rule_id = "rate-window"
    MIN_WINDOW_SECONDS = 120

    def check(self, alert: AlertRule, config: Config) -> list:
        findings = []
        for m in _RATE_WINDOW_RE.finditer(alert.expr):
            window = m.group(1)
            seconds = parse_duration(window)
            if 0 < seconds < self.MIN_WINDOW_SECONDS:
                n_samples = max(1, seconds // 15)
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=Severity.WARNING,
                        alert_name=alert.name,
                        group_name=alert.group_name,
                        file_path=alert.file_path,
                        line=alert.line,
                        message=(
                            f"rate()/irate() window '[{window}]' is shorter than 2m. "
                            f"With a 15s scrape interval this covers only ~{n_samples} "
                            "samples, making the signal noisy."
                        ),
                        suggestion="Use a window of at least 5m for stable rate calculations.",
                    )
                )
        return findings
