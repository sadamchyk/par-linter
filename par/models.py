from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"error": 2, "warning": 1, "info": 0}[self.value]

    def __ge__(self, other: Severity) -> bool:  # type: ignore[override]
        return self.rank >= other.rank

    def __gt__(self, other: Severity) -> bool:  # type: ignore[override]
        return self.rank > other.rank

    def __le__(self, other: Severity) -> bool:  # type: ignore[override]
        return self.rank <= other.rank

    def __lt__(self, other: Severity) -> bool:  # type: ignore[override]
        return self.rank < other.rank


@dataclass
class AlertRule:
    name: str
    expr: str
    for_duration: Optional[str]
    labels: dict
    annotations: dict
    group_name: str
    file_path: str
    line: int
    suppressed: set = field(default_factory=set)


@dataclass
class RecordingRule:
    name: str
    expr: str
    labels: dict
    group_name: str
    file_path: str
    line: int


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    alert_name: str
    group_name: str
    file_path: str
    line: int
    message: str
    suggestion: str
    owner: str = ""
