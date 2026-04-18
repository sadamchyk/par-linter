---
layout: default
title: duplicate-alert
grand_parent: Documentation
parent: Checks
nav_order: 10
---

# duplicate-alert

**Severity:** error  
**Category:** dependency

## What it checks

Two alerting rules in the same group share the same `alert` name.

## Why it matters

When two rules in the same group have the same name, Prometheus silently uses the last
definition and discards the first. The earlier alert is never evaluated. This is almost
always a copy-paste mistake. Symptoms include:

- An alert threshold that "doesn't work" because the rule defining it was discarded.
- Alertmanager deduplication behaving unexpectedly because alert identity is based on name.
- Inhibition rules not firing because the expected alert name is never produced.

## Examples

**Bad**

```yaml
groups:
  - name: disk_alerts
    rules:
      - alert: DiskFull
        expr: disk_used_percent{job="node"} > 90
        for: 5m
        labels:
          severity: warning

      - alert: DiskFull          # silently overrides the first
        expr: disk_used_percent{job="node"} > 95
        for: 5m
        labels:
          severity: critical
```

**Good — use distinct names**

```yaml
groups:
  - name: disk_alerts
    rules:
      - alert: DiskAlmostFull
        expr: disk_used_percent{job="node"} > 90
        for: 5m
        labels:
          severity: warning

      - alert: DiskFull
        expr: disk_used_percent{job="node"} > 95
        for: 5m
        labels:
          severity: critical
```

## Suppression

If the duplication is intentional, suppress the check on the second definition:

```yaml
# par disable duplicate-alert
- alert: DiskFull
  expr: disk_used_percent{job="node"} > 95
```
