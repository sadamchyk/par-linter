from par.checks.metadata import InvalidOwnerCheck, MissingAnnotationsCheck, MissingLabelsCheck
from par.config import Config
from par.models import Severity
from .conftest import make_alert


def test_missing_severity_label():
    check = MissingLabelsCheck()
    alert = make_alert(labels={"owner": "sre"})
    findings = check.check(alert, Config())
    assert len(findings) == 1
    assert findings[0].rule_id == "required-labels"
    assert "severity" in findings[0].message
    assert findings[0].severity == Severity.ERROR


def test_present_required_labels():
    check = MissingLabelsCheck()
    alert = make_alert(labels={"severity": "warning", "owner": "sre"})
    assert check.check(alert, Config()) == []


def test_custom_required_label():
    check = MissingLabelsCheck()
    config = Config()
    config.required_labels = ["severity", "team"]
    alert = make_alert(labels={"severity": "warning"})
    findings = check.check(alert, config)
    assert len(findings) == 1
    assert "team" in findings[0].message


def test_missing_summary_is_error():
    check = MissingAnnotationsCheck()
    alert = make_alert(annotations={})
    findings = check.check(alert, Config())
    summary_finding = next(f for f in findings if "summary" in f.message)
    assert summary_finding.severity == Severity.ERROR


def test_missing_description_is_warning():
    check = MissingAnnotationsCheck()
    alert = make_alert(annotations={"summary": "x", "runbook_url": "x"})
    findings = check.check(alert, Config())
    desc = next(f for f in findings if "description" in f.message)
    assert desc.severity == Severity.WARNING


def test_missing_runbook_is_error():
    check = MissingAnnotationsCheck()
    alert = make_alert(annotations={"summary": "x", "description": "x"})
    findings = check.check(alert, Config())
    runbook = next(f for f in findings if "runbook_url" in f.message)
    assert runbook.severity == Severity.ERROR


def test_missing_dashboard_url_is_warning():
    check = MissingAnnotationsCheck()
    alert = make_alert(annotations={"summary": "x", "description": "x", "runbook_url": "x"})
    findings = check.check(alert, Config())
    assert len(findings) == 1
    assert "dashboard_url" in findings[0].message
    assert findings[0].severity == Severity.WARNING


def test_all_annotations_present():
    check = MissingAnnotationsCheck()
    alert = make_alert(annotations={"summary": "x", "description": "x", "runbook_url": "x", "dashboard_url": "x"})
    assert check.check(alert, Config()) == []


def test_missing_owner_label_is_error():
    check = MissingLabelsCheck()
    alert = make_alert(labels={"severity": "warning"})
    findings = check.check(alert, Config())
    assert len(findings) == 1
    assert "owner" in findings[0].message
    assert findings[0].severity == Severity.ERROR


def test_invalid_owner_flagged():
    check = InvalidOwnerCheck()
    config = Config()
    config.valid_owners = ["sre", "dctech"]
    alert = make_alert(labels={"severity": "warning", "owner": "platform"})
    findings = check.check(alert, config)
    assert len(findings) == 1
    assert findings[0].rule_id == "invalid-owner"
    assert "platform" in findings[0].message
    assert findings[0].severity == Severity.ERROR


def test_valid_owner_passes():
    check = InvalidOwnerCheck()
    config = Config()
    config.valid_owners = ["sre", "dctech"]
    alert = make_alert(labels={"severity": "warning", "owner": "sre"})
    assert check.check(alert, config) == []


def test_no_valid_owners_configured_skips_validation():
    check = InvalidOwnerCheck()
    config = Config()
    config.valid_owners = []
    alert = make_alert(labels={"severity": "warning", "owner": "any-team"})
    assert check.check(alert, config) == []
