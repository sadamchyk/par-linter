---
layout: default
title: invalid-owner
grand_parent: Documentation
parent: Checks
nav_order: 12
---

# invalid-owner

**Severity:** error  
**Category:** metadata

## What it checks

The alert has an `owner` label, but its value is not in the configured `valid_owners` list.
This check is skipped when `valid_owners` is empty or not configured.

## Why it matters

A misspelled or ad-hoc owner value breaks Alertmanager routing — the alert fires but lands
in the wrong receiver or the default catch-all. Enforcing an allowlist of team names ensures
that ownership is always a deliberate, valid choice and that routing rules can be maintained
with confidence.

## Examples

**Bad** (owner value not in the configured list)

```yaml
- alert: HighSLOBurnRate
  expr: job:http_error_rate:rate5m{job="api"} > 0.01
  for: 5m
  labels:
    severity: critical
    owner: platform        # 'platform' is not in valid_owners
  annotations:
    summary: SLO burn rate is high
```

**Good**

```yaml
- alert: HighSLOBurnRate
  expr: job:http_error_rate:rate5m{job="api"} > 0.01
  for: 5m
  labels:
    severity: critical
    owner: sre
  annotations:
    summary: SLO burn rate is high
```

## Configuration

```yaml
valid_owners:
  - sre
  - dctech
  - infra
```

When `valid_owners` is not set or is an empty list, this check does not run — any owner
value (or no value) is accepted.

## Suppression

```yaml
# par disable invalid-owner
- alert: LegacyAlert
  expr: ...
```
