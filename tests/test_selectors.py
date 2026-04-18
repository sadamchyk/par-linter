from par.checks.selectors import BroadSelectorCheck
from par.config import Config
from par.models import Severity
from .conftest import make_alert


class TestBroadSelector:
    def test_no_selectors_flagged_as_warning(self):
        check = BroadSelectorCheck()
        alert = make_alert(expr="up == 0")
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert findings[0].rule_id == "broad-selector"
        assert findings[0].severity == Severity.WARNING

    def test_has_job_selector_passes(self):
        check = BroadSelectorCheck()
        alert = make_alert(expr='up{job="api"} == 0')
        assert check.check(alert, Config()) == []

    def test_has_namespace_selector_passes(self):
        check = BroadSelectorCheck()
        alert = make_alert(expr='container_memory_usage{namespace="prod"} > 1e9')
        assert check.check(alert, Config()) == []

    def test_selectors_without_scoping_labels_is_info(self):
        check = BroadSelectorCheck()
        # Has selector, but not one of: job, cluster, namespace, service
        alert = make_alert(expr='up{env="prod"} == 0')
        findings = check.check(alert, Config())
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO

    def test_cluster_selector_passes(self):
        check = BroadSelectorCheck()
        alert = make_alert(expr='up{cluster="prod-eu"} == 0')
        assert check.check(alert, Config()) == []
