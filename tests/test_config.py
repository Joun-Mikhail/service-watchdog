import pytest

from config import ConfigError, load_config


def write(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return str(path)


def test_loads_mapping_and_plain_url_targets(tmp_path):
    path = write(
        tmp_path,
        """
targets:
  - name: API
    url: https://api.example.com/health
    keyword: ok
    max_latency_ms: 500
  - https://example.com
check_interval: 1
""",
    )
    settings = load_config(path)

    assert [t.name for t in settings.targets] == ["API", "https://example.com"]
    assert settings.targets[0].keyword == "ok"
    assert settings.targets[0].max_latency_ms == 500
    assert settings.targets[1].expected_status == 200
    assert settings.check_interval == 1
    assert settings.failure_threshold == 2


def test_missing_file_raises():
    with pytest.raises(ConfigError, match="not found"):
        load_config("/nonexistent/config.yaml")


@pytest.mark.parametrize(
    "text, message",
    [
        ("targets: []", "non-empty list"),
        ("targets:\n  - ftp://example.com", "must start with http"),
        ("targets:\n  - url: https://example.com\n    expected_status: 999", "HTTP status code"),
        ("targets:\n  - https://example.com\ntimeout: -1", "positive number"),
        ("targets: [unclosed", "could not parse"),
    ],
)
def test_invalid_config_raises(tmp_path, text, message):
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, text))
