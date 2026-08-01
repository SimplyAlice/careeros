"""JWT access token issuance and verification.

Implements `TokenService` (`app/application/auth/ports.py`) via PyJWT,
signing with HS256 and `Settings.secret_key` — the field Milestone 1
added as a placeholder specifically for this purpose ("Used for JWT
signing in later milestones").
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.application.auth.errors import InvalidTokenError
from app.core.config import Settings

_ALGORITHM = "HS256"


class JwtTokenService:
    """Issues and validates short-lived HS256 JWT access tokens."""

    def __init__(self, settings: Settings) -> None:
        self._secret_key = settings.secret_key
        self._expire_minutes = settings.access_token_expire_minutes

    def create_access_token(self, *, user_id: UUID) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret_key, algorithm=_ALGORITHM)

    def decode_access_token(self, token: str) -> UUID:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[_ALGORITHM])
        except jwt.InvalidTokenError as exc:
            # PyJWT's InvalidTokenError is the common base for expired,
            # malformed, and badly-signed tokens alike — all three mean
            # the same thing to a caller: this token can't be trusted.
            msg = "Access token is invalid or expired."
            raise InvalidTokenError(msg) from exc

        subject = payload.get("sub")
        if subject is None:
            msg = "Access token is missing its subject claim."
            raise InvalidTokenError(msg)

        try:
            return UUID(subject)
        except ValueError as exc:
            msg = "Access token subject claim is not a valid user id."
            raise InvalidTokenError(msg) from exc
