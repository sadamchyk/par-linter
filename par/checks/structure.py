from __future__ import annotations

import re
from collections import defaultdict

from ..config import Config
from ..models import AlertRule, Finding, Severity
from .base import AlertCheck, CorpusCheck

_COMPARISON_RE = re.compile(r"(?:==|!=|>=|<=|>(?!=)|<(?!=))")
_BOOLEAN_FUNC_RE = re.compile(r"\b(absent|bool)\b")
_RATE_WRAPPER_RE = re.compile(r"\b(?:rate|increase|irate|delta)\s*\(")
_COUNTER_METRIC_RE = re.compile(r"\b(\w+(?:_total|_count))\b")
_RECORDING_RULE_REF_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*(?::[a-zA-Z0-9_]+){1,})\b")


class NoComparisonCheck(AlertCheck):
    """Alert expression has no comparison operator. Because any non-zero,
    non-NaN value is truthy in Prometheus, this alert fires for every instance
    that reports the metric."""

    rule_id = "no-comparison"

    def check(self, alert: AlertRule, config: Config) -> list:
        expr = alert.expr
        # absent() returns {0,1}; bool modifier returns {0,1} – both meaningful without comparison
        if _BOOLEAN_FUNC_RE.search(expr):
            return []
        if _COMPARISON_RE.search(expr):
            return []
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.WARNING,
                alert_name=alert.name,
                group_name=alert.group_name,
                file_path=alert.file_path,
                line=alert.line,
                message=(
                    "Alert expression has no comparison operator. "
                    "It will fire for every non-zero, non-NaN time series value."
                ),
                suggestion="Add a threshold: expr > <value>",
            )
        ]


class CounterAsThresholdCheck(AlertCheck):
    """A counter metric (name ending in _total or _count) is compared
    against an absolute threshold. Raw counter values grow monotonically with
    process lifetime and are meaningless as fixed thresholds."""

    rule_id = "counter-threshold"

    def check(self, alert: AlertRule, config: Config) -> list:
        expr = alert.expr
        if not _COMPARISON_RE.search(expr):
            return []
        # rate/increase/irate/delta wrappers make the counter meaningful
        if _RATE_WRAPPER_RE.search(expr):
            return []
        matches = _COUNTER_METRIC_RE.findall(expr)
        if not matches:
            return []
        metric = matches[0]
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.WARNING,
                alert_name=alert.name,
                group_name=alert.group_name,
                file_path=alert.file_path,
                line=alert.line,
                message=(
                    f"Counter metric '{metric}' is compared against an absolute threshold. "
                    "Counter values grow monotonically and depend on process uptime."
                ),
                suggestion=f"Use rate({metric}[5m]) > <threshold> to measure the rate of increase.",
            )
        ]


class DuplicateRuleCheck(CorpusCheck):
    """Two rules share the same alert name in the same group. Prometheus
    silently uses the last definition, so the first alert is never evaluated."""

    rule_id = "duplicate-alert"

    def check(self, alerts: list, recordings: list, config: Config) -> list:
        findings = []
        by_group: dict = defaultdict(list)
        for alert in alerts:
            by_group[(alert.file_path, alert.group_name, alert.name)].append(alert)

        for (file_path, group_name, name), rules in by_group.items():
            if len(rules) > 1:
                # Report on every occurrence after the first
                for rule in rules[1:]:
                    findings.append(
                        Finding(
                            rule_id=self.rule_id,
                            severity=Severity.ERROR,
                            alert_name=name,
                            group_name=group_name,
                            file_path=file_path,
                            line=rule.line,
                            message=(
                                f"Duplicate alert name '{name}' in group '{group_name}'. "
                                "The later definition silently overrides the earlier one."
                            ),
                            suggestion="Rename or remove the duplicate.",
                        )
                    )

        return findings


class BrokenDependencyCheck(CorpusCheck):
    """An alert expression references a recording rule (colon-notation name)
    that is not defined in any of the loaded files."""

    rule_id = "recording-ref"

    def check(self, alerts: list, recordings: list, config: Config) -> list:
        recording_names = {r.name for r in recordings}
        findings = []

        for alert in alerts:
            for ref in _RECORDING_RULE_REF_RE.findall(alert.expr):
                if ref not in recording_names:
                    findings.append(
                        Finding(
                            rule_id=self.rule_id,
                            severity=Severity.ERROR,
                            alert_name=alert.name,
                            group_name=alert.group_name,
                            file_path=alert.file_path,
                            line=alert.line,
                            message=(
                                f"Recording rule '{ref}' is referenced in the expression "
                                "but not defined in any loaded file."
                            ),
                            suggestion=(
                                "Define the recording rule or pass the file that contains "
                                "it to par."
                            ),
                        )
                    )

        return findings
