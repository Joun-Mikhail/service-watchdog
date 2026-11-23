# Runbook: HTTP errors and wrong content

**Alerts:** `[DOWN] <service> - HTTP failure`, `[DOWN] <service> - CONTENT failure`  
**Log:** `category=HTTP code=<status>` or `detail="no HTTP response within Ns"`;
`category=CONTENT detail="keyword '...' not found in response body"`

## What it means

The network path and TLS are fine; the application itself answered badly:

- `HTTP` — unexpected status code, or the server accepted the connection but never responded.
- `CONTENT` — status looked fine (often `200`), but the page is not the real page: maintenance
  screen, error page rendered with `200`, empty response, or a login wall.

## Diagnose

1. Reproduce and read the full response:

   ```bash
   curl -sS -o /dev/null -w '%{http_code} %{time_total}s\n' https://shop.example.com/health
   curl -sSv https://shop.example.com/health
   ```
   ```powershell
   # PowerShell 7+
   Invoke-WebRequest https://shop.example.com/health -SkipHttpErrorCheck | Select-Object StatusCode, Content
   ```

2. Use the status code to narrow it down:

| Status | Usually means | Look at |
|--------|---------------|---------|
| `500` | Unhandled application error | Application logs / stack traces around the alert time |
| `502` / `504` | Proxy or load balancer cannot get an answer from the backend | Backend process health, proxy upstream config, timeouts |
| `503` | Overloaded, in maintenance, or no healthy backends | Load balancer target health, autoscaling, maintenance flags |
| `401` / `403` | Auth or WAF blocking the check | Recent auth / WAF / IP allow-list changes |
| `404` | Wrong path, or a deploy removed the route | Recent deploys, routing / ingress config |
| No response | App hung (deadlock, exhausted worker pool) | Thread dumps, worker counts, CPU and memory |

3. Correlate with changes: what was deployed or reconfigured shortly before the first failure?

4. On the server:

   ```bash
   journalctl -u <app> --since "30 min ago" | grep -iE 'error|exception|traceback'
   sudo tail -n 100 /var/log/nginx/error.log
   ```
   ```powershell
   Get-WinEvent -LogName Application -MaxEvents 50 | Where-Object LevelDisplayName -eq 'Error'
   ```

## Common fixes

- Bad deploy → roll back first, investigate second.
- Dependency down (database, cache, external API) → check its health; the app is the messenger.
- Resource exhaustion → restart to restore service, then capture evidence (memory, connections) for
  the root cause.
- Maintenance page left on → disable the maintenance flag after confirming the work is finished.

## Escalate when

The cause is inside application code or a dependency owned by another team — hand over with the
status code, first-failure timestamp, affected endpoints and any log excerpts.

## Verify recovery

The expected status and keyword are returned, and the watchdog sends `[RECOVERED]` with the total downtime.
