import pytest

from app.platform.config import (
    LOCAL_DATABASE_URL,
    LOCAL_JWT_SECRET,
    ConfigError,
    Settings,
    load_settings,
)

FLAGS = [
    "FEATURE_STUDENT_CHOICE",
    "FEATURE_CROSS_INSTITUTION_STATS",
    "FEATURE_RERUN",
    "FEATURE_INFO_VISIBILITY",
    "FEATURE_LECTURER_TEST_GAME",
    "FEATURE_GAME_DATA_EXPORT",
    "FEATURE_CAPACITY",
]


# A full, valid production set (AD-17, Story 3.14). No value here is a real secret.
PRODUCTION_ENV = {
    "APP_ENV": "production",
    "DATABASE_URL": "postgresql://u:p@db.example:5432/prod?sslmode=require",
    "JWT_SECRET": "test-only-Vq3xT9mK2pL7wR4zN8bY6cH1dF5gJ0sA",
    "RESEND_API_KEY": "test-only-resend-key",
    # `whsec_` and the base64 of "test-only-webhook-key".
    "RESEND_WEBHOOK_SECRET": "whsec_dGVzdC1vbmx5LXdlYmhvb2sta2V5",
    "SUPABASE_URL": "https://test-only.supabase.example",
    "SUPABASE_SERVICE_ROLE_KEY": "test-only-service-role-key",
    "EMAIL_FROM": "ØL-spillet <noreply@olspillet.example>",
    "PUBLIC_BASE_URL": "https://olspillet.example",
    "BOOTSTRAP_ADMIN_EMAILS": "kari.admin@olspillet.example",
    "BCRYPT_ROUNDS": "12",
}
REQUIRED = [
    "DATABASE_URL",
    "JWT_SECRET",
    "BOOTSTRAP_ADMIN_EMAILS",
    "EMAIL_FROM",
    "PUBLIC_BASE_URL",
    "RESEND_API_KEY",
    "RESEND_WEBHOOK_SECRET",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
]
"""The variables production cannot start without; BCRYPT_ROUNDS has a safe default (12)."""


@pytest.fixture
def clean_env(monkeypatch):
    for name in ["DB_POOL_SIZE", "LOG_LEVEL", "TRUSTED_PROXY_CIDRS", *PRODUCTION_ENV, *FLAGS]:
        monkeypatch.delenv(name, raising=False)
    for name in Settings.model_fields:
        if "_rate_limit_" in name:
            monkeypatch.delenv(name.upper(), raising=False)
    return monkeypatch


def production_env(monkeypatch) -> None:
    for name, value in PRODUCTION_ENV.items():
        monkeypatch.setenv(name, value)


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


def test_production_starts_with_a_full_valid_set(clean_env):
    production_env(clean_env)
    assert load_settings().app_env == "production"


@pytest.mark.parametrize("name", REQUIRED)
def test_production_refuses_without_each_required_variable(clean_env, name):
    production_env(clean_env)
    clean_env.delenv(name)
    with pytest.raises(ConfigError, match=name):
        load_settings()


@pytest.mark.parametrize(
    "name,value",
    [
        ("JWT_SECRET", LOCAL_JWT_SECRET),
        ("JWT_SECRET", "a" * 40),
        ("JWT_SECRET", "Short-but-varied-1234"),
        ("DATABASE_URL", "postgresql://u:p@db.example:5432/prod"),
        ("DATABASE_URL", "postgresql://u:p@db.example:5432/prod?sslmode=prefer"),
        ("DATABASE_URL", "postgresql://u:p@db.example:5432/prod?sslmode=disable"),
        ("PASSWORD_RESET_RATE_LIMIT_PER_IP", "10000"),
        ("LOGIN_RATE_LIMIT_PER_ACCOUNT", "51"),
        ("ACCESS_REQUEST_RATE_LIMIT_PER_IP", "10000"),
        ("BCRYPT_ROUNDS", "4"),
        ("BOOTSTRAP_ADMIN_EMAILS", "ola"),
        ("BOOTSTRAP_ADMIN_EMAILS", "kari@usn.no, ola@usn"),
        ("BOOTSTRAP_ADMIN_EMAILS", " , "),
        ("EMAIL_FROM", "ØL-spillet <noreply@olspillet.local>"),
        ("PUBLIC_BASE_URL", "http://127.0.0.1:8080"),
        ("PUBLIC_BASE_URL", "http://olspillet.example"),
        ("PUBLIC_BASE_URL", "https://"),
        ("EMAIL_FROM", "noreply"),
        ("EMAIL_FROM", "ØL-spillet <noreply@localhost>"),
        ("TRUSTED_PROXY_CIDRS", ","),
        ("RESEND_API_KEY", "  "),
        ("RESEND_WEBHOOK_SECRET", "whsec_bG9jYWwtb25seS13ZWJob29rLXNlY3JldC1ub3QtZm9yLXByb2Q="),
        ("RESEND_WEBHOOK_SECRET", "not-a-whsec-secret"),
        ("RESEND_WEBHOOK_SECRET", "whsec_"),
        ("RESEND_WEBHOOK_SECRET", "whsec_%%%"),
        ("TRUSTED_PROXY_CIDRS", "0.0.0.0/0"),
        ("TRUSTED_PROXY_CIDRS", "10.0.0.0/8,::/0"),
    ],
)
def test_production_refuses_an_unsafe_value(clean_env, name, value):
    production_env(clean_env)
    clean_env.setenv(name, value)
    with pytest.raises(ConfigError) as exc:
        load_settings()
    message = str(exc.value)
    assert message.endswith(name) or f"{name}," in message
    assert len(value.strip()) < 2 or value not in message


@pytest.mark.parametrize(
    "name,value",
    [
        ("DATABASE_URL", "postgresql://u:p@db.example:5432/prod?sslmode=verify-full"),
        ("LOGIN_RATE_LIMIT_PER_IP", "3000"),
        ("BCRYPT_ROUNDS", "13"),
        ("BOOTSTRAP_ADMIN_EMAILS", "kari@usn.no, ,ola@usn.no"),
    ],
)
def test_production_accepts_a_tuned_safe_value(clean_env, name, value):
    production_env(clean_env)
    clean_env.setenv(name, value)
    assert load_settings().app_env == "production"


def test_the_message_names_every_bad_variable_and_no_value(clean_env):
    clean_env.setenv("APP_ENV", "production")
    clean_env.setenv("JWT_SECRET", "tiny")
    with pytest.raises(ConfigError) as exc:
        load_settings()
    message = str(exc.value)
    for name in REQUIRED:
        assert name in message
    assert "tiny" not in message


def test_a_malformed_trusted_proxy_list_refuses_anywhere(clean_env):
    clean_env.setenv("TRUSTED_PROXY_CIDRS", "10.0.0.0/8,proxy")
    with pytest.raises(ConfigError, match="TRUSTED_PROXY_CIDRS"):
        load_settings()


def test_the_local_raised_limits_and_cost_are_fine_outside_production(clean_env):
    clean_env.setenv("PASSWORD_RESET_RATE_LIMIT_PER_IP", "10000")
    clean_env.setenv("BCRYPT_ROUNDS", "4")
    assert load_settings().password_reset_rate_limit_per_ip == 10000


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
