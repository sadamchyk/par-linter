from __future__ import annotations

import re

from ..config import Config
from ..models import AlertRule, Finding, Severity
from .base import AlertCheck


def _has_any_selector(expr: str) -> bool:
    """True if the expression contains at least one {label=...} block."""
    return bool(re.search(r"\{[^}]*\S[^}]*\}", expr))


def _has_scoping_selector(expr: str, labels: list) -> bool:
    """True if at least one of the required scoping labels appears in a selector."""
    for label in labels:
        if re.search(rf'\b{re.escape(label)}\s*[=!~]', expr):
            return True
    return False


class BroadSelectorCheck(AlertCheck):
    """Expression has no label selectors (fires across all environments)
    or lacks any of the recommended scoping labels."""

    rule_id = "broad-selector"

    def check(self, alert: AlertRule, config: Config) -> list:
        required = config.selector_policy.require_one_of

        if not _has_any_selector(alert.expr):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    alert_name=alert.name,
                    group_name=alert.group_name,
                    file_path=alert.file_path,
                    line=alert.line,
                    message=(
                        "Expression has no label selectors. "
                        "This alert will fire for every matching time series across all "
                        "environments, jobs, and clusters."
                    ),
                    suggestion=f"Add at least one selector: {', '.join(required)}",
                )
            ]

        if not _has_scoping_selector(alert.expr, required):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.INFO,
                    alert_name=alert.name,
                    group_name=alert.group_name,
                    file_path=alert.file_path,
                    line=alert.line,
                    message=(
                        f"Expression has selectors but none of the recommended scoping "
                        f"labels ({', '.join(required)}). "
                        "The alert may fire in unintended environments."
                    ),
                    suggestion=f"Add one of: {', '.join(required)}",
                )
            ]

        return []
