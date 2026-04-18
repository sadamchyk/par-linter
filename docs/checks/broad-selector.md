---
layout: default
title: broad-selector
grand_parent: Documentation
parent: Checks
nav_order: 5
---

# broad-selector

**Severity:** warning (no selectors at all), info (selectors present but no scoping labels)  
**Category:** selector

## What it checks

The alert expression either has no label selectors at all, or has selectors that do not
include any of the recommended scoping labels (`job`, `cluster`, `namespace`, `service`).

## Why it matters

An expression like `up == 0` fires for every target across every environment, cluster, and
job. In large organisations this means:

- Staging outages page the production on-call.
- Deduplication in Alertmanager becomes unreliable.
- Production runbooks get triggered for unrelated services.

Adding even one scoping label like `job="api"` or `cluster="prod"` constrains the alert to
the intended target.

## Severity distinction

| Situation | Severity | Reason |
|-----------|----------|--------|
| No `{...}` selectors at all | warning | Fires globally — almost certainly unintentional |
| Has selectors but missing `job`/`cluster`/`namespace`/`service` | info | May be fine with other labels; worth reviewing |

## Examples

**Bad — no selectors**

```yaml
- alert: TargetDown
  expr: up == 0
  for: 5m
```

**Acceptable but worth reviewing — selectors present but no recommended scoping label**

```yaml
- alert: TargetDown
  expr: up{env="prod"} == 0
  for: 5m
```

**Good**

```yaml
- alert: TargetDown
  expr: up{job="api-server", cluster="prod"} == 0
  for: 5m
```

## Configuration

```yaml
selector_policy:
  require_one_of:
    - job
    - cluster
    - namespace
    - service
```

## Suppression

```yaml
# par disable broad-selector
- alert: GlobalScrapeFailure
  expr: up == 0
  for: 1m
```
