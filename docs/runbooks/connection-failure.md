# Runbook: TCP connection failure

**Alert:** `[DOWN] <service> - TCP failure`  
**Log:** `category=TCP detail="connection to <ip>:<port> refused | timed out | cannot reach"`

## What it means

DNS worked, but a TCP connection to the resolved IP and port could not be opened. The wording of
`detail` tells you which kind of failure it was:

| Detail | Meaning |
|--------|---------|
| `refused` | The host answered, but nothing is listening on that port (service stopped or crashed) |
| `timed out` | Packets were silently dropped — usually a firewall, security group, or the host is down |
| `cannot reach` / `no route to host` | Routing problem or host offline |

## Diagnose

1. Test the port from the watchdog host and from another network:

   ```bash
   nc -vz -w 5 203.0.113.25 443
   curl -v --connect-timeout 5 https://shop.example.com/
   ```
   ```powershell
   Test-NetConnection shop.example.com -Port 443
   ```

2. On the server, check whether the service is running and listening:

   ```bash
   systemctl status nginx
   sudo ss -tlnp | grep ':443'
   journalctl -u nginx --since "30 min ago"
   ```
   ```powershell
   Get-Service W3SVC
   Get-NetTCPConnection -LocalPort 443 -State Listen
   ```

3. If the port times out, follow the path: host firewall (`sudo iptables -L -n`, `ufw status`,
   `Get-NetFirewallRule`), cloud security group / network ACL, load balancer target health.

4. Check whether the host is up at all: cloud console instance state, `ping` (if ICMP is allowed),
   `traceroute` / `tracert`.

## Common causes and fixes

| Finding | Cause | Fix |
|---------|-------|-----|
| Refused, service stopped | Crash, OOM kill, failed deploy | Read service logs, `dmesg -T \| grep -i oom`; restart, then find the root cause |
| Refused, listening on `127.0.0.1` only | Bind address misconfigured | Bind to `0.0.0.0` / the correct interface |
| Timed out after a change | Firewall or security group rule removed | Restore the rule; review the change |
| Timed out, instance stopped | Host down or out of resources | Start / recover the instance; check status checks |
| Load balancer has no healthy targets | Health check failing on backends | Fix backends; check the target group health reason |

## Escalate when

- The host is unreachable and you have no console access.
- The network path crosses infrastructure you do not own (corporate firewall, ISP, cloud provider).

## Verify recovery

`Test-NetConnection` / `nc -vz` succeeds, the service answers HTTP, and the watchdog sends `[RECOVERED]`.
