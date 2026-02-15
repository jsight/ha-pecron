"""Comprehensive tests for smart time sensor logic."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.pecron.sensor import PECRON_SENSORS, PecronSensor
from custom_components.pecron.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = AsyncMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_coordinator():
    """Create mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = None
    return coordinator


@pytest.fixture
def mock_device():
    """Create mock device."""
    device = MagicMock()
    device.device_key = "test_device"
    device.device_name = "Test Device"
    device.product_name = "Test Product"
    return device


@pytest.fixture
def time_to_full_desc():
    """Get Time to Full sensor description."""
    return next(s for s in PECRON_SENSORS if s.key == "remain_charging_time")


@pytest.fixture
def time_to_empty_desc():
    """Get Time to Empty sensor description."""
    return next(s for s in PECRON_SENSORS if s.key == "remain_discharging_time")


def create_props(charging_time=None, discharging_time=None, input_power=0, output_power=0):
    """Helper to create mock properties object."""
    props = MagicMock()
    if charging_time is not None:
        props.remain_charging_time = charging_time
    else:
        delattr(props, "remain_charging_time")

    if discharging_time is not None:
        props.remain_discharging_time = discharging_time
    else:
        delattr(props, "remain_discharging_time")

    props.total_input_power = input_power
    props.total_output_power = output_power

    return props


class TestDeviceStates:
    """Test sensor behavior in different device states."""

    def test_idle_state_both_time_sensors_show_na(
        self, mock_coordinator, mock_device, time_to_full_desc, time_to_empty_desc
    ):
        """IDLE: Both sensors should show N/A."""
        props = create_props(
            charging_time=120,
            discharging_time=240,
            input_power=0,
            output_power=0,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        # Time to Full
        sensor_full = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor_full.native_value is None

        # Time to Empty
        sensor_empty = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_empty_desc)
        assert sensor_empty.native_value is None

    def test_charging_only_state(
        self, mock_coordinator, mock_device, time_to_full_desc, time_to_empty_desc
    ):
        """CHARGING_ONLY: Show Time to Full, N/A for Time to Empty."""
        props = create_props(
            charging_time=120,
            discharging_time=240,
            input_power=100,
            output_power=0,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        # Time to Full - should show value
        sensor_full = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor_full.native_value == 120

        # Time to Empty - should be N/A
        sensor_empty = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_empty_desc)
        assert sensor_empty.native_value is None

    def test_discharging_only_state(
        self, mock_coordinator, mock_device, time_to_full_desc, time_to_empty_desc
    ):
        """DISCHARGING_ONLY: N/A for Time to Full, show Time to Empty."""
        props = create_props(
            charging_time=120,
            discharging_time=240,
            input_power=0,
            output_power=50,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        # Time to Full - should be N/A
        sensor_full = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor_full.native_value is None

        # Time to Empty - should show value
        sensor_empty = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_empty_desc)
        assert sensor_empty.native_value == 240

    def test_ups_mode_state(
        self, mock_coordinator, mock_device, time_to_full_desc, time_to_empty_desc
    ):
        """UPS_MODE: Show both time values (input + output active)."""
        props = create_props(
            charging_time=120,
            discharging_time=240,
            input_power=100,
            output_power=50,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        # Time to Full - should show value (charging toward 100%)
        sensor_full = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor_full.native_value == 120

        # Time to Empty - should show value (runtime if input lost)
        sensor_empty = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_empty_desc)
        assert sensor_empty.native_value == 240


class TestPropertyMissing:
    """Test behavior when properties are missing."""

    def test_charging_time_missing_shows_na(
        self, mock_coordinator, mock_device, time_to_full_desc
    ):
        """Property missing should show N/A regardless of state."""
        props = create_props(
            charging_time=None,  # Missing
            discharging_time=240,
            input_power=100,  # Charging state
            output_power=0,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        sensor = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor.native_value is None

    def test_discharging_time_missing_shows_na(
        self, mock_coordinator, mock_device, time_to_empty_desc
    ):
        """Property missing should show N/A regardless of state."""
        props = create_props(
            charging_time=120,
            discharging_time=None,  # Missing
            input_power=0,
            output_power=50,  # Discharging state
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        sensor = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_empty_desc)
        assert sensor.native_value is None

    def test_both_properties_missing(
        self, mock_coordinator, mock_device, time_to_full_desc, time_to_empty_desc
    ):
        """Both missing should show N/A."""
        props = create_props(
            charging_time=None,
            discharging_time=None,
            input_power=100,
            output_power=50,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        sensor_full = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor_full.native_value is None

        sensor_empty = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_empty_desc)
        assert sensor_empty.native_value is None


class TestPropertyZeroValues:
    """Test behavior with zero property values."""

    def test_charging_time_zero_while_charging(
        self, mock_coordinator, mock_device, time_to_full_desc
    ):
        """Zero charging time (battery full) should show 0, not N/A."""
        props = create_props(
            charging_time=0,  # Battery at 100%
            discharging_time=240,
            input_power=100,
            output_power=0,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        sensor = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor.native_value == 0

    def test_discharging_time_zero_while_discharging(
        self, mock_coordinator, mock_device, time_to_empty_desc
    ):
        """Zero discharging time (battery empty) should show 0, not N/A."""
        props = create_props(
            charging_time=120,
            discharging_time=0,  # Battery depleted
            input_power=0,
            output_power=50,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        sensor = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_empty_desc)
        assert sensor.native_value == 0


class TestPowerValueEdgeCases:
    """Test edge cases with power values."""

    def test_negative_power_values_treated_as_zero(
        self, mock_coordinator, mock_device, time_to_full_desc, time_to_empty_desc
    ):
        """Negative power (measurement error) should be treated as 0."""
        props = create_props(
            charging_time=120,
            discharging_time=240,
            input_power=-5,  # Negative (error)
            output_power=-2,  # Negative (error)
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        # Should be treated as IDLE state (both 0)
        sensor_full = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor_full.native_value is None

        sensor_empty = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_empty_desc)
        assert sensor_empty.native_value is None

    def test_power_values_missing_treated_as_zero(
        self, mock_coordinator, mock_device, time_to_full_desc
    ):
        """Missing power properties should be treated as 0."""
        props = MagicMock()
        props.remain_charging_time = 120
        delattr(props, "total_input_power")  # Missing
        delattr(props, "total_output_power")  # Missing

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        # Should be treated as IDLE (both missing = both 0)
        sensor = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor.native_value is None

    def test_power_values_none_treated_as_zero(
        self, mock_coordinator, mock_device, time_to_full_desc
    ):
        """None power values should be treated as 0."""
        props = create_props(
            charging_time=120,
            discharging_time=240,
            input_power=None,
            output_power=None,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        # Should be treated as IDLE
        sensor = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor.native_value is None

    def test_small_power_values_still_trigger_state(
        self, mock_coordinator, mock_device, time_to_full_desc
    ):
        """Small power values (1W) should still trigger state logic."""
        props = create_props(
            charging_time=120,
            discharging_time=240,
            input_power=1,  # Very small
            output_power=0,
        )

        mock_coordinator.data = {
            "test_device": {
                "device": mock_device,
                "properties": props,
            }
        }

        # Should be CHARGING state (input > 0)
        sensor = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor.native_value == 120


class TestCoordinatorDataEdgeCases:
    """Test edge cases with coordinator data."""

    def test_coordinator_data_none(
        self, mock_coordinator, mock_device, time_to_full_desc
    ):
        """No coordinator data should return None."""
        mock_coordinator.data = None

        sensor = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor.native_value is None

    def test_device_not_in_coordinator_data(
        self, mock_coordinator, mock_device, time_to_full_desc
    ):
        """Device not in coordinator data should return None."""
        mock_coordinator.data = {}  # Empty dict

        sensor = PecronSensor(mock_coordinator, "test_device", mock_device, time_to_full_desc)
        assert sensor.native_value is None


class TestSensorDescriptionFlags:
    """Test that time sensors have correct flags."""

    def test_time_sensors_always_create_flag(self):
        """Time sensors should have always_create=True."""
        time_to_full = next(s for s in PECRON_SENSORS if s.key == "remain_charging_time")
        time_to_empty = next(s for s in PECRON_SENSORS if s.key == "remain_discharging_time")

        assert time_to_full.always_create is True
        assert time_to_empty.always_create is True

    def test_time_sensors_smart_availability_flag(self):
        """Time sensors should have smart_availability=True."""
        time_to_full = next(s for s in PECRON_SENSORS if s.key == "remain_charging_time")
        time_to_empty = next(s for s in PECRON_SENSORS if s.key == "remain_discharging_time")

        assert time_to_full.smart_availability is True
        assert time_to_empty.smart_availability is True

    def test_other_sensors_dont_have_flags(self):
        """Other sensors should not have these flags set."""
        battery_sensor = next(s for s in PECRON_SENSORS if s.key == "battery_percentage")

        assert battery_sensor.always_create is False
        assert battery_sensor.smart_availability is False
