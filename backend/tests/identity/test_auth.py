"""`platform/auth` without a database: hashing, the token and the cookie (AD-11)."""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from starlette.responses import Response

from app.platform import auth
from app.platform.config import get_settings

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def test_a_password_verifies_and_a_wrong_one_does_not():
    stored = auth.hash_password("riktig passord")
    assert stored.startswith("$2b$04$")  # the tests' cheap cost
    assert auth.verify_password("riktig passord", stored)
    assert not auth.verify_password("feil passord", stored)


def test_the_password_is_sha256_base64_before_bcrypt():
    """bcrypt 5 rejects input over 72 bytes; the pre-hash keeps every password at 44 bytes."""
    long_a = "x" * 100 + "a"
    long_b = "x" * 100 + "b"
    stored = auth.hash_password(long_a)
    assert auth.verify_password(long_a, stored)
    assert not auth.verify_password(long_b, stored)
    assert bcrypt.checkpw(auth._prehash(long_a), stored.encode())


def test_a_malformed_stored_hash_never_verifies():
    assert not auth.verify_password("x", "not-a-bcrypt-hash")


def test_the_dummy_hash_is_a_real_hash_that_matches_no_typed_password():
    assert auth.dummy_hash().startswith("$2b$")
    assert not auth.verify_password("", auth.dummy_hash())


def test_the_token_carries_the_user_id_and_its_times_only():
    user_id = uuid.uuid7()
    token = auth.issue_token(user_id, NOW)
    claims = jwt.decode(token, options={"verify_signature": False})
    assert set(claims) == {"user_id", "iat", "exp"}
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    assert auth.read_token(token, NOW + timedelta(hours=1)) == user_id


def test_an_expired_token_is_refused():
    token = auth.issue_token(uuid.uuid7(), NOW)
    max_age = timedelta(hours=get_settings().session_max_age_hours)
    assert auth.read_token(token, NOW + max_age - timedelta(seconds=1)) is not None
    assert auth.read_token(token, NOW + max_age) is None


def test_a_tampered_or_foreign_token_is_refused():
    user_id = uuid.uuid7()
    token = auth.issue_token(user_id, NOW)
    head, body, signature = token.split(".")
    flipped = signature[:-2] + ("AA" if signature[-2:] != "AA" else "BB")
    assert auth.read_token(f"{head}.{body}.{flipped}", NOW) is None
    foreign = jwt.encode(
        {"user_id": str(user_id), "iat": NOW, "exp": NOW + timedelta(hours=1)},
        "another-secret-that-is-long-enough-for-hs256",
        algorithm="HS256",
    )
    assert auth.read_token(foreign, NOW) is None
    unsigned = jwt.encode(
        {"user_id": str(user_id), "iat": NOW, "exp": NOW + timedelta(hours=1)},
        None,
        algorithm="none",
    )
    assert auth.read_token(unsigned, NOW) is None


def test_a_token_without_a_claim_or_with_a_bad_user_id_is_refused():
    secret = get_settings().jwt_secret
    no_exp = jwt.encode({"user_id": str(uuid.uuid7()), "iat": NOW}, secret, algorithm="HS256")
    bad_id = jwt.encode(
        {"user_id": "x", "iat": NOW, "exp": NOW + timedelta(hours=1)}, secret, algorithm="HS256"
    )
    assert auth.read_token(no_exp, NOW) is None
    assert auth.read_token(bad_id, NOW) is None
    assert auth.read_token(None, NOW) is None
    assert auth.read_token("", NOW) is None
    assert auth.read_token("garbage", NOW) is None


def test_the_cookie_is_httponly_secure_and_samesite_lax():
    response = Response()
    auth.set_session_cookie(response, uuid.uuid7(), NOW)
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{auth.COOKIE_NAME}=")
    for part in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"):
        assert part in cookie
    assert f"Max-Age={get_settings().session_max_age_hours * 3600}" in cookie


def test_clearing_the_cookie_expires_it():
    response = Response()
    auth.clear_session_cookie(response)
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f'{auth.COOKIE_NAME}=""') or cookie.startswith(f"{auth.COOKIE_NAME}=;")
    assert "Max-Age=0" in cookie


def test_a_signed_token_with_an_absurd_exp_or_a_non_string_user_id_is_refused():
    secret = get_settings().jwt_secret
    huge = jwt.encode(
        {"user_id": str(uuid.uuid7()), "iat": 0, "exp": 10**20}, secret, algorithm="HS256"
    )
    numeric = jwt.encode(
        {"user_id": 123, "iat": NOW, "exp": NOW + timedelta(hours=1)}, secret, algorithm="HS256"
    )
    assert auth.read_token(huge, NOW) is None
    assert auth.read_token(numeric, NOW) is None
