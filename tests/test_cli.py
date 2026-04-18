import os

from par.cli import run


_EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples", "bad_rules.yaml")


def test_lint_finds_issues():
    code = run(["lint", _EXAMPLES, "--format", "json"])
    # bad_rules.yaml has errors → exit code 2
    assert code == 2


def test_lint_min_severity_error():
    code = run(["lint", _EXAMPLES, "--format", "json", "--min-severity", "error"])
    assert code == 2


def test_lint_with_label_filter():
    # Filter to owner=sre; should still find some issues
    code = run(["lint", _EXAMPLES, "--label", "owner=sre"])
    assert code in (0, 1, 2)


def test_lint_nonexistent_file():
    code = run(["lint", "does_not_exist.yaml"])
    assert code == 3


def test_lint_bad_label_format():
    code = run(["lint", _EXAMPLES, "--label", "noequalssign"])
    assert code == 3


def test_summary_runs():
    code = run(["summary", _EXAMPLES, "--format", "json"])
    assert code in (1, 2)


def test_summary_table():
    code = run(["summary", _EXAMPLES, "--format", "table", "--no-color"])
    assert code in (1, 2)


def test_lint_text_format():
    code = run(["lint", _EXAMPLES, "--format", "text", "--no-color"])
    assert code == 2


def test_lint_table_format():
    code = run(["lint", _EXAMPLES, "--format", "table", "--no-color"])
    assert code == 2


def test_lint_sarif_format():
    code = run(["lint", _EXAMPLES, "--format", "sarif"])
    assert code == 2


def test_lint_directory_input(tmp_path):
    rule = tmp_path / "good.yaml"
    rule.write_text(
        "groups:\n"
        "  - name: g\n"
        "    rules:\n"
        "      - alert: OK\n"
        '        expr: up{job="x"} == 0\n'
        "        for: 5m\n"
        "        labels:\n"
        "          severity: warning\n"
        "          owner: sre\n"
        "        annotations:\n"
        "          summary: s\n"
        "          description: d\n"
        "          runbook_url: r\n"
        "          dashboard_url: d\n"
    )
    code = run(["lint", str(tmp_path)])
    assert code == 0
