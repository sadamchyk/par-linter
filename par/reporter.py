from __future__ import annotations

import json
import sys
import textwrap
from typing import TextIO

from .models import Finding, Severity

_COLOR = {
    Severity.ERROR: "\033[91m",
    Severity.WARNING: "\033[93m",
    Severity.INFO: "\033[94m",
    "bold": "\033[1m",
    "reset": "\033[0m",
    "dim": "\033[2m",
}

_LABEL = {
    Severity.ERROR: "ERROR",
    Severity.WARNING: "WARN ",
    Severity.INFO: "INFO ",
}


def _c(text: str, *codes: str, use_color: bool) -> str:
    if not use_color:
        return text
    return "".join(codes) + text + _COLOR["reset"]


def print_text(
    findings: list,
    files: list,
    alert_count: int,
    recording_count: int,
    use_color: bool = True,
    out: TextIO = sys.stdout,
) -> None:
    def _loc(f: Finding) -> str:
        return f"{f.file_path}:{f.line}" if f.line else f.file_path

    groups = {
        Severity.ERROR: [f for f in findings if f.severity == Severity.ERROR],
        Severity.WARNING: [f for f in findings if f.severity == Severity.WARNING],
        Severity.INFO: [f for f in findings if f.severity == Severity.INFO],
    }

    for severity, items in groups.items():
        if not items:
            continue
        label = _LABEL[severity]
        header = f"\n{label.strip()} ({len(items)})\n" + "─" * 60
        out.write(_c(header, _COLOR[severity], _COLOR["bold"], use_color=use_color) + "\n")
        for f in items:
            tag = _c(f"[{f.rule_id}]", _COLOR[severity], use_color=use_color)
            name = _c(f.alert_name, _COLOR["bold"], use_color=use_color)
            loc = _c(_loc(f), _COLOR["dim"], use_color=use_color)
            out.write(f"{tag} {name}  {loc}\n")
            if f.owner:
                out.write(f"       owner: {f.owner}\n")
            out.write(f"       {f.message}\n")
            out.write(_c(f"       Fix: {f.suggestion}\n\n", _COLOR["dim"], use_color=use_color))

    out.write("─" * 60 + "\n")
    out.write(
        f"Files: {len(files)}  "
        f"Alert rules: {alert_count}  "
        f"Recording rules: {recording_count}\n"
    )
    errors = len(groups[Severity.ERROR])
    warnings = len(groups[Severity.WARNING])
    infos = len(groups[Severity.INFO])
    out.write(f"Errors: {errors}  Warnings: {warnings}  Info: {infos}\n")


def print_table(
    findings: list,
    files: list,
    alert_count: int,
    recording_count: int,
    use_color: bool = True,
    out: TextIO = sys.stdout,
) -> None:
    _SEV_LABEL = {Severity.ERROR: "ERROR", Severity.WARNING: "WARN ", Severity.INFO: "INFO "}

    headers = ["ALERT", "CHECK", "SEV", "DESCRIPTION"]

    col_alert = max(len("ALERT"), max((len(f.alert_name) for f in findings), default=0))
    col_check = max(len("CHECK"), max((len(f.rule_id) for f in findings), default=0))
    col_sev = 5
    col_desc = 80

    widths = [col_alert, col_check, col_sev, col_desc]

    def _sep(left, mid, right):
        return left + mid.join("─" * (w + 2) for w in widths) + right

    sep_top = _sep("┌", "┬", "┐")
    sep_mid = _sep("├", "┼", "┤")
    sep_bot = _sep("└", "┴", "┘")

    def _render_row(cells, finding=None):
        parts = []
        for i, (cell, w) in enumerate(zip(cells, widths)):
            padded = cell.ljust(w)
            if use_color and finding and i == 2:
                padded = _c(padded, _COLOR[finding.severity], use_color=True)
            parts.append(f" {padded} ")
        return "│" + "│".join(parts) + "│"

    out.write(sep_top + "\n")
    out.write(_render_row(headers) + "\n")
    out.write(sep_mid + "\n")

    for i, f in enumerate(findings):
        sev = _SEV_LABEL[f.severity]
        desc_lines = textwrap.wrap(f.message, col_desc) or [f.message]

        out.write(_render_row([f.alert_name, f.rule_id, sev, desc_lines[0]], finding=f) + "\n")
        for extra in desc_lines[1:]:
            out.write(_render_row(["", "", "", extra]) + "\n")

        if i < len(findings) - 1:
            out.write(sep_mid + "\n")

    out.write(sep_bot + "\n")

    errors = sum(1 for f in findings if f.severity == Severity.ERROR)
    warnings = sum(1 for f in findings if f.severity == Severity.WARNING)
    infos = sum(1 for f in findings if f.severity == Severity.INFO)
    out.write(
        f"\nFiles: {len(files)}  Alert rules: {alert_count}  "
        f"Recording rules: {recording_count}\n"
    )
    out.write(f"Errors: {errors}  Warnings: {warnings}  Info: {infos}\n")


def _owner_buckets(findings: list, alerts: list) -> tuple[dict, dict, list]:
    """Return (finding_counts, alert_counts, sorted_owners) keyed by owner label."""
    from collections import defaultdict

    lookup = {(a.file_path, a.group_name, a.name): a.labels.get("owner", "(none)") for a in alerts}

    finding_counts: dict = defaultdict(lambda: {"errors": 0, "warnings": 0, "info": 0})
    for f in findings:
        owner = lookup.get((f.file_path, f.group_name, f.alert_name), "(none)")
        if f.severity == Severity.ERROR:
            finding_counts[owner]["errors"] += 1
        elif f.severity == Severity.WARNING:
            finding_counts[owner]["warnings"] += 1
        else:
            finding_counts[owner]["info"] += 1

    alert_counts: dict = defaultdict(int)
    for a in alerts:
        alert_counts[a.labels.get("owner", "(none)")] += 1

    all_owners = sorted(set(alert_counts) | set(finding_counts), key=lambda o: "\xff" if o == "(none)" else o)
    return finding_counts, alert_counts, all_owners


def print_summary_table(
    findings: list,
    alerts: list,
    files: list,
    recording_count: int,
    use_color: bool = True,
    out: TextIO = sys.stdout,
) -> None:
    _STATUS_COLOR = {"CLEAN": "\033[92m", "ISSUES": "\033[91m", "WARNINGS": "\033[93m"}

    finding_counts, alert_counts, owners = _owner_buckets(findings, alerts)

    headers = ["OWNER", "ALERTS", "ERRORS", "WARN", "INFO", "STATUS"]
    col_owner = max(len("OWNER"), max((len(o) for o in owners), default=0))
    widths = [col_owner, len("ALERTS"), len("ERRORS"), len("WARN"), len("INFO"), len("WARNINGS")]

    def _sep(left, mid, right):
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def _render_row(cells, status=None):
        parts = []
        for i, (cell, w) in enumerate(zip(cells, widths)):
            padded = cell.ljust(w)
            if use_color and status and i == 5:
                padded = _STATUS_COLOR.get(status, "") + padded + _COLOR["reset"]
            parts.append(f" {padded} ")
        return "│" + "│".join(parts) + "│"

    out.write(_sep("┌", "┬", "┐") + "\n")
    out.write(_render_row(headers) + "\n")
    out.write(_sep("├", "┼", "┤") + "\n")

    for i, owner in enumerate(owners):
        c = finding_counts[owner]
        if c["errors"] > 0:
            status = "ISSUES"
        elif c["warnings"] > 0:
            status = "WARNINGS"
        else:
            status = "CLEAN"
        row = [owner, str(alert_counts[owner]), str(c["errors"]), str(c["warnings"]), str(c["info"]), status]
        out.write(_render_row(row, status=status) + "\n")
        if i < len(owners) - 1:
            out.write(_sep("├", "┼", "┤") + "\n")

    out.write(_sep("└", "┴", "┘") + "\n")

    total_errors = sum(1 for f in findings if f.severity == Severity.ERROR)
    total_warnings = sum(1 for f in findings if f.severity == Severity.WARNING)
    total_info = sum(1 for f in findings if f.severity == Severity.INFO)
    out.write(f"\nFiles: {len(files)}  Alert rules: {len(alerts)}  Recording rules: {recording_count}\n")
    out.write(f"Errors: {total_errors}  Warnings: {total_warnings}  Info: {total_info}\n")


def print_summary_json(
    findings: list,
    alerts: list,
    files: list,
    recording_count: int,
    out: TextIO = sys.stdout,
) -> None:
    finding_counts, alert_counts, owners = _owner_buckets(findings, alerts)

    owners_data = []
    for owner in owners:
        c = finding_counts[owner]
        if c["errors"] > 0:
            status = "issues"
        elif c["warnings"] > 0:
            status = "warnings"
        else:
            status = "clean"
        owners_data.append({
            "owner": owner,
            "alerts": alert_counts[owner],
            "errors": c["errors"],
            "warnings": c["warnings"],
            "info": c["info"],
            "status": status,
        })

    total_errors = sum(1 for f in findings if f.severity == Severity.ERROR)
    total_warnings = sum(1 for f in findings if f.severity == Severity.WARNING)
    total_info = sum(1 for f in findings if f.severity == Severity.INFO)

    data = {
        "summary": {
            "files": len(files),
            "alert_rules": len(alerts),
            "recording_rules": recording_count,
            "errors": total_errors,
            "warnings": total_warnings,
            "info": total_info,
        },
        "owners": owners_data,
    }
    json.dump(data, out, indent=2)
    out.write("\n")


_SARIF_SEVERITY = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
}

_CHECK_DESCRIPTIONS = {
    "for-duration": "Alert has no or too-short 'for' duration.",
    "absent-selector": "absent() used without label selectors.",
    "rate-window": "rate()/irate() window shorter than 2 minutes.",
    "required-labels": "Missing required labels.",
    "required-annotations": "Missing required annotations.",
    "invalid-owner": "Owner label not in the configured allowlist.",
    "broad-selector": "Selector too broad or missing scoping labels.",
    "no-comparison": "Alert expression lacks a comparison operator.",
    "counter-threshold": "Counter metric used as an absolute threshold.",
    "non-base-unit": "Metric uses a non-base unit suffix.",
    "duplicate-alert": "Duplicate alert name in the same group.",
    "recording-ref": "Recording rule referenced but not defined.",
}


def print_sarif(
    findings: list,
    files: list,
    alert_count: int,
    recording_count: int,
    out: TextIO = sys.stdout,
) -> None:
    rule_ids = sorted({f.rule_id for f in findings})
    rules = [
        {
            "id": rid,
            "shortDescription": {"text": _CHECK_DESCRIPTIONS.get(rid, rid)},
        }
        for rid in rule_ids
    ]
    rule_index = {rid: i for i, rid in enumerate(rule_ids)}

    results = []
    for f in findings:
        region = {"startLine": f.line} if f.line else {}
        result = {
            "ruleId": f.rule_id,
            "ruleIndex": rule_index[f.rule_id],
            "level": _SARIF_SEVERITY[f.severity],
            "message": {"text": f"{f.message}\nFix: {f.suggestion}"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.file_path},
                        "region": region,
                    }
                }
            ],
        }
        results.append(result)

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "par",
                        "informationUri": "https://github.com/stadamch/par-linter",
                        "version": "0.1.0",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
    json.dump(sarif, out, indent=2)
    out.write("\n")


def print_json(
    findings: list,
    files: list,
    alert_count: int,
    recording_count: int,
    out: TextIO = sys.stdout,
) -> None:
    errors = sum(1 for f in findings if f.severity == Severity.ERROR)
    warnings = sum(1 for f in findings if f.severity == Severity.WARNING)
    infos = sum(1 for f in findings if f.severity == Severity.INFO)
    data = {
        "summary": {
            "files": len(files),
            "alert_rules": alert_count,
            "recording_rules": recording_count,
            "errors": errors,
            "warnings": warnings,
            "info": infos,
        },
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity.value,
                "alert": f.alert_name,
                "group": f.group_name,
                "file": f.file_path,
                "line": f.line,
                "message": f.message,
                "suggestion": f.suggestion,
            }
            for f in findings
        ],
    }
    json.dump(data, out, indent=2)
    out.write("\n")
