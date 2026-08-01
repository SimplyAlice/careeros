"""Unit tests for `BcryptPasswordHasher` and `JwtTokenService`.

Real implementations, not fakes — these are thin infrastructure adapters
where the whole point is proving the actual library integration works
(hash/verify round-trips, token encode/decode round-trips, expiry
actually rejects), matching the approach used for the PDF
renderer/local storage in Milestone 6.
"""

from __future__ import annotations

import time
import uuid

import jwt
import pytest

from app.application.auth.errors import InvalidTokenError
from app.core.config import Settings
from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_token_service import JwtTokenService


class TestBcryptPasswordHasher:
    def test_hash_then_verify_round_trips(self) -> None:
        hasher = BcryptPasswordHasher()

        hashed = hasher.hash("Sup3rSecret")

        assert hasher.verify(password="Sup3rSecret", password_hash=hashed) is True

    def test_verify_rejects_wrong_password(self) -> None:
        hasher = BcryptPasswordHasher()
        hashed = hasher.hash("Sup3rSecret")

        assert hasher.verify(password="wrong-password", password_hash=hashed) is False

    def test_hash_produces_a_different_value_each_time(self) -> None:
        """Bcrypt salts each hash independently — two hashes of the same
        password must never be identical (otherwise the salt isn't doing
        its job).
        """
        hasher = BcryptPasswordHasher()

        assert hasher.hash("Sup3rSecret") != hasher.hash("Sup3rSecret")

    def test_verify_returns_false_for_a_malformed_stored_hash(self) -> None:
        hasher = BcryptPasswordHasher()

        assert hasher.verify(password="anything", password_hash="not-a-real-bcrypt-hash") is False


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {"secret_key": "test-signing-key", "access_token_expire_minutes": 15}
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


class TestJwtTokenService:
    def test_create_then_decode_round_trips(self) -> None:
        service = JwtTokenService(_settings())
        user_id = uuid.uuid4()

        token = service.create_access_token(user_id=user_id)
        decoded_user_id = service.decode_access_token(token)

        assert decoded_user_id == user_id

    def test_decode_rejects_a_garbage_token(self) -> None:
        service = JwtTokenService(_settings())

        with pytest.raises(InvalidTokenError):
            service.decode_access_token("not-a-real-token")

    def test_decode_rejects_an_expired_token(self) -> None:
        service = JwtTokenService(_settings(access_token_expire_minutes=0))
        user_id = uuid.uuid4()
        token = service.create_access_token(user_id=user_id)

        time.sleep(1.1)  # ensure the exp claim (whole seconds) has passed

        with pytest.raises(InvalidTokenError):
            service.decode_access_token(token)

    def test_decode_rejects_a_token_signed_with_a_different_key(self) -> None:
        service = JwtTokenService(_settings(secret_key="key-one"))
        other_service = JwtTokenService(_settings(secret_key="key-two"))
        token = service.create_access_token(user_id=uuid.uuid4())

        with pytest.raises(InvalidTokenError):
            other_service.decode_access_token(token)

    def test_decode_rejects_a_token_missing_the_subject_claim(self) -> None:
        service = JwtTokenService(_settings())
        token_without_subject = jwt.encode({"iat": 0}, "test-signing-key", algorithm="HS256")

        with pytest.raises(InvalidTokenError, match="missing its subject claim"):
            service.decode_access_token(token_without_subject)

    def test_decode_rejects_a_token_with_a_non_uuid_subject(self) -> None:
        service = JwtTokenService(_settings())
        bad_token = jwt.encode({"sub": "not-a-uuid"}, "test-signing-key", algorithm="HS256")

        with pytest.raises(InvalidTokenError, match="not a valid user id"):
            service.decode_access_token(bad_token)
