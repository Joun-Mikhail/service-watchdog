import smtplib
from email.mime.text import MIMEText
from datetime import datetime


def send_down_alert(smtp_server, smtp_port, sender, password, recipient, url, status_code, error=None):
    """Send an email alert when a monitored URL goes down.

    Args:
        smtp_server: SMTP server hostname.
        smtp_port: SMTP server port.
        sender: Sender email address.
        password: Sender email password or app password.
        recipient: Recipient email address.
        url: The URL that is down.
        status_code: HTTP status code received (0 if unreachable).
        error: Optional error message from the request.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"[ALERT] Service Down: {url}"

    body = f"""Service Watchdog Alert

URL: {url}
Status: DOWN
Status Code: {status_code}
Time: {timestamp}
"""
    if error:
        body += f"Error: {error}\n"

    body += "\nThis is an automated alert from Service Watchdog."

    _send_email(smtp_server, smtp_port, sender, password, recipient, subject, body)


def send_recovery_alert(smtp_server, smtp_port, sender, password, recipient, url, downtime_seconds):
    """Send an email alert when a monitored URL recovers.

    Args:
        smtp_server: SMTP server hostname.
        smtp_port: SMTP server port.
        sender: Sender email address.
        password: Sender email password or app password.
        recipient: Recipient email address.
        url: The URL that recovered.
        downtime_seconds: How long the service was down in seconds.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"[RECOVERY] Service Back Up: {url}"

    downtime_str = _format_downtime(downtime_seconds)

    body = f"""Service Watchdog Recovery Notice

URL: {url}
Status: UP (Recovered)
Time: {timestamp}
Downtime Duration: {downtime_str}

This is an automated alert from Service Watchdog."""

    _send_email(smtp_server, smtp_port, sender, password, recipient, subject, body)


def _format_downtime(seconds):
    """Format a duration in seconds into a human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        A string like '2h 15m 30s' or '45s'.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)


def _send_email(smtp_server, smtp_port, sender, password, recipient, subject, body):
    """Send an email using SMTP with TLS.

    Args:
        smtp_server: SMTP server hostname.
        smtp_port: SMTP server port.
        sender: Sender email address.
        password: Sender email password or app password.
        recipient: Recipient email address.
        subject: Email subject line.
        body: Email body text.
    """
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
