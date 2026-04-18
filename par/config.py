from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

import yaml

from .models import Severity


def parse_duration(s: str) -> int:
    """Convert a Prometheus duration string to seconds. Returns 0 for empty/unparseable."""
    total = 0
    for match in re.finditer(r"(\d+)([smhdwy])", str(s)):
        n, unit = int(match.group(1)), match.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}
        total += n * multipliers[unit]
    return total


@dataclass
class ForPolicy:
    required: bool = True
    min_seconds: int = 120  # 2m


@dataclass
class SelectorPolicy:
    require_one_of: list = field(
        default_factory=lambda: ["job", "cluster", "namespace", "service"]
    )


@dataclass
class Config:
    severity_threshold: Severity = Severity.INFO
    required_labels: list = field(default_factory=lambda: ["severity", "owner"])
    required_annotations: list = field(
        default_factory=lambda: ["summary", "description", "runbook_url", "dashboard_url"]
    )
    valid_owners: list = field(default_factory=list)
    selector_policy: SelectorPolicy = field(default_factory=SelectorPolicy)
    for_policy: ForPolicy = field(default_factory=ForPolicy)

    @classmethod
    def load(cls, path: Optional[str] = None) -> Config:
        if path is None:
            for candidate in (".par.yaml", ".par.yml"):
                if os.path.exists(candidate):
                    path = candidate
                    break

        if path is None:
            return cls()

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = cls()

        if "severity_threshold" in data:
            config.severity_threshold = Severity(data["severity_threshold"])
        if "required_labels" in data:
            config.required_labels = data["required_labels"]
        if "valid_owners" in data:
            config.valid_owners = data["valid_owners"]
        if "required_annotations" in data:
            config.required_annotations = data["required_annotations"]
        if "selector_policy" in data:
            sp = data["selector_policy"]
            config.selector_policy = SelectorPolicy(
                require_one_of=sp.get(
                    "require_one_of", config.selector_policy.require_one_of
                )
            )
        if "for_policy" in data:
            fp = data["for_policy"]
            config.for_policy = ForPolicy(
                required=fp.get("required_for_alerts", True),
                min_seconds=parse_duration(fp.get("min", "2m")),
            )

        return config
