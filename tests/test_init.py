"""Tests for integration initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.pecron import async_setup_entry, async_unload_entry
from custom_components.pecron.const import DOMAIN


@pytest.fixture
def mock_hass() -> AsyncMock:
    """Return a mock Home Assistant instance."""
    hass = AsyncMock()
    hass.data = {DOMAIN: {}}
    hass.config_entries = AsyncMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Return a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "email": "test@example.com",
        "password": "password",
        "region": "US",
    }
    return entry


@pytest.mark.asyncio
async def test_async_setup_entry_imports() -> None:
    """Test that async_setup_entry function exists."""
    assert callable(async_setup_entry)


@pytest.mark.asyncio
async def test_async_unload_entry_imports() -> None:
    """Test that async_unload_entry function exists."""
    assert callable(async_unload_entry)


def test_domain_exists() -> None:
    """Test that domain constant is available."""
    assert DOMAIN == "pecron"
