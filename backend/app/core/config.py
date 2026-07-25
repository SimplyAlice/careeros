"""Application configuration.

Centralizes all environment-driven configuration behind a single, typed
`Settings` object, loaded once via `get_settings()` (cached with
`lru_cache` so it's cheap to depend on from anywhere, including FastAPI's
dependency-injection system).

Design notes
------------
- Values are read from environment variables (and a local `.env` file in
  development) via `pydantic-settings`. Nothing here should ever contain a
  real secret — see `.env.example` at the repo root for the documented set
  of variables, all with placeholder values.
- `Environment` distinguishes development / testing / production so that
  behavior that must differ (e.g. whether interactive API docs are
  exposed) is driven by one explicit field, not scattered `if DEBUG`
  checks.
- This module has no FastAPI or SQLAlchemy imports — it is pure
  configuration and safe to import from any layer.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """The environment the application is running in.

    Deliberately a closed set of three values (not an arbitrary string) so
    environment-dependent branches in the codebase (e.g. `if settings.environment
    is Environment.PRODUCTION`) are checked by the type system, not by string
    comparison typos.
    """

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Typed application settings, sourced from environment variables / `.env`.

    Every field has either a sensible development default or is required
    (no default) when it must be explicitly provided in every environment
    (e.g. `secret_key`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application identity -------------------------------------------------
    project_name: str = "CareerOS"
    api_v1_prefix: str = "/api/v1"
    version: str = "0.1.0"

    # --- Environment / debug ---------------------------------------------------
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # --- Security ----------------------------------------------------------
    # Placeholder for JWT implementation (Milestone 2+). Required now so the
    # settings object fails fast in any environment that forgets to set it,
    # rather than silently running with an insecure default.
    secret_key: str = Field(..., description="Used for JWT signing in later milestones.")

    # --- Database ------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://careeros:careeros@postgres:5432/careeros",
        description="Async SQLAlchemy connection string.",
    )

    # --- Redis ---------------------------------------------------------------
    redis_url: str = Field(default="redis://redis:6379/0")

    # --- CORS ------------------------------------------------------------------
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Job sources (Milestone 3) --------------------------------------------
    # Optional (default None) so an environment without real Adzuna
    # credentials still starts up normally — the ingestion endpoint returns
    # a clear 503 rather than the app failing at startup. Get free
    # credentials at https://developer.adzuna.com.
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    adzuna_country: str = "us"

    # --- AI provider (Milestone 5) ----------------------------------------------
    # Optional (default None), same reasoning as Adzuna above — the
    # scoring endpoint returns a clear 503 rather than the app failing to
    # start. Verify the current model identifier against
    # https://docs.anthropic.com/en/docs/about-claude/models before
    # deploying — model strings are versioned and change over time.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # --- Logging -----------------------------------------------------------
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            msg = f"log_level must be one of {sorted(allowed)}, got {value!r}"
            raise ValueError(msg)
        return normalized

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @property
    def docs_enabled(self) -> bool:
        """Interactive API docs are enabled everywhere except production.

        Matches the API strategy documented in
        `docs/architecture/api-design.md`: OpenAPI docs are a development
        convenience, not something exposed unauthenticated in production.
        """
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide `Settings` instance.

    Cached so repeated calls (e.g. from many FastAPI `Depends(get_settings)`
    usages) don't re-parse the environment on every request — the
    environment doesn't change during a process's lifetime.
    """
    return Settings()
