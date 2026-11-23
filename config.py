"""Load and validate the watchdog configuration file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


class ConfigError(ValueError):
    """Raised when the configuration file is missing or invalid."""


@dataclass
class Target:
    """A single endpoint to monitor."""

    name: str
    url: str
    expected_status: int = 200
    keyword: Optional[str] = None
    max_latency_ms: Optional[float] = None


@dataclass
class Settings:
    """Validated runtime settings."""

    targets: List[Target] = field(default_factory=list)
    check_interval: float = 5
    timeout: float = 10
    failure_threshold: int = 2
    tls_expiry_warning_days: int = 14
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    history_file: str = "logs/history.csv"


def _positive_number(raw, key, default):
    """Return raw[key] as a positive number, or default when it is absent."""
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"'{key}' must be a positive number, got {value!r}")
    return value


def _parse_target(item, index):
    """Build a Target from a plain URL string or a mapping."""
    if isinstance(item, str):
        item = {"url": item}
    if not isinstance(item, dict):
        raise ConfigError(f"targets[{index}] must be a URL or a mapping")

    url = item.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ConfigError(f"targets[{index}].url must start with http:// or https://, got {url!r}")

    expected_status = item.get("expected_status", 200)
    if not isinstance(expected_status, int) or not 100 <= expected_status <= 599:
        raise ConfigError(f"targets[{index}].expected_status must be an HTTP status code")

    max_latency = item.get("max_latency_ms")
    if max_latency is not None:
        max_latency = _positive_number(item, "max_latency_ms", None)

    return Target(
        name=str(item.get("name") or url),
        url=url,
        expected_status=expected_status,
        keyword=item.get("keyword"),
        max_latency_ms=max_latency,
    )


def load_config(path="config.yaml"):
    """Read the YAML file at path and return validated Settings.

    Raises:
        ConfigError: if the file is missing, unparsable, or has invalid values.
    """
    if not os.path.exists(path):
        raise ConfigError(f"config file not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"could not parse {path}: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a YAML mapping at the top level")

    items = raw.get("targets")
    if not isinstance(items, list) or not items:
        raise ConfigError("'targets' must be a non-empty list")

    email = raw.get("email") or {}

    return Settings(
        targets=[_parse_target(item, i) for i, item in enumerate(items)],
        check_interval=_positive_number(raw, "check_interval", 5),
        timeout=_positive_number(raw, "timeout", 10),
        failure_threshold=int(_positive_number(raw, "failure_threshold", 2)),
        tls_expiry_warning_days=int(_positive_number(raw, "tls_expiry_warning_days", 14)),
        smtp_server=email.get("smtp_server", "smtp.gmail.com"),
        smtp_port=int(email.get("smtp_port", 587)),
        history_file=str(raw.get("history_file", "logs/history.csv")),
    )
