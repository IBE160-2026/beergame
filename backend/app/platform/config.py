"""One settings class for every process (AD-17).

Locally, with no environment at all, everything has a working default.
With APP_ENV=production the process refuses to start when a required
secret is missing or still has its built-in local default.
"""

from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = "postgresql+psycopg://olspillet:olspillet@localhost:5432/olspillet"
LOCAL_JWT_SECRET = "local-only-jwt-secret-not-for-production"

# Variables that must be set, and not to a built-in default, in production.
# Later epics add JWT_SECRET, RESEND_API_KEY and the storage keys here.
PRODUCTION_REQUIRED: dict[str, str] = {
    "database_url": LOCAL_DATABASE_URL,
}


class ConfigError(SystemExit):
    """Raised at settings load when the process must not start."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    app_env: Literal["local", "test", "ci", "production"] = "local"
    database_url: str = LOCAL_DATABASE_URL
    db_pool_size: int = Field(10, ge=1)
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"

    # PRD §8.1 cut-list flags only (AD-17).
    feature_student_choice: bool = True
    feature_cross_institution_stats: bool = True
    feature_rerun: bool = True
    feature_info_visibility: bool = True
    feature_lecturer_test_game: bool = True
    feature_game_data_export: bool = True
    feature_capacity: bool = True

    # AI budgets in USD (FR-69, AD-6). PLACEHOLDERS until the prototype sets them (issue #8):
    # the default cost limit of a new Class session, and the reserve kept for the Debrief and
    # the AI assessment when a budget is created without one.
    ai_default_session_budget_usd: Decimal = Field(Decimal("15.00"), ge=0, decimal_places=8)
    ai_budget_reserve_usd: Decimal = Field(Decimal("1.00"), ge=0, decimal_places=8)

    # Session and login (AD-11, Story 3.2). JWT_SECRET's production guard comes with Story 3.14.
    jwt_secret: str = LOCAL_JWT_SECRET
    session_max_age_hours: int = Field(168, ge=1)
    # bcrypt cost; the tests set the minimum, 4, so hashing stays cheap.
    bcrypt_rounds: int = Field(12, ge=4, le=16)
    # PLACEHOLDERS to be confirmed before the pilot: failed logins allowed per window. The IP
    # limit stays far above a class size, since a whole class can share one NAT address.
    login_rate_limit_per_ip: int = Field(300, ge=1)
    login_rate_limit_per_account: int = Field(5, ge=1)
    login_rate_limit_window_minutes: int = Field(15, ge=1)
    # Password reset (Story 3.6). PLACEHOLDERS: the link validity is the one hour the UX spine
    # assumes; the limits count requests per window, for every address, known or not.
    password_reset_valid_minutes: int = Field(60, ge=1)
    password_reset_rate_limit_per_ip: int = Field(50, ge=1)
    password_reset_rate_limit_per_account: int = Field(5, ge=1)
    password_reset_rate_limit_window_minutes: int = Field(60, ge=1)

    # Mail (AD-9, AD-17, Story 3.5). With no RESEND_API_KEY outside production every mail goes
    # to the `[email:mock]` sender; the compose file never passes a key.
    email_from: str = "ØL-spillet <noreply@olspillet.local>"
    public_base_url: str = "http://127.0.0.1:8080"
    resend_api_key: str = ""

    @field_validator("log_level", mode="before")
    @classmethod
    def _lower_level(cls, v: object) -> object:
        return v.lower() if isinstance(v, str) else v

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, v: str) -> str:
        # Hosted Postgres hands out postgresql:// URLs; we use psycopg 3 only.
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v

    def check_production(self) -> None:
        if self.app_env != "production":
            return
        bad = [
            name.upper()
            for name, default in PRODUCTION_REQUIRED.items()
            if not getattr(self, name) or getattr(self, name) == default
        ]
        if bad:
            raise ConfigError(
                "Refusing to start with APP_ENV=production: "
                f"missing or default value for {', '.join(bad)}"
            )


def load_settings() -> Settings:
    try:
        settings = Settings()
    except ValidationError as exc:
        fields = ", ".join(str(e["loc"][0]).upper() for e in exc.errors() if e["loc"])
        raise ConfigError(f"Invalid configuration: {fields or exc}") from None
    settings.check_production()
    return settings


@lru_cache
def get_settings() -> Settings:
    return load_settings()
