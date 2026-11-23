# Runbook: TLS / certificate problems

**Alerts:** `[DOWN] <service> - TLS failure`, `[DEGRADED] <service> - TLS_EXPIRING`  
**Log:** `category=TLS detail="certificate verification failed: ..."` or `category=TLS_EXPIRING tls_days=N`

## What it means

- `TLS` — the TCP connection worked but the TLS handshake failed or the certificate was rejected.
  Browsers show a full-page security warning; most users cannot continue.
- `TLS_EXPIRING` — the certificate is still valid but expires within `tls_expiry_warning_days`.
  Nothing is broken yet: this is the time to fix it calmly.

## Diagnose

1. See exactly what the server presents:

   ```bash
   openssl s_client -connect shop.example.com:443 -servername shop.example.com </dev/null 2>/dev/null \
     | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
   ```
   ```powershell
   $tcp = [Net.Sockets.TcpClient]::new('shop.example.com', 443)
   $ssl = [Net.Security.SslStream]::new($tcp.GetStream(), $false, { $true })
   $ssl.AuthenticateAsClient('shop.example.com')
   $ssl.RemoteCertificate | Format-List Subject, Issuer, NotBefore, NotAfter
   ```

2. Match the `verification failed` reason to a cause:

| Reason in `detail` | Cause | Fix |
|--------------------|-------|-----|
| `certificate has expired` | Renewal failed or was never automated | Renew now; then fix automation (certbot timer, ACM, cert-manager) |
| `self-signed certificate` | Default / test certificate in production | Install a certificate from a trusted CA |
| `unable to get local issuer certificate` | Intermediate certificate missing from the chain | Serve the full chain (`fullchain.pem`, not `cert.pem`) |
| `Hostname mismatch` | Certificate does not cover this name | Reissue including the name in SubjectAltName |
| Handshake failure, no certificate | Wrong port, protocol/cipher mismatch, SNI not configured | Check the listener config and `-servername` result |

3. For `TLS_EXPIRING`, check why automatic renewal has not happened yet:

   ```bash
   sudo certbot renew --dry-run
   systemctl list-timers | grep certbot
   ```

## Escalate when

- The certificate is managed by another team or a vendor and expires in under 72 hours.
- A private key may be compromised — revoke and reissue, do not just renew.

## Verify recovery

`openssl s_client ... | openssl x509 -noout -dates` shows the new `notAfter`, the browser shows no
warning, and the watchdog reports `tls_days` with the new value.
