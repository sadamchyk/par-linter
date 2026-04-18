---
layout: default
title: required-labels
parent: Checks
nav_order: 3
---

# required-labels

**Severity:** error  
**Category:** metadata

## What it checks

One or more labels configured as required are absent from the alert's `labels` block.

## Why it matters

Alertmanager uses labels to route, group, and silence alerts. The `severity` label is the
most common routing key — without it, an alert may land in the wrong receiver, get silenced
unintentionally, or not get delivered at all.

The `owner` label ensures every alert has a clear responsible team when it fires at 3am,
and enables Alertmanager to route directly to the right receiver without manual triage.

## Examples

**Bad**

```yaml
- alert: HighCpuUsage
  expr: process_cpu_seconds_total{job="api"} > 0.8
  for: 5m
  annotations:
    summary: CPU usage is high
```

**Good**

```yaml
- alert: HighCpuUsage
  expr: process_cpu_seconds_total{job="api"} > 0.8
  for: 5m
  labels:
    severity: warning
    owner: sre
  annotations:
    summary: CPU usage is high
```

## Configuration

```yaml
required_labels:
  - severity
  - owner       # add any additional labels your routing policy requires
```

## Suppression

```yaml
# par disable required-labels
- alert: InfraAlert
  expr: ...
```
