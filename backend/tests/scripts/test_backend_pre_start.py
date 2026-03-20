from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.backend_pre_start import init, logger


@pytest.mark.anyio
async def test_init_successful_connection() -> None:
    mock_client = MagicMock()
    mock_client.admin.command = AsyncMock(return_value={"ok": 1})

    with (
        patch(
            "app.backend_pre_start.AsyncIOMotorClient",
            return_value=mock_client,
        ),
        patch.object(logger, "info"),
        patch.object(logger, "error"),
        patch.object(logger, "warn"),
    ):
        try:
            await init()
            connection_successful = True
        except Exception:
            connection_successful = False

        assert connection_successful, (
            "The database connection should be successful and not raise an exception."
        )

        mock_client.admin.command.assert_called_once_with("ping")
