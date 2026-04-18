from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Config
from ..models import AlertRule


class AlertCheck(ABC):
    """Runs independently on each alert rule."""

    rule_id: str

    @abstractmethod
    def check(self, alert: AlertRule, config: Config) -> list:
        ...


class CorpusCheck(ABC):
    """Runs once with full context of all loaded rules."""

    rule_id: str

    @abstractmethod
    def check(self, alerts: list, recordings: list, config: Config) -> list:
        ...
