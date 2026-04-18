from __future__ import annotations

from ..config import Config
from ..models import AlertRule, Finding, Severity
from .base import AlertCheck

_ANNOTATION_SEVERITY = {
    "summary": Severity.ERROR,
    "description": Severity.WARNING,
    "runbook_url": Severity.ERROR,
    "dashboard_url": Severity.WARNING,
}


class MissingLabelsCheck(AlertCheck):
    rule_id = "required-labels"

    def check(self, alert: AlertRule, config: Config) -> list:
        missing = [l for l in config.required_labels if l not in alert.labels]
        if not missing:
            return []
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.ERROR,
                alert_name=alert.name,
                group_name=alert.group_name,
                file_path=alert.file_path,
                line=alert.line,
                message=f"Missing required label(s): {', '.join(missing)}",
                suggestion=f"Add labels: {', '.join(f'{l}: <value>' for l in missing)}",
            )
        ]


class MissingAnnotationsCheck(AlertCheck):
    rule_id = "required-annotations"

    def check(self, alert: AlertRule, config: Config) -> list:
        findings = []
        for annotation in config.required_annotations:
            if annotation not in alert.annotations:
                severity = _ANNOTATION_SEVERITY.get(annotation, Severity.WARNING)
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=severity,
                        alert_name=alert.name,
                        group_name=alert.group_name,
                        file_path=alert.file_path,
                        line=alert.line,
                        message=f"Missing annotation '{annotation}'",
                        suggestion=_annotation_hint(annotation),
                    )
                )
        return findings


class InvalidOwnerCheck(AlertCheck):
    """invalid-owner – The owner annotation is present but its value is not in the
    configured list of valid team names."""

    rule_id = "invalid-owner"

    def check(self, alert: AlertRule, config: Config) -> list:
        if not config.valid_owners:
            return []
        owner = alert.labels.get("owner", "").strip()
        if not owner or owner in config.valid_owners:
            return []
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.ERROR,
                alert_name=alert.name,
                group_name=alert.group_name,
                file_path=alert.file_path,
                line=alert.line,
                message=f"Unknown owner '{owner}'. Must be one of: {', '.join(sorted(config.valid_owners))}",
                suggestion=f"Set owner to a known team: {', '.join(sorted(config.valid_owners))}",
            )
        ]


def _annotation_hint(name: str) -> str:
    hints = {
        "summary": "Add a one-sentence human-readable summary: what is broken right now?",
        "description": "Add a description with {{ $value }} and context for the on-call engineer.",
        "runbook_url": "Add a runbook_url linking to remediation steps.",
        "dashboard_url": "Add a dashboard_url linking to the relevant observability dashboard.",
    }
    return hints.get(name, f"Add annotation '{name}'.")
