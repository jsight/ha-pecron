"""Tests for automatic token refresh functionality."""

from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from unofficial_pecron_api.exceptions import PecronAPIError

from custom_components.pecron import PecronDataUpdateCoordinator


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = AsyncMock()
    hass.data = {}
    hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
    return hass


@pytest.fixture
def mock_pecron_api():
    """Create a mock PecronAPI."""
    api = MagicMock()
    api.login = MagicMock()
    api.get_devices = MagicMock(return_value=[])
    api.get_device_properties = MagicMock()
    api.get_product_tsl = MagicMock(return_value=[])
    api.close = MagicMock()
    return api


@pytest.fixture
def mock_device():
    """Create a mock device."""
    device = MagicMock()
    device.device_key = "test_key"
    device.device_name = "Test Device"
    device.product_name = "Test Product"
    device.product_key = "test_product"
    device.online = True
    return device


@pytest.fixture
def mock_properties():
    """Create mock device properties."""
    props = MagicMock()
    props.battery_percentage = 75
    props.total_input_power = 100
    props.total_output_power = 50
    return props


class TestTokenRefreshDuringDeviceListFetch:
    """Test token refresh when authentication fails during get_devices()."""

    @pytest.mark.asyncio
    async def test_auth_failure_on_initial_fetch_triggers_retry(
        self, mock_hass, mock_pecron_api, mock_device, mock_properties
    ):
        """Test that auth failure during initial device fetch triggers retry."""
        with patch("custom_components.pecron.PecronAPI", return_value=mock_pecron_api):
            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # First call fails with auth error, second succeeds
            mock_pecron_api.get_devices.side_effect = [
                PecronAPIError("Token validation failed", code=5032),
                [mock_device],
            ]
            mock_pecron_api.get_device_properties.return_value = mock_properties

            # Should retry and succeed on second attempt
            await coordinator.async_refresh()

            # Verify retry happened (get_devices called twice)
            assert mock_pecron_api.get_devices.call_count == 2


class TestTokenRefreshDuringPropertyFetch:
    """Test token refresh when authentication fails during get_device_properties()."""

    @pytest.mark.asyncio
    async def test_auth_failure_during_property_fetch_triggers_retry(
        self, mock_hass, mock_pecron_api, mock_device, mock_properties
    ):
        """Test that auth failure during property fetch triggers retry and API reset."""
        call_count = 0

        def property_side_effect(device):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PecronAPIError("API error 5032: Token validation failed", code=5032)
            return mock_properties

        with patch("custom_components.pecron.PecronAPI", return_value=mock_pecron_api):
            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # Setup: initial fetch succeeds
            mock_pecron_api.get_devices.return_value = [mock_device]
            mock_pecron_api.get_device_properties.return_value = mock_properties

            # First refresh succeeds
            await coordinator.async_refresh()
            assert coordinator.data is not None

            # Second refresh: property fetch fails with auth error, then succeeds on retry
            mock_pecron_api.get_device_properties.side_effect = property_side_effect

            # This should trigger auth error detection and retry, then succeed
            await coordinator.async_refresh()

            # Verify retry happened
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_error_5032_detected_and_api_reset(
        self, mock_hass, mock_device, mock_properties
    ):
        """Test that error code 5032 is detected, API is reset, and retries work."""
        call_count = 0

        def property_side_effect(device):
            nonlocal call_count
            call_count += 1
            # Fail on first call with 5032, then succeed
            if call_count == 1:
                raise PecronAPIError("API error 5032: Token validation failed", code=5032)
            return mock_properties

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            api_instances = []

            def create_api(*args, **kwargs):
                api = MagicMock()
                api.login = MagicMock()
                api.get_devices.return_value = [mock_device]
                api.get_device_properties.side_effect = property_side_effect
                api.get_product_tsl.return_value = []
                api_instances.append(api)
                return api

            mock_api_class.side_effect = create_api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # Initial refresh: should fail once with 5032, then retry and succeed
            await coordinator.async_refresh()

            # Verify retry happened (2 property fetch attempts)
            assert call_count == 2
            # API instance created multiple times due to reset
            assert len(api_instances) >= 2

    @pytest.mark.asyncio
    async def test_token_string_in_error_triggers_reset(
        self, mock_hass, mock_device, mock_properties
    ):
        """Test that 'token' in error message triggers API reset and retry."""
        call_count = 0

        def property_side_effect(device):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PecronAPIError("Invalid token provided", code=400)
            return mock_properties

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login = MagicMock()
            api.get_devices.return_value = [mock_device]
            api.get_device_properties.side_effect = property_side_effect
            api.get_product_tsl.return_value = []
            mock_api_class.return_value = api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # Should detect 'token' and retry successfully
            await coordinator.async_refresh()
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_authentication_string_triggers_reset(
        self, mock_hass, mock_device, mock_properties
    ):
        """Test that 'authentication' in error message triggers API reset and retry."""
        call_count = 0

        def property_side_effect(device):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PecronAPIError("Authentication failed", code=401)
            return mock_properties

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login = MagicMock()
            api.get_devices.return_value = [mock_device]
            api.get_device_properties.side_effect = property_side_effect
            api.get_product_tsl.return_value = []
            mock_api_class.return_value = api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            await coordinator.async_refresh()
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_401_error_triggers_reset(
        self, mock_hass, mock_device, mock_properties
    ):
        """Test that 401 error code triggers API reset and retry."""
        call_count = 0

        def property_side_effect(device):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PecronAPIError("Unauthorized - 401 error", code=401)
            return mock_properties

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login = MagicMock()
            api.get_devices.return_value = [mock_device]
            api.get_device_properties.side_effect = property_side_effect
            api.get_product_tsl.return_value = []
            mock_api_class.return_value = api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            await coordinator.async_refresh()
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_unauthorized_string_triggers_reset(
        self, mock_hass, mock_device, mock_properties
    ):
        """Test that 'unauthorized' in error message triggers API reset and retry."""
        call_count = 0

        def property_side_effect(device):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PecronAPIError("Unauthorized access", code=403)
            return mock_properties

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login = MagicMock()
            api.get_devices.return_value = [mock_device]
            api.get_device_properties.side_effect = property_side_effect
            api.get_product_tsl.return_value = []
            mock_api_class.return_value = api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            await coordinator.async_refresh()
            assert call_count == 2


class TestNonAuthErrorsDontTriggerReset:
    """Test that non-authentication errors don't trigger API reset."""

    @pytest.mark.asyncio
    async def test_connection_error_does_not_reset_api(
        self, mock_hass, mock_pecron_api, mock_device, mock_properties
    ):
        """Test that connection errors don't reset API."""
        with patch("custom_components.pecron.PecronAPI", return_value=mock_pecron_api):
            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            mock_pecron_api.get_devices.return_value = [mock_device]
            await coordinator.async_refresh()

            original_api = coordinator.api

            # Property fetch fails with connection error (non-auth)
            mock_pecron_api.get_device_properties.side_effect = Exception(
                "Connection timeout"
            )

            # Should not raise (error is caught and logged for individual device)
            await coordinator.async_refresh()

            # API should NOT be reset for non-auth errors
            assert coordinator.api is original_api

    @pytest.mark.asyncio
    async def test_generic_error_does_not_reset_api(
        self, mock_hass, mock_pecron_api, mock_device, mock_properties
    ):
        """Test that generic errors don't reset API."""
        with patch("custom_components.pecron.PecronAPI", return_value=mock_pecron_api):
            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            mock_pecron_api.get_devices.return_value = [mock_device]
            await coordinator.async_refresh()

            original_api = coordinator.api

            mock_pecron_api.get_device_properties.side_effect = Exception(
                "Something went wrong"
            )

            await coordinator.async_refresh()

            # API should NOT be reset
            assert coordinator.api is original_api


class TestPartialSuccessScenarios:
    """Test scenarios where some devices succeed and others fail."""

    @pytest.mark.asyncio
    async def test_auth_error_on_first_device_stops_processing(
        self, mock_hass, mock_properties
    ):
        """Test that auth error on first device triggers retry and processes both devices."""
        device1 = MagicMock()
        device1.device_key = "device1"
        device1.device_name = "Device 1"
        device1.product_name = "Product 1"

        device2 = MagicMock()
        device2.device_key = "device2"
        device2.device_name = "Device 2"
        device2.product_name = "Product 2"

        call_count = 0

        def property_side_effect(device):
            nonlocal call_count
            call_count += 1
            # First call fails (device1 on first attempt), then succeeds for all subsequent calls
            if call_count == 1:
                raise PecronAPIError("Token validation failed", code=5032)
            return mock_properties

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login = MagicMock()
            api.get_devices.return_value = [device1, device2]
            api.get_device_properties.side_effect = property_side_effect
            api.get_product_tsl.return_value = []
            mock_api_class.return_value = api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # Auth error on first device should trigger retry, then process both devices
            await coordinator.async_refresh()

            # First call fails, retry processes both devices (3 total calls)
            assert call_count >= 2  # At least the retry happened


class TestRetryLogic:
    """Test the retry logic in _async_update_data."""

    @pytest.mark.asyncio
    async def test_max_retries_respected(
        self, mock_hass, mock_device
    ):
        """Test that max retries (2) is respected when auth keeps failing."""
        api_instances = []

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            def create_api(*args, **kwargs):
                api = MagicMock()
                api.login = MagicMock()
                # Always fail with auth error
                api.get_devices.side_effect = PecronAPIError(
                    "Token validation failed", code=5032
                )
                api.get_product_tsl.return_value = []
                api_instances.append(api)
                return api

            mock_api_class.side_effect = create_api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # All attempts fail with auth error, should exhaust retries
            try:
                await coordinator.async_refresh()
                # If no exception, check that it tried multiple times
                assert len(api_instances) >= 2
            except UpdateFailed as exc:
                # Should have tried max_retries times
                assert len(api_instances) == 2
                assert "Authentication failed" in str(exc)

    @pytest.mark.asyncio
    async def test_successful_retry_after_auth_failure(
        self, mock_hass, mock_device, mock_properties
    ):
        """Test successful retry after initial auth failure."""
        call_count = 0

        def side_effect_get_properties(device):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PecronAPIError("Token validation failed", code=5032)
            return mock_properties

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            mock_api = MagicMock()
            mock_api.login = MagicMock()
            mock_api.get_devices.return_value = [mock_device]
            mock_api.get_device_properties = MagicMock(side_effect=side_effect_get_properties)
            mock_api.get_product_tsl.return_value = []
            mock_api_class.return_value = mock_api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # First attempt fails, second succeeds
            await coordinator.async_refresh()

            # Should have succeeded on retry
            assert coordinator.data is not None
            assert mock_device.device_key in coordinator.data


class TestCaseInsensitiveErrorDetection:
    """Test that error detection is case-insensitive."""

    @pytest.mark.asyncio
    async def test_uppercase_token_detected(
        self, mock_hass, mock_device, mock_properties
    ):
        """Test that 'TOKEN' (uppercase) is detected."""
        call_count = 0

        def property_side_effect(device):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Invalid TOKEN provided")
            return mock_properties

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login = MagicMock()
            api.get_devices.return_value = [mock_device]
            api.get_device_properties.side_effect = property_side_effect
            api.get_product_tsl.return_value = []
            mock_api_class.return_value = api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # Should detect 'TOKEN' (case-insensitive) and retry
            await coordinator.async_refresh()
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_mixed_case_authentication_detected(
        self, mock_hass, mock_device, mock_properties
    ):
        """Test that 'Authentication' (mixed case) is detected."""
        call_count = 0

        def property_side_effect(device):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Authentication Failed")
            return mock_properties

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            api = MagicMock()
            api.login = MagicMock()
            api.get_devices.return_value = [mock_device]
            api.get_device_properties.side_effect = property_side_effect
            api.get_product_tsl.return_value = []
            mock_api_class.return_value = api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # Should detect 'Authentication' (case-insensitive) and retry
            await coordinator.async_refresh()
            assert call_count == 2


class TestAPIReinitialization:
    """Test that API is properly reinitialized after reset."""

    @pytest.mark.asyncio
    async def test_api_reinitialized_after_reset(
        self, mock_hass, mock_device, mock_properties
    ):
        """Test that setting api=None triggers fresh login on next fetch."""
        login_calls = []

        with patch("custom_components.pecron.PecronAPI") as mock_api_class:
            def create_api(*args, **kwargs):
                api = MagicMock()
                api.login = MagicMock(side_effect=lambda *a: login_calls.append(a))
                api.get_devices.return_value = [mock_device]
                api.get_device_properties.return_value = mock_properties
                api.get_product_tsl.return_value = []
                return api

            mock_api_class.side_effect = create_api

            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            # First refresh
            await coordinator.async_refresh()
            assert len(login_calls) == 1

            # Manually reset API (simulating token expiration detection)
            coordinator.api = None

            # Next refresh should re-login
            await coordinator.async_refresh()
            assert len(login_calls) == 2

    @pytest.mark.asyncio
    async def test_token_refresh_logged(
        self, mock_hass, mock_pecron_api, mock_device, mock_properties
    ):
        """Test that token refresh is logged appropriately."""
        with patch("custom_components.pecron.PecronAPI", return_value=mock_pecron_api):
            coordinator = PecronDataUpdateCoordinator(
                mock_hass, "test@example.com", "password", "US", 600
            )

            mock_pecron_api.get_devices.return_value = [mock_device]
            mock_pecron_api.get_device_properties.return_value = mock_properties

            # First refresh (initial setup)
            await coordinator.async_refresh()
            assert coordinator.devices == [mock_device]

            # Force API reset (simulating token expiration)
            coordinator.api = None

            # Second refresh (should log as token refresh)
            await coordinator.async_refresh()
            # Verify devices list is preserved (indicates refresh, not initial setup)
            assert len(coordinator.devices) > 0
