"""Tests for config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests
from unofficial_pecron_api.exceptions import AuthenticationError

from custom_components.pecron.config_flow import (
    PecronAuthError,
    PecronConfigFlow,
    PecronConnectionError,
)
from custom_components.pecron.const import (
    DEFAULT_REGION,
    DOMAIN,
)


@pytest.fixture
def mock_hass() -> object:
    """Return a mock Home Assistant instance."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_config_flow_user_step(mock_hass: object) -> None:
    """Test user config flow step."""
    # This is a placeholder for full config flow tests
    # They would require mocking the config_flow.ConfigFlow class
    assert DOMAIN == "pecron"
    assert DEFAULT_REGION == "US"


def test_config_flow_imports() -> None:
    """Test that config flow module imports successfully."""
    try:
        from custom_components.pecron import config_flow

        assert config_flow is not None
    except ImportError:
        assert False, "config_flow module could not be imported"


class TestValidatePecronCredentials:
    """Tests for the region-vs-credentials error classification (GH#6)."""

    def test_authentication_error_raises_auth_error(self) -> None:
        """A rejected login (bad password OR wrong region) maps to invalid_auth."""
        with patch("custom_components.pecron.config_flow.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login.side_effect = AuthenticationError("signature invalid", code=5001)
            mock_api_class.return_value = api

            with pytest.raises(PecronAuthError):
                PecronConfigFlow._validate_pecron_credentials("test@example.com", "password", "EU")

    def test_network_error_raises_connection_error(self) -> None:
        """A genuine network failure maps to cannot_connect."""
        with patch("custom_components.pecron.config_flow.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login.side_effect = requests.exceptions.ConnectionError("DNS failure")
            mock_api_class.return_value = api

            with pytest.raises(PecronConnectionError):
                PecronConfigFlow._validate_pecron_credentials("test@example.com", "password", "US")

    def test_no_devices_raises_auth_error(self) -> None:
        """An account with no bound devices is treated as an auth-level problem."""
        with patch("custom_components.pecron.config_flow.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login.return_value = None
            api.get_devices.return_value = []
            mock_api_class.return_value = api

            with pytest.raises(PecronAuthError):
                PecronConfigFlow._validate_pecron_credentials("test@example.com", "password", "US")

    def test_successful_login_does_not_raise(self) -> None:
        """A successful login with devices present raises nothing."""
        with patch("custom_components.pecron.config_flow.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login.return_value = None
            api.get_devices.return_value = [MagicMock()]
            mock_api_class.return_value = api

            PecronConfigFlow._validate_pecron_credentials("test@example.com", "password", "US")
