from par.checks.stability import (
    AbsentWithoutSelectorCheck,
    MissingForCheck,
    SuspiciousRateWindowCheck,
)
from par.config import Config
from .conftest import make_alert


class TestMissingFor:
    def test_no_for_flagged(self):
        check = MissingForCheck()
        alert = make_alert(for_duration=None)
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert findings[0].rule_id == "for-duration"

    def test_absent_expr_exempt(self):
        check = MissingForCheck()
        alert = make_alert(for_duration=None, expr='absent(up{job="api"})')
        assert check.check(alert, Config()) == []

    def test_short_for_flagged(self):
        check = MissingForCheck()
        alert = make_alert(for_duration="30s")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert "30s" in findings[0].message

    def test_adequate_for_passes(self):
        check = MissingForCheck()
        alert = make_alert(for_duration="5m")
        assert check.check(alert, Config()) == []

    def test_exactly_minimum_passes(self):
        check = MissingForCheck()
        alert = make_alert(for_duration="2m")
        assert check.check(alert, Config()) == []

    def test_disabled_policy_skips(self):
        check = MissingForCheck()
        config = Config()
        config.for_policy.required = False
        alert = make_alert(for_duration=None)
        assert check.check(alert, config) == []


class TestAbsentWithoutSelector:
    def test_absent_no_selector_flagged(self):
        check = AbsentWithoutSelectorCheck()
        alert = make_alert(expr="absent(up)")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert findings[0].rule_id == "absent-selector"

    def test_absent_with_selector_passes(self):
        check = AbsentWithoutSelectorCheck()
        alert = make_alert(expr='absent(up{job="api", namespace="prod"})')
        assert check.check(alert, Config()) == []

    def test_no_absent_passes(self):
        check = AbsentWithoutSelectorCheck()
        alert = make_alert(expr='up{job="api"} == 0')
        assert check.check(alert, Config()) == []


class TestSuspiciousRateWindow:
    def test_short_window_flagged(self):
        check = SuspiciousRateWindowCheck()
        alert = make_alert(expr="rate(http_requests_total{job='api'}[1m]) > 100")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert findings[0].rule_id == "rate-window"
        assert "1m" in findings[0].message

    def test_adequate_window_passes(self):
        check = SuspiciousRateWindowCheck()
        alert = make_alert(expr="rate(http_requests_total{job='api'}[5m]) > 100")
        assert check.check(alert, Config()) == []

    def test_irate_short_window_flagged(self):
        check = SuspiciousRateWindowCheck()
        alert = make_alert(expr="irate(http_requests_total[30s]) > 50")
        findings = check.check(alert, Config())
        assert len(findings) == 1

    def test_exact_2m_passes(self):
        check = SuspiciousRateWindowCheck()
        alert = make_alert(expr="rate(metric[2m]) > 1")
        assert check.check(alert, Config()) == []
