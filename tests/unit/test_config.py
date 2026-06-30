from app.config.settings import get_settings, load_runtime_config


def test_settings_load_defaults():
    settings = get_settings()
    assert settings.temporal_task_queue == "head-hunter"


def test_runtime_config_loads_example_yaml():
    config = load_runtime_config()
    assert config.scan_policy.total_scan_blocks == 7
    assert config.seed_policy.automatic_activation is True
