# Postmortem (example): Admin portal unavailable after certificate change

> **Training example.** This is a worked example based on the failure modes in the
> [demo lab](../demo/lab.py), written to show how the watchdog's alerts feed an incident review.
> It does not describe a real incident.

| | |
|---|---|
| **Date** | 2026-11-23 |
| **Duration** | 09:12 – 09:41 UTC (29 minutes) |
| **Severity** | SEV2 — internal admin tool unavailable, customer-facing services unaffected |
| **Services affected** | Admin portal |
| **Detected by** | service-watchdog `[DOWN] Admin portal - TLS failure` |

## Summary

A routine web server configuration change replaced the admin portal's certificate with the server's
default self-signed certificate. Browsers blocked access with a security warning for 29 minutes until
the correct certificate chain was restored.

## Impact

- Support staff could not open the admin portal to process refunds; 14 refund tickets were delayed.
- No customer-facing service was affected.

## Timeline (UTC)

| Time | Event |
|------|-------|
| 09:08 | Web server configuration updated to add a new virtual host |
| 09:12 | First check fails: `category=TLS detail="certificate verification failed: self-signed certificate"` |
| 09:17 | Second consecutive failure → `[DOWN] Admin portal - TLS failure` alert emailed and sent to SNS |
| 09:19 | On-call engineer acknowledges, opens the linked [TLS runbook](runbooks/tls-certificate.md) |
| 09:24 | `openssl s_client` shows `issuer=CN=localhost` — the default certificate, not the CA-issued one |
| 09:33 | Virtual host found pointing to the default certificate path; corrected to `fullchain.pem` |
| 09:36 | Config tested (`nginx -t`) and reloaded |
| 09:41 | `[RECOVERED] Admin portal - back up after 29m 0s` |

## Root cause

The new virtual host was copied from a template that referenced the default certificate. The
server picked it for the admin portal's hostname because the new block was listed first and had a
matching `server_name` wildcard.

1. Why was the portal unavailable? Browsers rejected the self-signed certificate.
2. Why was a self-signed certificate served? A new virtual host block matched the hostname first.
3. Why did it reference the default certificate? It was copied from a template with placeholder paths.
4. Why was it not caught before reload? `nginx -t` checks syntax, not which certificate is served.

## What went well

- The watchdog alert named the failing layer (TLS), so diagnosis started in the right place.
- The runbook's `openssl s_client` command identified the wrong issuer within five minutes.

## What went poorly

- 9 minutes passed between the change and the alert (failure threshold of 2 × 5-minute interval).
- The template's placeholder paths pointed to a real, working certificate instead of failing loudly.

## Action items

| Action | Type | Owner | Due |
|--------|------|-------|-----|
| Replace template certificate paths with obviously invalid placeholders so a missed edit fails `nginx -t` | Prevent | Web team | 2026-11-30 |
| Add a post-change step: `openssl s_client` issuer check for every hostname on the server | Prevent | Web team | 2026-11-30 |
| Lower the admin portal's check interval to 1 minute | Detect | Ops | 2026-11-24 |
