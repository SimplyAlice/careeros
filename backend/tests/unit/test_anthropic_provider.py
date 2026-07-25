"""Unit tests for `AnthropicProvider`.

The Anthropic SDK client is mocked — this is a unit test for our
adapter's request construction and response-text extraction, not a
contract test against Anthropic's live API (which would be separate,
deliberately labeled, and never part of the regular suite that runs on
every commit).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.infrastructure.ai_providers.anthropic_provider import AnthropicNotConfiguredError, AnthropicProvider


def _configured_settings() -> Settings:
    return Settings(secret_key="test", anthropic_api_key="test-api-key", anthropic_model="claude-test-model")


def _fake_response(text: str) -> SimpleNamespace:
    """A minimal stand-in for `anthropic.types.Message` — only the
    `content` blocks our adapter actually reads.
    """
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


@pytest.mark.asyncio
async def test_complete_raises_when_not_configured() -> None:
    unconfigured = Settings(secret_key="test")  # anthropic_api_key defaults to None
    provider = AnthropicProvider(unconfigured)

    with pytest.raises(AnthropicNotConfiguredError):
        await provider.complete(system="be helpful", prompt="hello")


@pytest.mark.asyncio
async def test_complete_returns_the_response_text() -> None:
    provider = AnthropicProvider(_configured_settings())

    with patch("app.infrastructure.ai_providers.anthropic_provider.AsyncAnthropic") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.messages.create = AsyncMock(return_value=_fake_response('{"score": 80}'))

        result = await provider.complete(system="be helpful", prompt="hello")

    assert result == '{"score": 80}'


@pytest.mark.asyncio
async def test_complete_passes_system_prompt_model_and_message_to_the_sdk() -> None:
    provider = AnthropicProvider(_configured_settings())

    with patch("app.infrastructure.ai_providers.anthropic_provider.AsyncAnthropic") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.messages.create = AsyncMock(return_value=_fake_response("ok"))

        await provider.complete(system="You are a scorer.", prompt="Score this job.")

        mock_client.messages.create.assert_awaited_once_with(
            model="claude-test-model",
            max_tokens=1024,
            system="You are a scorer.",
            messages=[{"role": "user", "content": "Score this job."}],
        )


@pytest.mark.asyncio
async def test_complete_concatenates_multiple_text_blocks() -> None:
    provider = AnthropicProvider(_configured_settings())
    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="part one "),
            SimpleNamespace(type="text", text="part two"),
        ]
    )

    with patch("app.infrastructure.ai_providers.anthropic_provider.AsyncAnthropic") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.messages.create = AsyncMock(return_value=response)

        result = await provider.complete(system="s", prompt="p")

    assert result == "part one part two"
