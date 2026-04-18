from __future__ import annotations

import re
from typing import Optional

import yaml

from .models import AlertRule, RecordingRule


def _parse_suppression_comments(content: str) -> dict:
    """Return {line_number: {rule_id, ...}} for par disable comments."""
    result: dict = {}
    for i, line in enumerate(content.splitlines(), start=1):
        m = re.search(r"#\s*par\s+disable\s+([\w-]+(?:\s*,\s*[\w-]+)*)", line)
        if m:
            ids = {x.strip() for x in m.group(1).split(",")}
            result[i] = ids
    return result


def _build_rule_lines(document_node) -> list:
    """
    Walk the composed YAML node and return a list-of-lists mirroring
    groups[*].rules[*], each entry being the 1-indexed line number of that rule.
    """
    result = []
    if document_node is None:
        return result

    groups_node = None
    for key_node, val_node in document_node.value:
        if key_node.value == "groups":
            groups_node = val_node
            break

    if groups_node is None:
        return result

    for group_node in groups_node.value:
        group_lines = []
        rules_node = None
        for key_node, val_node in group_node.value:
            if key_node.value == "rules":
                rules_node = val_node
                break
        if rules_node is not None:
            for rule_node in rules_node.value:
                group_lines.append(rule_node.start_mark.line + 1)
        result.append(group_lines)

    return result


def load_files(paths: list) -> tuple:
    alerts: list = []
    recordings: list = []
    for path in paths:
        a, r = load_file(path)
        alerts.extend(a)
        recordings.extend(r)
    return alerts, recordings


def load_file(path: str) -> tuple:
    with open(path, encoding="utf-8") as f:
        content = f.read()

    suppression_map = _parse_suppression_comments(content)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error in {path}: {exc}") from exc

    if not isinstance(data, dict):
        return [], []

    try:
        composed = yaml.compose(content)
        rule_lines = _build_rule_lines(composed)
    except Exception:
        rule_lines = []

    alerts: list = []
    recordings: list = []

    for gi, group in enumerate(data.get("groups") or []):
        group_name = str(group.get("name", ""))
        group_rule_lines = rule_lines[gi] if gi < len(rule_lines) else []

        for ri, rule in enumerate(group.get("rules") or []):
            line = group_rule_lines[ri] if ri < len(group_rule_lines) else 0

            # Suppressions are read from the comment on the line immediately above
            suppressed = suppression_map.get(line - 1, set())

            if "alert" in rule:
                raw_for = rule.get("for")
                alerts.append(
                    AlertRule(
                        name=str(rule["alert"]),
                        expr=str(rule.get("expr", "")),
                        for_duration=str(raw_for) if raw_for is not None else None,
                        labels=dict(rule.get("labels") or {}),
                        annotations=dict(rule.get("annotations") or {}),
                        group_name=group_name,
                        file_path=path,
                        line=line,
                        suppressed=suppressed,
                    )
                )
            elif "record" in rule:
                recordings.append(
                    RecordingRule(
                        name=str(rule["record"]),
                        expr=str(rule.get("expr", "")),
                        labels=dict(rule.get("labels") or {}),
                        group_name=group_name,
                        file_path=path,
                        line=line,
                    )
                )

    return alerts, recordings
