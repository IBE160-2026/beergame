"""One settings class for every process (AD-17).

Locally, with no environment at all, everything has a working default.
With APP_ENV=production the process refuses to start when a required
secret is missing or still has its built-in local default.
"""

import base64
import ipaddress
from dataclasses import dataclass
from decimal import Decimal
from email.utils import parseaddr
from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = "postgresql+psycopg://olspillet:olspillet@localhost:5432/olspillet"
LOCAL_JWT_SECRET = "local-only-jwt-secret-not-for-production"
LOCAL_EMAIL_FROM = "ØL-spillet <noreply@olspillet.local>"
LOCAL_PUBLIC_BASE_URL = "http://127.0.0.1:8080"
# The local signing secret of the mail provider's webhook (Story 4.6): Svix's `whsec_` and the
# base64 of a local-only key, so the tests and the dev bounce route can sign events. Refused in
# production.
LOCAL_RESEND_WEBHOOK_SECRET = "whsec_bG9jYWwtb25seS13ZWJob29rLXNlY3JldC1ub3QtZm9yLXByb2Q="
# The peers whose `X-Forwarded-For` the api believes: loopback, private networks, the shared
# address space Railway's network uses, and IPv6 unique-local (Railway's private network). The
# api is never public; the proxy in front of it decides the client address (Story 3.14).
LOCAL_TRUSTED_PROXY_CIDRS = (
    "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10,fc00::/7"
)

# Production guard (AD-17, NFR-7, Story 3.14). Each rule names one variable; the message lists
# the names of the variables that break a rule, never their values.
JWT_SECRET_MIN_LENGTH = 32
JWT_SECRET_MIN_DISTINCT = 8
BCRYPT_ROUNDS_MIN_PRODUCTION = 12
RATE_LIMIT_PRODUCTION_FACTOR = 10
"""A rate limit above this many times its built-in default is a local raised limit (the
compose file's) and refused in production."""
TLS_SSLMODES = frozenset({"require", "verify-ca", "verify-full"})
REQUIRED_SECRETS = ("resend_api_key", "supabase_url", "supabase_service_role_key")
"""Secrets with no default at all; the storage keys are used from `platform/storage` on."""


class ConfigError(SystemExit):
    """Raised at settings load when the process must not start."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    app_env: Literal["local", "test", "ci", "production"] = "local"
    database_url: str = LOCAL_DATABASE_URL
    db_pool_size: int = Field(10, ge=1)
    # The pool size of the Supabase session pooler, copied by hand from Supabase (Database ->
    # Connection pooling), since it cannot be read over the pooler (Story 15.9). Unset (empty)
    # means the pooler check reports "not checked", never "passed".
    db_pooler_size: int | None = Field(None, ge=1)
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
    # The daily AI spend above which every Admin is alerted once that day (Story 15.7, FR-69).
    # PLACEHOLDER until the prototype sets it (issue #8): about 50 Students at the USD 0.50 target
    # in one day. Empty (`AI_DAILY_ALERT_USD=`) means not set: no alert is sent.
    ai_daily_alert_usd: Decimal | None = Field(Decimal("25.00"), ge=0, decimal_places=8)

    # Session and login (AD-11, Story 3.2). Production refuses a missing, default or weak one.
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
    # Invitations to the Lecturer or Admin role (Story 3.7). PLACEHOLDER: the 14 days of the UX
    # spine («Invitasjonen er gyldig i 14 dager.»).
    role_invitation_valid_days: int = Field(14, ge=1)
    # Accepting an Invitation and asking for a new one (Story 3.8). PLACEHOLDERS: attempts per
    # window, per client address and per Invitation link.
    invitation_accept_rate_limit_per_ip: int = Field(50, ge=1)
    invitation_accept_rate_limit_per_invitation: int = Field(10, ge=1)
    invitation_renewal_rate_limit_per_ip: int = Field(20, ge=1)
    invitation_renewal_rate_limit_per_invitation: int = Field(3, ge=1)
    invitation_rate_limit_window_minutes: int = Field(60, ge=1)
    # The public «Be om lærertilgang» form (Story 3.13). PLACEHOLDER: requests per client address
    # and window.
    access_request_rate_limit_per_ip: int = Field(20, ge=1)
    access_request_rate_limit_window_minutes: int = Field(60, ge=1)
    # The first Admin (AD-17, Story 3.8): comma-separated addresses. With APP_ENV=production the
    # api mails each one an Admin Invitation at startup; a listed User gains Admin at first login.
    bootstrap_admin_emails: str = ""

    # Roster upload (Story 4.2, FR-7, NFR-3). PLACEHOLDERS that cover a Class of at least 400
    # Students with room to spare: the largest file the api reads, the most data rows it stages,
    # and how long a staged upload is kept before it is purged.
    roster_max_file_mb: int = Field(5, ge=1, le=50)
    roster_max_rows: int = Field(5000, ge=1)
    roster_staging_ttl_hours: int = Field(24, ge=1)
    # Manual registration (Story 4.8, FR-9). PLACEHOLDER: the whole days (Europe/Oslo) the
    # set-password link of a manually registered Student works.
    manual_registration_link_days: int = Field(14, ge=1, le=60)

    # The date plan of a Class session (Story 5.2, FR-18). PLACEHOLDER, unset until SM-11 is
    # known: the least playing time per Week, in minutes. While unset the Klasseøkt never warns
    # that the time between the Start date and the Play deadline is too short.
    min_play_minutes_per_week: int | None = Field(None, ge=1)
    # The required share of Weeks a new Class session starts with (Story 5.7, FR-17), a whole
    # percent. PLACEHOLDER from FR-17's assumption; Completion itself is Epic 13's.
    completion_default_share_percent: int = Field(80, ge=1, le=100)
    # The Group debrief (Story 9.11, FR-43). PLACEHOLDER: how long a shared step must have been
    # open before its opener may move every joined Student on, in minutes.
    debrief_move_on_wait_minutes: int = Field(5, ge=0)
    # Follow-up questions in the Debrief (Story 9.15, FR-45, AD-11). PLACEHOLDERS: questions per
    # account and per client address in a window, and how long one question's model call may
    # take before the Student is told no answer could be given.
    follow_up_rate_limit_per_account: int = Field(10, ge=1)
    # Per address high enough for a lecture hall behind one network address.
    follow_up_rate_limit_per_ip: int = Field(300, ge=1)
    follow_up_rate_limit_window_minutes: int = Field(10, ge=1)
    follow_up_deadline_seconds: int = Field(20, ge=1, le=120)
    # The Replay walkthrough (Story 10.7, FR-50, UX-DR64). PLACEHOLDER (under one minute): how
    # long after the Replay finished its page waits for the AI line before it shows the code's.
    replay_walkthrough_wait_seconds: int = Field(45, ge=1, le=600)
    # Messages from staff to Students (Story 7.9, FR-40). PLACEHOLDER: the most characters a
    # Message may hold; a longer one is refused with `message_too_long` and this limit.
    message_max_length: int = Field(2000, ge=1, le=20000)
    # The turn reminder (Story 8.13, FR-27). PLACEHOLDER from FR-27's assumption, to be confirmed
    # by the founder: how long, in minutes, a Class game has waited for a Student's Order before
    # a `turn_reminder` digest notice is queued.
    turn_reminder_delay_minutes: int = Field(120, ge=1, le=10080)
    # Story 8.14 (FR-38, NFR-3, spine Deferred): placeholder, an open input set after the
    # prototype: how long, in minutes, a Class game may stay `playing_out` after the Play deadline
    # playout took it over; a Game still playing out after it is logged as an error.
    playout_allowed_minutes: int = Field(60, ge=1, le=10080)

    # Mail (AD-9, AD-17, Story 3.5). With no RESEND_API_KEY outside production every mail goes
    # to the `[email:mock]` sender; the compose file never passes a key.
    email_from: str = LOCAL_EMAIL_FROM
    public_base_url: str = LOCAL_PUBLIC_BASE_URL
    resend_api_key: str = ""
    # The provider's rate limit (Story 4.4, NFR-3): the Resend sender sends at most this many
    # mails a second per process; `worker-batch` runs the mail queue in one process.
    mail_provider_per_second: float = Field(2.0, gt=0, le=100)
    # The signing secret of Resend's delivery and bounce webhook (Story 4.6, AD-11): `whsec_`
    # and a base64 key, as Resend shows it. Production refuses the local default.
    resend_webhook_secret: str = LOCAL_RESEND_WEBHOOK_SECRET

    # Storage (AD-17): required in production from Story 3.14 on, used by `platform/storage`
    # in a later epic. Server only, never sent to the browser.
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Comma-separated networks whose `X-Forwarded-For` the api believes (Story 3.14).
    trusted_proxy_cidrs: str = LOCAL_TRUSTED_PROXY_CIDRS

    # The error tracker (Story 15.11, AD-17, issue #28): a DSN in the Sentry form
    # `https://<key>@<host>/<project>`, which Sentry, GlitchTip and Bugsink accept. The tool is
    # the founder's open decision: empty outside production keeps every report in the recording
    # mock; empty in production only logs that reports are not sent.
    error_tracker_dsn: str = ""
    # The deployed commit, which Railway sets; sent with each report as its release.
    railway_git_commit_sha: str = ""

    @field_validator("log_level", mode="before")
    @classmethod
    def _lower_level(cls, v: object) -> object:
        return v.lower() if isinstance(v, str) else v

    @field_validator("ai_daily_alert_usd", "db_pooler_size", mode="before")
    @classmethod
    def _unset_alert(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, v: str) -> str:
        # Hosted Postgres hands out postgresql:// URLs; we use psycopg 3 only.
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v

    @field_validator("trusted_proxy_cidrs")
    @classmethod
    def _networks(cls, v: str) -> str:
        trusted_networks(v)  # a malformed entry refuses at load, naming the variable
        return v

    @field_validator("error_tracker_dsn")
    @classmethod
    def _dsn(cls, v: str) -> str:
        v = v.strip()
        if v:
            parse_dsn(v)  # a malformed DSN refuses at load, naming the variable, not its value
        return v

    def production_problems(self) -> list[str]:
        """The fields that break a production rule, in declaration order; empty outside
        production."""
        if self.app_env != "production":
            return []
        bad: list[str] = []
        if (
            self.database_url == LOCAL_DATABASE_URL
            or not _requires_tls(self.database_url)
            or uses_transaction_pooler(self.database_url)
        ):
            bad.append("database_url")
        secret = self.jwt_secret
        if (
            secret == LOCAL_JWT_SECRET
            or len(secret) < JWT_SECRET_MIN_LENGTH
            or len(set(secret)) < JWT_SECRET_MIN_DISTINCT
        ):
            bad.append("jwt_secret")
        if self.bcrypt_rounds < BCRYPT_ROUNDS_MIN_PRODUCTION:
            bad.append("bcrypt_rounds")
        for name, field in type(self).model_fields.items():
            if "_rate_limit_per_" in name and isinstance(field.default, int):
                if getattr(self, name) > field.default * RATE_LIMIT_PRODUCTION_FACTOR:
                    bad.append(name)
        if not _addresses_are_valid(self.bootstrap_admin_emails):
            bad.append("bootstrap_admin_emails")
        if self.email_from.strip() == LOCAL_EMAIL_FROM or not _addresses_are_valid(
            parseaddr(self.email_from)[1]
        ):
            bad.append("email_from")
        base = urlsplit(self.public_base_url)
        if (
            self.public_base_url == LOCAL_PUBLIC_BASE_URL
            or base.scheme != "https"
            or not base.hostname
        ):
            bad.append("public_base_url")
        bad.extend(name for name in REQUIRED_SECRETS if not getattr(self, name).strip())
        if self.resend_webhook_secret == LOCAL_RESEND_WEBHOOK_SECRET or not webhook_key(
            self.resend_webhook_secret
        ):
            bad.append("resend_webhook_secret")
        networks = trusted_networks(self.trusted_proxy_cidrs)
        if not networks or any(net.prefixlen == 0 for net in networks):
            bad.append("trusted_proxy_cidrs")
        if self.error_tracker_dsn and parse_dsn(self.error_tracker_dsn).scheme != "https":
            bad.append("error_tracker_dsn")  # reports leave only over TLS (NFR-7)
        return bad

    def check_production(self) -> None:
        bad = self.production_problems()
        if bad:
            why = ""
            if "database_url" in bad and _names_transaction_pooler(self.database_url):
                why = (
                    f" (DATABASE_URL points at the transaction pooler (port "
                    f"{TRANSACTION_POOLER_PORT}), which breaks LISTEN/NOTIFY and procrastinate; "
                    "use the session pooler on port 5432)"
                )
            raise ConfigError(
                f"Refusing to start with APP_ENV=production{why}: "
                f"missing, default or unsafe value for {', '.join(n.upper() for n in bad)}"
            )


def trusted_networks(value: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """The networks of a comma-separated CIDR list; raises ValueError on a malformed entry."""
    return [ipaddress.ip_network(part.strip()) for part in value.split(",") if part.strip()]


@dataclass(frozen=True)
class Dsn:
    """An error tracker's DSN, read: where its envelopes go and the key that signs them."""

    scheme: str
    public_key: str
    host: str
    """The host with its port, when the DSN names one."""
    prefix: str
    """The path before the project id, without a trailing slash (empty for most trackers)."""
    project_id: str

    @property
    def envelope_url(self) -> str:
        return f"{self.scheme}://{self.host}{self.prefix}/api/{self.project_id}/envelope/"


def parse_dsn(value: str) -> Dsn:
    """Read `<scheme>://<key>@<host>[:port][/<prefix>]/<project_id>`; raises ValueError naming
    no part of the value (it holds the key)."""
    parts = urlsplit(value.strip())
    try:
        port = parts.port
    except ValueError:
        raise ValueError("the DSN's port is not a number") from None
    path = parts.path.rstrip("/")
    prefix, _, project_id = path.rpartition("/")
    if (
        parts.scheme not in ("http", "https")
        or not parts.username
        or not parts.hostname
        or not project_id
        or parts.query
        or parts.fragment
    ):
        raise ValueError("not a DSN of the form <scheme>://<key>@<host>/<project>")
    host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname  # IPv6
    if port is not None:
        host = f"{host}:{port}"
    return Dsn(parts.scheme, parts.username, host, prefix, project_id)


def webhook_key(secret: str) -> bytes | None:
    """The signing key of a Svix-style webhook secret (`whsec_` and base64), or None when the
    secret has another shape or an empty key."""
    prefix = "whsec_"
    if not secret.startswith(prefix):
        return None
    try:
        key = base64.b64decode(secret[len(prefix) :], validate=True)
    except ValueError:
        return None
    return key or None


TRANSACTION_POOLER_PORT = 6543
"""Supabase's transaction pooler (Supavisor, transaction mode). It hands a client a server
connection per transaction, so LISTEN/NOTIFY and procrastinate's worker break on it; production
must use the session pooler on port 5432 (SETUP-GUIDE §5, Story 15.9)."""


def _ports(database_url: str) -> list[str]:
    """Every port the URL names: in its host part and in a libpq `port` query parameter. Raises
    ValueError when the host part's port cannot be read."""
    parts = urlsplit(database_url)
    found = [str(parts.port)] if parts.port is not None else []
    return found + [p.strip() for p in parse_qs(parts.query).get("port", [])]


def uses_transaction_pooler(database_url: str) -> bool:
    """True when the URL names the transaction pooler's port. A URL whose port cannot be read
    counts as one, so a malformed port never passes the production guard."""
    try:
        return str(TRANSACTION_POOLER_PORT) in _ports(database_url)
    except ValueError:
        return True


def _names_transaction_pooler(database_url: str) -> bool:
    """True only when the URL's port reads as the transaction pooler's (for the message)."""
    try:
        return str(TRANSACTION_POOLER_PORT) in _ports(database_url)
    except ValueError:
        return False


def _requires_tls(database_url: str) -> bool:
    """True when the URL asks libpq for TLS (`sslmode` require or stricter, NFR-7)."""
    modes = parse_qs(urlsplit(database_url).query).get("sslmode", [])
    return bool(modes) and all(mode in TLS_SSLMODES for mode in modes)


def _addresses_are_valid(value: str) -> bool:
    """At least one address, and every non-empty entry shaped like one: no whitespace, one `@`,
    a name before it and a dotted domain after it (the rule of `identity`'s address check)."""
    entries = [part.strip() for part in value.split(",") if part.strip()]
    if not entries:
        return False
    for entry in entries:
        if any(ch.isspace() or not ch.isprintable() for ch in entry) or entry.count("@") != 1:
            return False
        local, domain = entry.split("@")
        labels = domain.split(".")
        if not local or len(labels) < 2 or not all(labels):
            return False
    return True


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
