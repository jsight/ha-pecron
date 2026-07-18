"""Tests for battery electrical measurement sensors."""

from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential

from custom_components.pecron.sensor import PECRON_SENSORS, PecronSensor


def _sensor_description(key: str):
    """Return the description for a sensor key."""
    return next(description for description in PECRON_SENSORS if description.key == key)


def _sensor_with_value(key: str, value: float) -> PecronSensor:
    """Create a sensor whose coordinator reports a battery measurement."""
    device = MagicMock(device_key="test_device", device_name="Test Device", product_name="Test Product")
    properties = MagicMock()
    setattr(properties, key, value)
    coordinator = MagicMock(
        data={"test_device": {"device": device, "properties": properties}}
    )
    return PecronSensor(coordinator, "test_device", device, _sensor_description(key))


def test_battery_voltage_sensor_metadata_and_value() -> None:
    """Battery voltage is exposed as a voltage measurement in volts."""
    description = _sensor_description("battery_voltage")

    assert description.device_class is SensorDeviceClass.VOLTAGE
    assert description.state_class is SensorStateClass.MEASUREMENT
    assert description.native_unit_of_measurement == UnitOfElectricPotential.VOLT
    assert _sensor_with_value("battery_voltage", 51.2).native_value == 51.2


def test_battery_current_sensor_metadata_and_value() -> None:
    """Battery current is exposed as a current measurement in amperes."""
    description = _sensor_description("battery_current")

    assert description.device_class is SensorDeviceClass.CURRENT
    assert description.state_class is SensorStateClass.MEASUREMENT
    assert description.native_unit_of_measurement == UnitOfElectricCurrent.AMPERE
    assert _sensor_with_value("battery_current", -12.5).native_value == -12.5
