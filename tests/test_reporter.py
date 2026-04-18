import io
import json

from par.models import Finding, Severity
from par.reporter import print_json, print_sarif, print_text, print_table, print_summary_json, print_summary_table
from .conftest import make_alert


def _make_finding(**kwargs):
    defaults = dict(
        rule_id="test-check",
        severity=Severity.WARNING,
        alert_name="TestAlert",
        group_name="test_group",
        file_path="test.yaml",
        line=10,
        message="Something is wrong",
        suggestion="Fix it",
        owner="sre",
    )
    defaults.update(kwargs)
    return Finding(**defaults)


class TestPrintText:
    def test_empty_findings(self):
        out = io.StringIO()
        print_text([], ["a.yaml"], 3, 1, use_color=False, out=out)
        text = out.getvalue()
        assert "Files: 1" in text
        assert "Errors: 0" in text

    def test_findings_grouped(self):
        out = io.StringIO()
        findings = [
            _make_finding(severity=Severity.ERROR, message="bad"),
            _make_finding(severity=Severity.WARNING, message="meh"),
        ]
        print_text(findings, ["a.yaml"], 2, 0, use_color=False, out=out)
        text = out.getvalue()
        assert "ERROR" in text
        assert "WARN" in text
        assert "Errors: 1" in text

    def test_owner_shown(self):
        out = io.StringIO()
        print_text([_make_finding(owner="sre")], ["a.yaml"], 1, 0, use_color=False, out=out)
        assert "owner: sre" in out.getvalue()


class TestPrintJson:
    def test_structure(self):
        out = io.StringIO()
        findings = [_make_finding()]
        print_json(findings, ["a.yaml"], 2, 1, out=out)
        data = json.loads(out.getvalue())
        assert data["summary"]["files"] == 1
        assert data["summary"]["alert_rules"] == 2
        assert len(data["findings"]) == 1
        assert data["findings"][0]["rule_id"] == "test-check"

    def test_empty(self):
        out = io.StringIO()
        print_json([], ["a.yaml", "b.yaml"], 0, 0, out=out)
        data = json.loads(out.getvalue())
        assert data["summary"]["errors"] == 0
        assert data["findings"] == []


class TestPrintTable:
    def test_renders_rows(self):
        out = io.StringIO()
        findings = [_make_finding(), _make_finding(severity=Severity.ERROR)]
        print_table(findings, ["a.yaml"], 2, 0, use_color=False, out=out)
        text = out.getvalue()
        assert "TestAlert" in text
        assert "test-check" in text
        assert "┌" in text  # table border


class TestPrintSummaryJson:
    def test_status_logic(self):
        out = io.StringIO()
        alerts = [make_alert(labels={"owner": "sre", "severity": "warning"})]
        findings = [_make_finding(severity=Severity.WARNING)]
        print_summary_json(findings, alerts, ["a.yaml"], 0, out=out)
        data = json.loads(out.getvalue())
        owner = data["owners"][0]
        assert owner["status"] == "warnings"

    def test_clean_status(self):
        out = io.StringIO()
        alerts = [make_alert(labels={"owner": "sre", "severity": "warning"})]
        print_summary_json([], alerts, ["a.yaml"], 0, out=out)
        data = json.loads(out.getvalue())
        owner = data["owners"][0]
        assert owner["status"] == "clean"

    def test_error_status(self):
        out = io.StringIO()
        alerts = [make_alert(labels={"owner": "sre", "severity": "warning"})]
        findings = [_make_finding(severity=Severity.ERROR)]
        print_summary_json(findings, alerts, ["a.yaml"], 0, out=out)
        data = json.loads(out.getvalue())
        owner = data["owners"][0]
        assert owner["status"] == "issues"


class TestPrintSarif:
    def test_valid_sarif_structure(self):
        out = io.StringIO()
        findings = [
            _make_finding(rule_id="for-duration", severity=Severity.WARNING, line=5),
            _make_finding(rule_id="required-labels", severity=Severity.ERROR, line=10),
        ]
        print_sarif(findings, ["a.yaml"], 2, 1, out=out)
        data = json.loads(out.getvalue())

        assert data["version"] == "2.1.0"
        assert "$schema" in data
        assert len(data["runs"]) == 1

        run = data["runs"][0]
        assert run["tool"]["driver"]["name"] == "par"
        assert len(run["tool"]["driver"]["rules"]) == 2
        assert len(run["results"]) == 2

    def test_severity_mapping(self):
        out = io.StringIO()
        findings = [
            _make_finding(severity=Severity.ERROR),
            _make_finding(rule_id="warn-check", severity=Severity.WARNING),
            _make_finding(rule_id="info-check", severity=Severity.INFO),
        ]
        print_sarif(findings, ["a.yaml"], 1, 0, out=out)
        data = json.loads(out.getvalue())
        levels = [r["level"] for r in data["runs"][0]["results"]]
        assert levels == ["error", "warning", "note"]

    def test_location_has_line(self):
        out = io.StringIO()
        print_sarif([_make_finding(line=42)], ["a.yaml"], 1, 0, out=out)
        data = json.loads(out.getvalue())
        loc = data["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        assert loc["region"]["startLine"] == 42
        assert loc["artifactLocation"]["uri"] == "test.yaml"

    def test_zero_line_omits_region(self):
        out = io.StringIO()
        print_sarif([_make_finding(line=0)], ["a.yaml"], 1, 0, out=out)
        data = json.loads(out.getvalue())
        region = data["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]
        assert region == {}

    def test_empty_findings(self):
        out = io.StringIO()
        print_sarif([], ["a.yaml"], 0, 0, out=out)
        data = json.loads(out.getvalue())
        assert data["runs"][0]["results"] == []
        assert data["runs"][0]["tool"]["driver"]["rules"] == []

    def test_message_includes_suggestion(self):
        out = io.StringIO()
        print_sarif([_make_finding(message="bad thing", suggestion="do better")], ["a.yaml"], 1, 0, out=out)
        data = json.loads(out.getvalue())
        msg = data["runs"][0]["results"][0]["message"]["text"]
        assert "bad thing" in msg
        assert "Fix: do better" in msg

    def test_rules_deduplicated(self):
        out = io.StringIO()
        findings = [
            _make_finding(rule_id="for-duration", alert_name="A"),
            _make_finding(rule_id="for-duration", alert_name="B"),
            _make_finding(rule_id="broad-selector", alert_name="C"),
        ]
        print_sarif(findings, ["a.yaml"], 3, 0, out=out)
        data = json.loads(out.getvalue())
        rules = data["runs"][0]["tool"]["driver"]["rules"]
        assert len(rules) == 2
        rule_ids = [r["id"] for r in rules]
        assert "for-duration" in rule_ids
        assert "broad-selector" in rule_ids

    def test_rule_index_matches(self):
        out = io.StringIO()
        findings = [
            _make_finding(rule_id="broad-selector"),
            _make_finding(rule_id="for-duration"),
        ]
        print_sarif(findings, ["a.yaml"], 2, 0, out=out)
        data = json.loads(out.getvalue())
        rules = data["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = [r["id"] for r in rules]
        for result in data["runs"][0]["results"]:
            assert rule_ids[result["ruleIndex"]] == result["ruleId"]


class TestPrintSummaryTable:
    def test_renders(self):
        out = io.StringIO()
        alerts = [make_alert(labels={"owner": "sre", "severity": "warning"})]
        findings = [_make_finding(severity=Severity.ERROR)]
        print_summary_table(findings, alerts, ["a.yaml"], 0, use_color=False, out=out)
        text = out.getvalue()
        assert "sre" in text
        assert "ISSUES" in text
