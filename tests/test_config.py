import textwrap


from par.config import Config, parse_duration


class TestParseDuration:
    def test_minutes(self):
        assert parse_duration("5m") == 300

    def test_seconds(self):
        assert parse_duration("30s") == 30

    def test_hours(self):
        assert parse_duration("2h") == 7200

    def test_compound(self):
        assert parse_duration("1h30m") == 5400

    def test_empty(self):
        assert parse_duration("") == 0

    def test_invalid(self):
        assert parse_duration("abc") == 0


class TestConfigLoad:
    def test_defaults(self):
        config = Config()
        assert "severity" in config.required_labels
        assert "owner" in config.required_labels
        assert "summary" in config.required_annotations
        assert config.for_policy.required is True
        assert config.for_policy.min_seconds == 120

    def test_no_config_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = Config.load(None)
        assert config.required_labels == ["severity", "owner"]

    def test_load_from_file(self, tmp_path):
        f = tmp_path / ".par.yaml"
        f.write_text(textwrap.dedent("""\
            severity_threshold: warning
            required_labels:
              - severity
              - team
            required_annotations:
              - summary
            valid_owners:
              - sre
              - platform
            selector_policy:
              require_one_of:
                - job
                - namespace
            for_policy:
              required_for_alerts: true
              min: 5m
        """))
        config = Config.load(str(f))
        assert config.required_labels == ["severity", "team"]
        assert config.required_annotations == ["summary"]
        assert config.valid_owners == ["sre", "platform"]
        assert config.selector_policy.require_one_of == ["job", "namespace"]
        assert config.for_policy.min_seconds == 300

    def test_auto_discover_par_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / ".par.yaml"
        f.write_text("required_labels:\n  - team\n")
        config = Config.load(None)
        assert config.required_labels == ["team"]

    def test_auto_discover_par_yml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / ".par.yml"
        f.write_text("required_labels:\n  - team\n")
        config = Config.load(None)
        assert config.required_labels == ["team"]

    def test_empty_config_file(self, tmp_path):
        f = tmp_path / ".par.yaml"
        f.write_text("")
        config = Config.load(str(f))
        # Should use defaults
        assert "severity" in config.required_labels
