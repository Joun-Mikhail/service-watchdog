# Runbook: High latency

**Alert:** `[DEGRADED] <service> - LATENCY`  
**Log:** `category=LATENCY latency_ms=<ms> detail="<ms> exceeds limit of <limit>ms"`

## What it means

The service works but answered slower than its `max_latency_ms` threshold. Users notice slowness,
timeouts in clients, and abandoned requests. Latency problems often turn into outages if ignored.

## Diagnose

1. Split the request time into phases to see *where* the time goes:

   ```bash
   curl -o /dev/null -s -w 'dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' https://shop.example.com/
   ```

   | Slow phase | Points to |
   |------------|-----------|
   | `dns` | Resolver problems |
   | `connect` | Network distance, packet loss, overloaded load balancer |
   | `tls` | Handshake cost, OCSP/CRL lookups |
   | `ttfb` (time to first byte) | The application or its dependencies — most common |

2. Check how widespread and how long: `python report.py --hours 24` shows average and p95 per service.

3. On the server, check resource saturation:

   ```bash
   uptime; top -o %CPU; free -m; df -h; iostat -xz 1 5
   ```
   ```powershell
   Get-Counter '\Processor(_Total)\% Processor Time','\Memory\Available MBytes' -SampleInterval 2 -MaxSamples 5
   ```

4. Check dependencies: slow database queries, cache hit rate, third-party API response times.

## Common causes and fixes

| Cause | Fix |
|-------|-----|
| CPU or memory saturation | Scale up/out; find the process consuming resources |
| Slow database queries | Check slow query log, missing indexes, lock contention |
| Traffic spike | Scale out; enable caching / rate limiting |
| Disk full or slow I/O | Free space, rotate logs, move to faster storage |
| Slow third-party dependency | Add timeouts and fallbacks; contact the vendor |

## Escalate when

p95 latency keeps rising across several checks, or `LATENCY` turns into `HTTP` timeouts.

## Verify recovery

Latency returns below the threshold for several consecutive checks; the next check logs `status=UP`.
