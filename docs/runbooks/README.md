# Runbooks

Every alert links to the runbook for its failure category. Each runbook follows the same structure:
**what it means → impact → diagnose → common causes and fixes → escalate → verify recovery**.

| Alert category | Runbook | First question to answer |
|----------------|---------|--------------------------|
| `DNS` | [dns-failure.md](dns-failure.md) | Does the name resolve from anywhere? |
| `TCP` | [connection-failure.md](connection-failure.md) | Is anything listening, and can packets reach it? |
| `TLS`, `TLS_EXPIRING` | [tls-certificate.md](tls-certificate.md) | What certificate is the server presenting? |
| `HTTP`, `CONTENT` | [http-errors.md](http-errors.md) | What status and body does the server return? |
| `LATENCY` | [high-latency.md](high-latency.md) | Where is the time spent? |
| Watchdog silent (AWS alarm) | [watchdog-silent.md](watchdog-silent.md) | Is the monitor itself running? |

## General first response

1. **Acknowledge** the alert so others know it is being handled.
2. **Confirm from a second location** — your laptop, a phone on mobile data, or an online checker.
   A failure seen only by the watchdog points to the watchdog host's network, not the service.
3. **Check scope** — one service or many? Several categories failing at once usually means a shared
   dependency (DNS provider, network, load balancer, cloud region).
4. **Check recent changes** — deployments, DNS edits, certificate renewals, firewall changes.
5. **Follow the category runbook**, and write down timestamps and findings as you go; they become the
   incident timeline ([postmortem template](../postmortem-template.md)).
