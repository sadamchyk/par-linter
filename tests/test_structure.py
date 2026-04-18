import pytest
from par.checks.structure import (
    BrokenDependencyCheck,
    CounterAsThresholdCheck,
    DuplicateRuleCheck,
    NoComparisonCheck,
)
from par.config import Config
from par.models import RecordingRule, Severity
from .conftest import make_alert


class TestNoComparison:
    def test_bare_metric_flagged(self):
        check = NoComparisonCheck()
        alert = make_alert(expr="process_open_fds{job='api'}")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert findings[0].rule_id == "no-comparison"

    def test_comparison_passes(self):
        check = NoComparisonCheck()
        alert = make_alert(expr='up{job="api"} == 0')
        assert check.check(alert, Config()) == []

    def test_absent_exempt(self):
        check = NoComparisonCheck()
        alert = make_alert(expr='absent(up{job="api"})')
        assert check.check(alert, Config()) == []

    def test_bool_modifier_exempt(self):
        check = NoComparisonCheck()
        alert = make_alert(expr='up{job="api"} == bool 0')
        assert check.check(alert, Config()) == []


class TestCounterAsThreshold:
    def test_counter_absolute_threshold_flagged(self):
        check = CounterAsThresholdCheck()
        alert = make_alert(expr="http_errors_total{job='api'} > 100")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert findings[0].rule_id == "counter-threshold"

    def test_counter_with_rate_passes(self):
        check = CounterAsThresholdCheck()
        alert = make_alert(expr="rate(http_errors_total{job='api'}[5m]) > 0.1")
        assert check.check(alert, Config()) == []

    def test_counter_with_increase_passes(self):
        check = CounterAsThresholdCheck()
        alert = make_alert(expr="increase(http_errors_total[1h]) > 100")
        assert check.check(alert, Config()) == []

    def test_gauge_metric_not_flagged(self):
        check = CounterAsThresholdCheck()
        alert = make_alert(expr="process_open_fds{job='api'} > 1000")
        assert check.check(alert, Config()) == []


class TestDuplicateRule:
    def test_duplicate_in_same_group_flagged(self):
        check = DuplicateRuleCheck()
        a1 = make_alert(name="DiskFull", line=10)
        a2 = make_alert(name="DiskFull", line=20)
        findings = check.check([a1, a2], [], Config())
        assert len(findings) == 1
        assert findings[0].rule_id == "duplicate-alert"
        assert findings[0].severity == Severity.ERROR

    def test_unique_names_pass(self):
        check = DuplicateRuleCheck()
        a1 = make_alert(name="AlertA", line=10)
        a2 = make_alert(name="AlertB", line=20)
        assert check.check([a1, a2], [], Config()) == []

    def test_same_name_different_groups_not_flagged(self):
        check = DuplicateRuleCheck()
        a1 = make_alert(name="DiskFull", group_name="group_a", line=10)
        a2 = make_alert(name="DiskFull", group_name="group_b", line=20)
        assert check.check([a1, a2], [], Config()) == []


class TestBrokenDependency:
    def test_missing_recording_rule_flagged(self):
        check = BrokenDependencyCheck()
        alert = make_alert(expr="job:http_error_rate:rate5m{job='api'} > 0.01")
        findings = check.check([alert], [], Config())
        assert len(findings) == 1
        assert findings[0].rule_id == "recording-ref"

    def test_present_recording_rule_passes(self):
        check = BrokenDependencyCheck()
        alert = make_alert(expr="job:http_error_rate:rate5m{job='api'} > 0.01")
        recording = RecordingRule(
            name="job:http_error_rate:rate5m",
            expr="...",
            labels={},
            group_name="recordings",
            file_path="recordings.yaml",
            line=5,
        )
        assert check.check([alert], [recording], Config()) == []

    def test_regular_metric_not_flagged(self):
        check = BrokenDependencyCheck()
        alert = make_alert(expr='up{job="api"} == 0')
        assert check.check([alert], [], Config()) == []
