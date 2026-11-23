# Postmortem: <short title>

> Blameless format: describe what happened and why the system allowed it, not who to blame.

| | |
|---|---|
| **Date** | YYYY-MM-DD |
| **Duration** | HH:MM – HH:MM UTC (total downtime from the `[RECOVERED]` alert) |
| **Severity** | SEV1 (full outage) / SEV2 (major degradation) / SEV3 (minor) |
| **Services affected** | |
| **Detected by** | service-watchdog alert / customer report / other |
| **Author** | |

## Summary

Two or three sentences: what broke, who was affected, how it was fixed.

## Impact

- Users affected and how (could not log in, slow checkout, errors on page X)
- Requests / orders / tickets affected, if known
- SLA or SLO impact

## Timeline (UTC)

| Time | Event |
|------|-------|
| | Triggering change or first failure |
| | Alert received (`[DOWN] ... - <CATEGORY> failure`) |
| | Acknowledged by |
| | Diagnosis milestones |
| | Mitigation applied |
| | `[RECOVERED]` alert, service confirmed healthy |

## Root cause

What actually failed, and why. Use "5 whys" until you reach something you can change.

## What went well

## What went poorly

## Action items

| Action | Type (prevent / detect / mitigate) | Owner | Due |
|--------|-------------------------------------|-------|-----|
| | | | |
