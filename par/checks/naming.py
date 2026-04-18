from __future__ import annotations

import re

from ..config import Config
from ..models import AlertRule, Finding, Severity
from .base import AlertCheck

# Maps non-base suffix → recommended base unit (Prometheus naming best practices)
_NON_BASE_UNITS: dict = {
    "_milliseconds": "seconds",
    "_microseconds": "seconds",
    "_nanoseconds": "seconds",
    "_minutes": "seconds",
    "_hours": "seconds",
    "_days": "seconds",
    "_weeks": "seconds",
    "_kilobytes": "bytes",
    "_megabytes": "bytes",
    "_gigabytes": "bytes",
    "_terabytes": "bytes",
    "_kbytes": "bytes",
    "_mbytes": "bytes",
    "_kilobits": "bytes",
    "_megabits": "bytes",
    "_gigabits": "bytes",
    "_percent": "ratio (0–1)",
    "_percentage": "ratio (0–1)",
    "_millivolts": "volts",
    "_milliamperes": "amperes",
    "_milligrams": "grams",
    "_kilometers": "meters",
    "_centimeters": "meters",
    "_millimeters": "meters",
}

# Longest suffixes first so _milliseconds matches before _seconds
_SORTED_SUFFIXES = sorted(_NON_BASE_UNITS, key=len, reverse=True)

_NON_BASE_RE = re.compile(
    r"\b(\w+(" + "|".join(re.escape(s) for s in _SORTED_SUFFIXES) + r"))\b"
)


class NonBaseUnitCheck(AlertCheck):
    """non-base-unit – A metric in the alert expression uses a non-base unit suffix.

    Prometheus naming best practices require base units (seconds, bytes, meters…)
    so that metrics from different sources stay interoperable and PromQL expressions
    remain unambiguous about what they are measuring.
    """

    rule_id = "non-base-unit"

    def check(self, alert: AlertRule, config: Config) -> list:
        findings = []
        seen: set = set()

        for m in _NON_BASE_RE.finditer(alert.expr):
            metric, suffix = m.group(1), m.group(2)
            if metric in seen:
                continue
            seen.add(metric)

            base = _NON_BASE_UNITS[suffix]
            bad_unit = suffix.lstrip("_")
            base_unit = base.split()[0]  # first word, e.g. "seconds" from "seconds"
            renamed = metric[: -len(suffix)] + f"_{base_unit}"

            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.INFO,
                    alert_name=alert.name,
                    group_name=alert.group_name,
                    file_path=alert.file_path,
                    line=alert.line,
                    message=(
                        f"Metric '{metric}' uses non-base unit '{bad_unit}'. "
                        f"Prometheus recommends '{base}' for interoperability."
                    ),
                    suggestion=f"Rename to '{renamed}' and update the exporter.",
                )
            )

        return findings
