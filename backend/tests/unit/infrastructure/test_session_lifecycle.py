from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.db.session import get_db_session


@pytest.mark.asyncio
async def test_get_db_session_commits_on_success() -> None:
    mock_session = AsyncMock()
    mock_session.is_active = True
    mock_session_factory = MagicMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    mock_session_ctx.__aexit__.return_value = None
    mock_session_factory.return_value = mock_session_ctx

    with patch("app.infrastructure.db.session.get_session_factory", return_value=mock_session_factory):
        async for session in get_db_session():
            assert session is mock_session
            # Simulate some work inside the endpoint
            mock_session.is_active = True

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_db_session_rolls_back_on_exception() -> None:
    mock_session = AsyncMock()
    mock_session.is_active = True
    mock_session_factory = MagicMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    mock_session_ctx.__aexit__.return_value = None
    mock_session_factory.return_value = mock_session_ctx

    with patch("app.infrastructure.db.session.get_session_factory", return_value=mock_session_factory):
        gen = get_db_session()
        session = await gen.__anext__()
        assert session is mock_session
        with pytest.raises(RuntimeError, match="Endpoint error"):
            await gen.athrow(RuntimeError("Endpoint error"))

    mock_session.commit.assert_not_awaited()
    mock_session.rollback.assert_awaited_once()
