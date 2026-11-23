# Troubleshooting toolkit

The commands below follow the same order as the watchdog's checks: **DNS → TCP → TLS → HTTP**.
Work down the layers; the first one that fails is where the problem is.

| Layer | Linux / macOS | Windows (PowerShell) |
|-------|---------------|----------------------|
| DNS | `dig +short host` · `dig @1.1.1.1 host` · `nslookup host` | `Resolve-DnsName host` · `Resolve-DnsName host -Server 1.1.1.1` |
| Reachability | `ping -c 4 host` · `traceroute host` · `mtr host` | `Test-Connection host` · `tracert host` |
| TCP port | `nc -vz -w 5 host 443` | `Test-NetConnection host -Port 443` |
| TLS | `openssl s_client -connect host:443 -servername host` | see [tls-certificate runbook](runbooks/tls-certificate.md) |
| HTTP | `curl -sSv https://host/path` | `Invoke-WebRequest https://host/path` |
| Timing | `curl -o /dev/null -s -w '%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer}\n' URL` | `Measure-Command { Invoke-WebRequest URL }` |

## On the server

| Question | Linux | Windows |
|----------|-------|---------|
| Is the service running? | `systemctl status <svc>` | `Get-Service <svc>` |
| What is listening? | `sudo ss -tlnp` | `Get-NetTCPConnection -State Listen` |
| Recent service logs | `journalctl -u <svc> --since "1 hour ago"` | `Get-WinEvent -LogName System -MaxEvents 50` |
| CPU / memory | `top` · `free -m` · `vmstat 1 5` | `Get-Counter '\Processor(_Total)\% Processor Time'` |
| Disk space | `df -h` · `du -sh /var/log/*` | `Get-PSDrive -PSProvider FileSystem` |
| Killed by out-of-memory? | `dmesg -T \| grep -i oom` | Event Viewer → System → Resource-Exhaustion-Detector |
| Firewall rules | `sudo ufw status` · `sudo iptables -L -n` | `Get-NetFirewallRule -Enabled True` |
| DNS settings | `resolvectl status` · `cat /etc/resolv.conf` | `Get-DnsClientServerAddress` |
| Flush DNS cache | `sudo resolvectl flush-caches` | `Clear-DnsClientCache` |

## service-watchdog itself

| Question | Command |
|----------|---------|
| Run every check once, no alerts | `python watchdog.py --once --dry-run` |
| Validate the config | `python watchdog.py --once --dry-run --config config.yaml; echo $?` (exit code `2` = invalid) |
| Recent failures | `grep -E 'status=(DOWN\|DEGRADED)' logs/watchdog.log \| tail` |
| Failures by category | `grep -o 'category=[A-Z_]*' logs/watchdog.log \| sort \| uniq -c` |
| Uptime summary | `python report.py --hours 24` |
| Service status (Linux) | `systemctl status service-watchdog` · `journalctl -u service-watchdog -f` |
| Task status (Windows) | `Get-ScheduledTask service-watchdog \| Get-ScheduledTaskInfo` |

## Practising

`python demo/lab.py` starts local services that fail in every category the watchdog detects
(HTTP 503, slow responses, maintenance page, flaky service, self-signed certificate). Run the
watchdog against `demo/config.yaml` and work through each alert with the runbooks.
