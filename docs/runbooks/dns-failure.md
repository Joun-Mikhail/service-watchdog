# Runbook: DNS failure

**Alert:** `[DOWN] <service> - DNS failure`  
**Log:** `category=DNS detail="could not resolve <host>: ..."`

## What it means

The watchdog could not turn the hostname into an IP address, so no connection was attempted.

## Impact

Usually total: every user whose resolver gives the same answer cannot reach the service. If the
problem is only the watchdog host's resolver, users may be unaffected.

## Diagnose

1. Resolve the name from the watchdog host and from another network:

   ```bash
   dig +short shop.example.com          # Linux / macOS
   nslookup shop.example.com            # any OS
   ```
   ```powershell
   Resolve-DnsName shop.example.com     # Windows
   ```

2. Query a public resolver and the domain's authoritative servers directly, to separate a local
   resolver problem from a problem with the zone:

   ```bash
   dig @1.1.1.1 shop.example.com
   dig NS example.com +short
   dig @<authoritative-ns> shop.example.com
   ```
   ```powershell
   Resolve-DnsName shop.example.com -Server 1.1.1.1
   ```

3. Read the response code: `NXDOMAIN` = the name does not exist; `SERVFAIL` = resolution failed
   (often DNSSEC or unreachable name servers); timeout = resolver unreachable.

4. Check domain registration and expiry: `whois example.com | grep -i expir`.

## Common causes and fixes

| Finding | Cause | Fix |
|---------|-------|-----|
| `NXDOMAIN` everywhere | Record deleted or renamed | Restore the record in the DNS provider; check recent DNS changes |
| `NXDOMAIN`, domain expired | Registration lapsed | Renew at the registrar; enable auto-renew |
| `SERVFAIL` | DNSSEC misconfiguration or name servers down | `dig +dnssec`; check the DNS provider's status page |
| Works on `1.1.1.1`, fails locally | Local resolver issue | Check `/etc/resolv.conf` / `Get-DnsClientServerAddress`; flush cache (`resolvectl flush-caches`, `ipconfig /flushdns`) |
| Old IP returned | Stale cache after a change | Wait for TTL to expire; lower TTL before future migrations |

## Escalate when

- The authoritative name servers do not answer — escalate to whoever owns the DNS provider account.
- The domain has expired and you cannot access the registrar account.

## Verify recovery

`dig +short <host>` returns the expected IP from several resolvers, and the watchdog sends a
`[RECOVERED]` alert.
