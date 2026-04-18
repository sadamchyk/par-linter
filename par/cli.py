from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .checks.metadata import InvalidOwnerCheck, MissingAnnotationsCheck, MissingLabelsCheck
from .checks.naming import NonBaseUnitCheck
from .checks.selectors import BroadSelectorCheck
from .checks.stability import (
    AbsentWithoutSelectorCheck,
    MissingForCheck,
    SuspiciousRateWindowCheck,
)
from .checks.structure import (
    BrokenDependencyCheck,
    CounterAsThresholdCheck,
    DuplicateRuleCheck,
    NoComparisonCheck,
)
from .config import Config
from .models import Finding, Severity
from .parser import load_files
from .reporter import print_json, print_sarif, print_summary_json, print_summary_table, print_table, print_text

_YAML_SUFFIXES = {".yaml", ".yml"}

_ALERT_CHECKS = [
    MissingForCheck(),
    AbsentWithoutSelectorCheck(),
    SuspiciousRateWindowCheck(),
    MissingLabelsCheck(),
    MissingAnnotationsCheck(),
    InvalidOwnerCheck(),
    BroadSelectorCheck(),
    NoComparisonCheck(),
    CounterAsThresholdCheck(),
    NonBaseUnitCheck(),
]

_CORPUS_CHECKS = [
    DuplicateRuleCheck(),
    BrokenDependencyCheck(),
]


def _resolve_paths(inputs: list) -> list:
    result = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            found = sorted(f for f in p.rglob("*") if f.suffix in _YAML_SUFFIXES)
            result.extend(str(f) for f in found)
        else:
            if p.suffix not in _YAML_SUFFIXES:
                print(f"par: warning: {p} does not look like a YAML file", file=sys.stderr)
            result.append(str(p))
    return result


def _parse_labels(raw_labels: list) -> tuple[dict, int]:
    selectors: dict = {}
    for raw in raw_labels:
        if "=" not in raw:
            print(f"par: --label requires KEY=VALUE format, got: {raw!r}", file=sys.stderr)
            return {}, 3
        k, _, v = raw.partition("=")
        selectors[k.strip()] = v.strip()
    return selectors, 0


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("files", nargs="+", metavar="PATH", help="Rule YAML file(s) or director(ies).")
    p.add_argument("--format", choices=["text", "json", "table", "sarif"], default="text", help="Output format (default: text). Use 'sarif' for GitHub Actions integration.")
    p.add_argument("--config", metavar="FILE", help="Config file (default: .par.yaml)")
    p.add_argument("--label", metavar="KEY=VALUE", action="append", dest="labels", default=[], help="Only include alerts matching KEY=VALUE. Repeatable.")
    p.add_argument("--no-color", action="store_true", help="Disable colored output")
    p.add_argument("--force-color", action="store_true", help="Force colored output even when stdout is not a TTY")


def _load(args) -> tuple:
    try:
        config = Config.load(args.config)
    except Exception as exc:
        print(f"par: config error: {exc}", file=sys.stderr)
        return None, None, None, None, 3

    label_selectors, err = _parse_labels(args.labels)
    if err:
        return None, None, None, None, err

    try:
        resolved = _resolve_paths(args.files)
    except OSError as exc:
        print(f"par: {exc}", file=sys.stderr)
        return None, None, None, None, 3

    if not resolved:
        print("par: no YAML files found in the provided paths", file=sys.stderr)
        return None, None, None, None, 3

    try:
        alerts, recordings = load_files(resolved)
    except (ValueError, OSError) as exc:
        print(f"par: {exc}", file=sys.stderr)
        return None, None, None, None, 3

    if label_selectors:
        alerts = [a for a in alerts if all(a.labels.get(k) == v for k, v in label_selectors.items())]

    return config, resolved, alerts, recordings, 0


def _collect_findings(alerts, recordings, config) -> list[Finding]:
    findings: list = []
    alert_lookup = {(a.file_path, a.group_name, a.name): a for a in alerts}

    for alert in alerts:
        for check in _ALERT_CHECKS:
            for finding in check.check(alert, config):
                if finding.rule_id not in alert.suppressed:
                    finding.owner = alert.labels.get("owner", "")
                    findings.append(finding)

    for check in _CORPUS_CHECKS:
        for finding in check.check(alerts, recordings, config):
            alert_obj = next(
                (
                    a
                    for a in alerts
                    if a.name == finding.alert_name
                    and a.group_name == finding.group_name
                    and (finding.line == 0 or a.line == finding.line)
                ),
                None,
            )
            if alert_obj is None or finding.rule_id not in alert_obj.suppressed:
                finding.owner = alert_obj.labels.get("owner", "") if alert_obj else ""
                findings.append(finding)

    return findings


def _run_lint(args) -> int:
    config, resolved, alerts, recordings, err = _load(args)
    if err:
        return err

    if args.min_severity is not None:
        config.severity_threshold = Severity(args.min_severity)

    findings = _collect_findings(alerts, recordings, config)
    filtered = [f for f in findings if f.severity >= config.severity_threshold]
    filtered.sort(key=lambda f: (-f.severity.rank, f.file_path, f.line))

    use_color = not args.no_color and (args.force_color or sys.stdout.isatty())

    if args.format == "json":
        print_json(filtered, resolved, len(alerts), len(recordings))
    elif args.format == "sarif":
        print_sarif(filtered, resolved, len(alerts), len(recordings))
    elif args.format == "table":
        print_table(filtered, resolved, len(alerts), len(recordings), use_color=use_color)
    else:
        print_text(filtered, resolved, len(alerts), len(recordings), use_color=use_color)

    has_errors = any(f.severity == Severity.ERROR for f in filtered)
    has_warnings = any(f.severity == Severity.WARNING for f in filtered)
    if has_errors:
        return 2
    if has_warnings:
        return 1
    return 0


def _run_summary(args) -> int:
    config, resolved, alerts, recordings, err = _load(args)
    if err:
        return err

    findings = _collect_findings(alerts, recordings, config)

    use_color = not args.no_color and (args.force_color or sys.stdout.isatty())

    if args.format == "json":
        print_summary_json(findings, alerts, resolved, len(recordings))
    else:
        print_summary_table(findings, alerts, resolved, len(recordings), use_color=use_color)

    has_errors = any(f.severity == Severity.ERROR for f in findings)
    has_warnings = any(f.severity == Severity.WARNING for f in findings)
    if has_errors:
        return 2
    if has_warnings:
        return 1
    return 0


_CHECK_TABLE = """\
  Checks:
    for-duration        [warn]  Alert has no or too-short 'for' duration
    absent-selector     [warn]  absent() used without label selectors
    rate-window         [warn]  rate()/irate() window shorter than 2 minutes
    required-labels     [error] Missing required labels (severity, owner, …)
    required-annotations[error] Missing required annotations (summary, runbook_url, …)
    invalid-owner       [error] Owner label not in the configured allowlist
    broad-selector      [warn]  Selector too broad or missing scoping labels
    no-comparison       [warn]  Alert expression lacks a comparison operator
    counter-threshold   [warn]  Counter metric used as an absolute threshold
    non-base-unit       [info]  Metric uses a non-base unit suffix (e.g. milliseconds)
    duplicate-alert     [error] Duplicate alert name in the same group
    recording-ref       [error] Recording rule referenced but not defined"""

_EXAMPLES = """\
  Examples:
    par lint rules/
    par lint rules/*.yaml --format json
    par lint rules/ --config .par.yaml --min-severity warning
    par lint rules/ --label team=sre --format table
    par lint rules/ --format sarif > par.sarif
    par summary rules/
    par summary rules/ --format json

  GitHub Actions usage:
    - name: Run par linter
      run: par lint rules/ --format sarif > par.sarif
    - name: Upload SARIF
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: par.sarif"""

_SUPPRESSION = """\
  Inline suppression:
    Add a comment on the line immediately above a rule to suppress a check:
      # par disable <check-id>[, <check-id>, ...]
    Example:
      # par disable broad-selector
      - alert: GlobalScrapeFailure
        expr: up == 0"""

_CONFIG_HELP = """\
  Configuration (.par.yaml):
    severity_threshold:  minimum severity to report (error | warning | info)
    required_labels:     list of labels every alert must have
    required_annotations: list of annotations every alert must have
    valid_owners:        allowlist for the owner label (empty = skip check)
    selector_policy:
      require_one_of:    scoping labels (default: job, cluster, namespace, service)
    for_policy:
      required_for_alerts: true/false
      min:               minimum 'for' duration (default: 2m)"""


def run(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="par",
        description="PAR — Prometheus Alert Rule linter.\n\n"
        "Analyzes Prometheus alerting rule files and flags quality issues\n"
        "that make alerts noisy, flaky, or hard to act on during an incident.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"{_CHECK_TABLE}\n\n"
            f"{_CONFIG_HELP}\n\n"
            f"{_SUPPRESSION}\n\n"
            f"{_EXAMPLES}\n\n"
            "  Exit codes:\n"
            "    0  no findings\n"
            "    1  warnings found, no errors\n"
            "    2  errors found\n"
            "    3  input/config error"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    lint_p = subparsers.add_parser(
        "lint",
        help="Check rules and report findings",
        description="Run all checks against the given rule files and report findings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"{_CHECK_TABLE}\n\n"
            f"{_SUPPRESSION}\n\n"
            "  Examples:\n"
            "    par lint rules/*.yaml\n"
            "    par lint rules/ --format json\n"
            "    par lint rules/ --min-severity warning --label team=sre\n"
            "    par lint rules/ --format table --force-color\n"
            "    par lint rules/ --format sarif > par.sarif"
        ),
    )
    _add_common_args(lint_p)
    lint_p.add_argument(
        "--min-severity",
        choices=["error", "warning", "info"],
        default=None,
        help="Only report findings at or above this level (default: info)",
    )

    sum_p = subparsers.add_parser(
        "summary",
        help="Show a per-owner health summary",
        description="Show a per-owner summary table with finding counts and health status.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "  Status values:\n"
            "    CLEAN     no errors or warnings\n"
            "    WARNINGS  warnings found, no errors\n"
            "    ISSUES    errors found\n\n"
            "  Examples:\n"
            "    par summary rules/\n"
            "    par summary rules/ --format json\n"
            "    par summary rules/ --label team=sre --no-color"
        ),
    )
    _add_common_args(sum_p)

    args = parser.parse_args(argv)

    if args.command == "lint":
        return _run_lint(args)
    return _run_summary(args)


def main() -> None:
    sys.exit(run())
