import os
import time

import yaml
from dotenv import load_dotenv

from monitor import check_url
from alerter import send_down_alert, send_recovery_alert
from logger import setup_logger


def load_config(path="config.yaml"):
    """Load and return the watchdog configuration from a YAML file.

    Args:
        path: Path to the YAML config file.

    Returns:
        A dict containing the parsed configuration.
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_email_settings(config):
    """Build email settings dict from config and environment variables.

    Args:
        config: The parsed config dict from config.yaml.

    Returns:
        A dict with smtp_server, smtp_port, sender, password, and recipient.
    """
    return {
        "smtp_server": config["email"]["smtp_server"],
        "smtp_port": config["email"]["smtp_port"],
        "sender": os.getenv("SENDER_EMAIL"),
        "password": os.getenv("SENDER_PASSWORD"),
        "recipient": os.getenv("RECIPIENT_EMAIL"),
    }


def run():
    """Main loop that monitors URLs and sends alerts on status changes.

    Loads configuration, checks each URL at the configured interval,
    logs results, and sends email alerts when services go down or recover.
    """
    load_dotenv()
    config = load_config()
    logger = setup_logger()
    email_settings = get_email_settings(config)

    urls = config["urls"]
    interval = config["check_interval"] * 60
    timeout = config.get("timeout", 10)

    down_since = {}

    logger.info("Service Watchdog started. Monitoring %d URLs every %d minutes.",
                len(urls), config["check_interval"])

    while True:
        for url in urls:
            result = check_url(url, timeout=timeout)

            if result["is_up"]:
                logger.info("URL: %s | Status: %d | Response Time: %.2f ms",
                            result["url"], result["status_code"], result["response_time_ms"])

                if url in down_since:
                    downtime = time.time() - down_since.pop(url)
                    logger.info("URL: %s | RECOVERED after %.0f seconds", url, downtime)
                    try:
                        send_recovery_alert(**email_settings, url=url, downtime_seconds=downtime)
                        logger.info("Recovery email sent for %s", url)
                    except Exception as e:
                        logger.error("Failed to send recovery email for %s: %s", url, e)
            else:
                error_msg = result.get("error", "")
                logger.warning("URL: %s | Status: %d | DOWN | Error: %s",
                               result["url"], result["status_code"], error_msg)

                if url not in down_since:
                    down_since[url] = time.time()
                    try:
                        send_down_alert(**email_settings, url=url,
                                        status_code=result["status_code"], error=error_msg)
                        logger.info("Down alert email sent for %s", url)
                    except Exception as e:
                        logger.error("Failed to send down alert email for %s: %s", url, e)

        time.sleep(interval)


if __name__ == "__main__":
    run()
