"""Application-level errors for authentication use cases."""

from __future__ import annotations


class UserAlreadyExistsError(Exception):
    """Raised when registering with an email that's already taken."""


class InvalidCredentialsError(Exception):
    """Raised on login with an unknown email or a wrong password.

    Deliberately the same error for both cases — distinguishing "wrong
    password" from "no such user" in the response would let an attacker
    enumerate registered emails.
    """


class InvalidTokenError(Exception):
    """Raised when a JWT (access or refresh) is malformed, expired, or
    has been revoked.
    """
