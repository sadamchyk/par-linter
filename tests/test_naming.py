from par.checks.naming import NonBaseUnitCheck
from par.config import Config
from par.models import Severity
from .conftest import make_alert


class TestNonBaseUnit:
    def test_milliseconds_flagged(self):
        check = NonBaseUnitCheck()
        alert = make_alert(expr="http_request_duration_milliseconds{job='api'} > 500")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert findings[0].rule_id == "non-base-unit"
        assert findings[0].severity == Severity.INFO
        assert "milliseconds" in findings[0].message
        assert "seconds" in findings[0].message

    def test_seconds_passes(self):
        check = NonBaseUnitCheck()
        alert = make_alert(expr="http_request_duration_seconds{job='api'} > 0.5")
        assert check.check(alert, Config()) == []

    def test_megabytes_flagged(self):
        check = NonBaseUnitCheck()
        alert = make_alert(expr="node_memory_usage_megabytes{job='node'} > 1024")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert "megabytes" in findings[0].message
        assert "bytes" in findings[0].message

    def test_bytes_passes(self):
        check = NonBaseUnitCheck()
        alert = make_alert(expr="node_memory_usage_bytes{job='node'} > 1073741824")
        assert check.check(alert, Config()) == []

    def test_percent_flagged(self):
        check = NonBaseUnitCheck()
        alert = make_alert(expr="disk_usage_percent{job='node'} > 90")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert "percent" in findings[0].message
        assert "ratio" in findings[0].message

    def test_milliseconds_not_confused_with_seconds(self):
        # _milliseconds suffix should not accidentally match _seconds
        check = NonBaseUnitCheck()
        alert = make_alert(expr="latency_milliseconds > 100")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert "latency_seconds" in findings[0].suggestion

    def test_each_metric_reported_once(self):
        # Same metric appearing twice in an expression should produce one finding
        check = NonBaseUnitCheck()
        alert = make_alert(
            expr="rate(http_request_duration_milliseconds[5m]) / http_request_duration_milliseconds > 1"
        )
        findings = check.check(alert, Config())
        assert len(findings) == 1

    def test_no_non_base_unit_passes(self):
        check = NonBaseUnitCheck()
        alert = make_alert(expr='up{job="api"} == 0')
        assert check.check(alert, Config()) == []
