---
layout: default
title: Checks
nav_order: 2
parent: Documentation
has_children: true
---

# Checks

par runs the following checks on every alerting rule file it processes.
Each check has a short, descriptive name that appears in the output and can be used
in inline suppression comments.

## Catalog

| Check | Severity | Category | Description |
|-------|----------|----------|-------------|
| [for-duration](checks/for-duration.md) | warning | stability | Alert has no `for` duration or duration is too short |
| [absent-selector](checks/absent-selector.md) | warning | stability | `absent()` used without label selectors |
| [required-labels](checks/required-labels.md) | error | metadata | Missing required labels |
| [required-annotations](checks/required-annotations.md) | error / warning | metadata | Missing required annotations |
| [broad-selector](checks/broad-selector.md) | warning / info | selector | Expression has no label selectors or lacks scoping labels |
| [no-comparison](checks/no-comparison.md) | warning | promql | Alert expression has no comparison operator |
| [counter-threshold](checks/counter-threshold.md) | warning | promql | Counter metric used as an absolute threshold |
| [rate-window](checks/rate-window.md) | warning | promql | `rate()` or `irate()` window shorter than 2 minutes |
| [recording-ref](checks/recording-ref.md) | error | dependency | Recording rule referenced but not defined in any loaded file |
| [duplicate-alert](checks/duplicate-alert.md) | error | dependency | Duplicate alert name in the same group |
| [non-base-unit](checks/non-base-unit.md) | info | naming | Metric uses a non-base unit suffix (milliseconds, megabytes, percent…) |
| [invalid-owner](checks/invalid-owner.md) | error | metadata | `owner` label value not in the configured allowlist |

## Suppressing a check

To suppress a specific check for one rule, add a comment on the line immediately above it:

```yaml
# par disable broad-selector
- alert: GlobalHealthCheck
  expr: up == 0
  for: 5m
```

Multiple checks can be suppressed in one comment:

```yaml
# par disable broad-selector, for-duration
- alert: ...
```
