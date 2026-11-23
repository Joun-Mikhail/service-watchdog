import watchdog


def test_invalid_config_returns_exit_code_2(tmp_path):
    bad = tmp_path / "config.yaml"
    bad.write_text("targets: []")
    assert watchdog.main(["--config", str(bad), "--once", "--dry-run"]) == 2


def test_once_returns_1_when_a_target_is_down(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("targets:\n  - http://127.0.0.1:9\n")
    assert watchdog.main(["--config", str(cfg), "--once", "--dry-run"]) == 1
