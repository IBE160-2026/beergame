import pytest

from app.platform.config import LOCAL_DATABASE_URL, ConfigError, Settings, load_settings

FLAGS = [
    "FEATURE_STUDENT_CHOICE",
    "FEATURE_CROSS_INSTITUTION_STATS",
    "FEATURE_RERUN",
    "FEATURE_INFO_VISIBILITY",
    "FEATURE_LECTURER_TEST_GAME",
    "FEATURE_GAME_DATA_EXPORT",
    "FEATURE_CAPACITY",
]


@pytest.fixture
def clean_env(monkeypatch):
    for name in ["APP_ENV", "DATABASE_URL", "DB_POOL_SIZE", "LOG_LEVEL", *FLAGS]:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_local_defaults_with_no_env(clean_env):
    settings = load_settings()
    assert settings.app_env == "local"
    assert settings.database_url == LOCAL_DATABASE_URL
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.db_pool_size == 10
    assert settings.log_level == "info"


def test_exactly_the_seven_cut_list_flags_default_true(clean_env):
    settings = load_settings()
    flags = {k for k in Settings.model_fields if k.startswith("feature_")}
    assert flags == {f.lower() for f in FLAGS}
    assert all(getattr(settings, f) is True for f in flags)


def test_flag_can_be_turned_off(clean_env):
    clean_env.setenv("FEATURE_CAPACITY", "false")
    assert load_settings().feature_capacity is False


def test_unknown_app_env_refuses(clean_env):
    clean_env.setenv("APP_ENV", "staging")
    with pytest.raises(ConfigError, match="APP_ENV"):
        load_settings()


def test_production_refuses_without_database_url(clean_env):
    clean_env.setenv("APP_ENV", "production")
    with pytest.raises(SystemExit, match="DATABASE_URL"):
        load_settings()


def test_production_refuses_with_default_database_url(clean_env):
    clean_env.setenv("APP_ENV", "production")
    clean_env.setenv("DATABASE_URL", LOCAL_DATABASE_URL)
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        load_settings()


def test_production_starts_with_real_database_url(clean_env):
    clean_env.setenv("APP_ENV", "production")
    clean_env.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db.example:5432/prod")
    assert load_settings().app_env == "production"


def test_refusal_message_does_not_echo_the_secret(clean_env):
    clean_env.setenv("APP_ENV", "production")
    clean_env.setenv("DATABASE_URL", LOCAL_DATABASE_URL)
    with pytest.raises(ConfigError) as exc:
        load_settings()
    assert "olspillet:olspillet" not in str(exc.value)


@pytest.mark.parametrize("name,value", [("LOG_LEVEL", "verbose"), ("DB_POOL_SIZE", "0")])
def test_invalid_values_refuse_with_the_variable_name(clean_env, name, value):
    clean_env.setenv(name, value)
    with pytest.raises(ConfigError, match=name):
        load_settings()


def test_plain_postgresql_url_uses_psycopg(clean_env):
    clean_env.setenv("DATABASE_URL", "postgresql://u:p@db.example:5432/prod")
    assert load_settings().database_url == "postgresql+psycopg://u:p@db.example:5432/prod"
