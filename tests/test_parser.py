import textwrap

import pytest

from par.parser import load_file, _parse_suppression_comments


class TestParseSuppressionComments:
    def test_single_rule(self):
        content = "# par disable for-duration\n- alert: X\n"
        result = _parse_suppression_comments(content)
        assert result == {1: {"for-duration"}}

    def test_multiple_rules(self):
        content = "# par disable for-duration, broad-selector\n- alert: X\n"
        result = _parse_suppression_comments(content)
        assert result == {1: {"for-duration", "broad-selector"}}

    def test_no_comments(self):
        content = "- alert: X\n  expr: up == 0\n"
        assert _parse_suppression_comments(content) == {}


class TestLoadFile:
    def test_alert_parsed(self, tmp_path):
        f = tmp_path / "rules.yaml"
        f.write_text(textwrap.dedent("""\
            groups:
              - name: test
                rules:
                  - alert: Foo
                    expr: up == 0
                    for: 5m
                    labels:
                      severity: warning
                    annotations:
                      summary: bar
        """))
        alerts, recordings = load_file(str(f))
        assert len(alerts) == 1
        assert alerts[0].name == "Foo"
        assert alerts[0].for_duration == "5m"
        assert alerts[0].group_name == "test"
        assert alerts[0].line > 0

    def test_recording_rule_parsed(self, tmp_path):
        f = tmp_path / "rules.yaml"
        f.write_text(textwrap.dedent("""\
            groups:
              - name: recordings
                rules:
                  - record: job:http_errors:rate5m
                    expr: rate(http_errors_total[5m])
        """))
        alerts, recordings = load_file(str(f))
        assert len(alerts) == 0
        assert len(recordings) == 1
        assert recordings[0].name == "job:http_errors:rate5m"

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        alerts, recordings = load_file(str(f))
        assert alerts == []
        assert recordings == []

    def test_no_groups_key(self, tmp_path):
        f = tmp_path / "other.yaml"
        f.write_text("foo: bar\n")
        alerts, recordings = load_file(str(f))
        assert alerts == []
        assert recordings == []

    def test_malformed_yaml_raises(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(":\n  :\n    - [invalid")
        with pytest.raises(ValueError, match="YAML parse error"):
            load_file(str(f))

    def test_suppression_applied(self, tmp_path):
        f = tmp_path / "rules.yaml"
        f.write_text(textwrap.dedent("""\
            groups:
              - name: test
                rules:
                  # par disable for-duration
                  - alert: Foo
                    expr: up == 0
                    labels:
                      severity: warning
        """))
        alerts, _ = load_file(str(f))
        assert "for-duration" in alerts[0].suppressed

    def test_mixed_rules(self, tmp_path):
        f = tmp_path / "rules.yaml"
        f.write_text(textwrap.dedent("""\
            groups:
              - name: mixed
                rules:
                  - alert: A
                    expr: up == 0
                    for: 5m
                    labels: {}
                  - record: job:x:rate5m
                    expr: rate(x[5m])
                  - alert: B
                    expr: up == 1
                    for: 5m
                    labels: {}
        """))
        alerts, recordings = load_file(str(f))
        assert len(alerts) == 2
        assert len(recordings) == 1
        assert alerts[0].name == "A"
        assert alerts[1].name == "B"
