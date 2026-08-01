"""Bcrypt password hashing.

Implements `PasswordHasher` (`app/application/auth/ports.py`) via the
`bcrypt` library directly — chosen over `passlib` (which itself wraps
bcrypt, among other algorithms) to avoid a heavier dependency for a
single, settled choice; `docs/architecture/security.md` and
`docs/adr/0008-jwt-auth.md` (Milestone 0) already named bcrypt/argon2id
as the intended algorithm.
"""

from __future__ import annotations

import bcrypt

_BCRYPT_ROUNDS = 12


class BcryptPasswordHasher:
    """Hashes and verifies passwords with bcrypt."""

    def hash(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify(self, *, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            # A malformed stored hash (shouldn't happen in practice, but
            # bcrypt raises rather than returning False for garbage
            # input) is treated as "doesn't match" — never let a
            # corrupted hash crash the login endpoint.
            return False
