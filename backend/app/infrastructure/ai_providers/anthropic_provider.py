"""Anthropic LLM provider adapter.

Implements `LLMProvider` (see `app/application/scoring/ports.py`) against
Anthropic's Messages API — the first concrete implementation of the
interface `docs/adr/0005-ai-provider-abstraction.md` (Milestone 0)
documented well before any AI feature existed. OpenAI/Gemini adapters
follow later behind the same interface, per that ADR.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.core.config import Settings

_MAX_RESPONSE_TOKENS = 1024


class AnthropicNotConfiguredError(Exception):
    """Raised when no Anthropic API key is configured.

    Mirrors `AdzunaNotConfiguredError` (Milestone 3): a specific,
    catchable exception rather than a confusing failure deep inside an
    HTTP call — the API layer maps this to a 503 telling the operator
    exactly which environment variable to set.
    """


class AnthropicProvider:
    """Calls Anthropic's Messages API and returns the model's text response."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.anthropic_api_key
        self._model = settings.anthropic_model

    async def complete(
        self, *, system: str, prompt: str, response_format: type[BaseModel] | None = None
    ) -> str:
        """Send `system`/`prompt` to the model and return its text response.

        `response_format` isn't passed to the Anthropic API directly —
        unlike some providers, Anthropic has no native structured-output
        parameter; the `system` prompt is expected to already contain the
        JSON-shape instruction (see `_SYSTEM_PROMPT` in
        `app/application/scoring/scoring_service.py`), and the caller
        validates the returned text against `response_format` itself.
        This parameter exists on the interface for provider parity (a
        future OpenAI adapter *can* use its native structured-output
        support here) — accepting but not using it keeps the `LLMProvider`
        protocol identical across adapters.
        """
        del response_format  # not used by this adapter; see docstring

        if not self._api_key:
            msg = "Anthropic API key is not configured (ANTHROPIC_API_KEY)."
            raise AnthropicNotConfiguredError(msg)

        client = AsyncAnthropic(api_key=self._api_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=_MAX_RESPONSE_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        text_blocks = [block.text for block in response.content if block.type == "text"]
        return "".join(text_blocks)
