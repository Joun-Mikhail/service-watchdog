# Runbook: Watchdog silent (AWS)

**Alert:** CloudWatch alarm `service-watchdog-silent` in `ALARM` state (sent through SNS)

## What it means

No check results reached CloudWatch Logs for three check intervals. The monitored services may be
fine — but nobody would be told if they were not. Treat this as urgent: **monitoring is blind.**

## Diagnose

1. Connect to the instance (no SSH needed):

   ```bash
   aws ssm start-session --target <instance-id>
   ```

   If the instance is not reachable, check its state and status checks in the EC2 console — the
   `instance-recover` alarm may already be moving it to new hardware.

2. Is the service running?

   ```bash
   sudo systemctl status service-watchdog
   sudo journalctl -u service-watchdog -n 50 --no-pager
   ```

   - `failed` with exit code `2` → invalid `config.yaml`; the unit deliberately does not restart-loop.
     Fix the config, then `sudo systemctl restart service-watchdog`.
   - `active (running)` → the watchdog is fine; the problem is log shipping (next step).

3. Is the CloudWatch agent shipping logs?

   ```bash
   sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a status
   sudo tail -n 50 /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log
   sudo tail -n 5 /opt/service-watchdog/logs/watchdog.log
   ```

   `AccessDenied` in the agent log means the instance role or its policy changed.

4. Disk full stops logging: `df -h /`.

## Verify recovery

New lines appear in `aws logs tail /service-watchdog/watchdog --follow`, and the alarm returns to `OK`
(an `OK` notification is sent through SNS).
