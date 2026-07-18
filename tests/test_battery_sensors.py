"""Tests for battery electrical measurement sensors."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
)

from custom_components.pecron.const import DOMAIN
from custom_components.pecron.sensor import PECRON_SENSORS, PecronSensor, async_setup_entry


def _sensor_description(key: str):
    """Return the description for a sensor key."""
    return next(description for description in PECRON_SENSORS if description.key == key)


def _sensor_with_battery_pack(battery_pack: dict | None) -> tuple[MagicMock, MagicMock]:
    """Create a battery sensor whose coordinator reports a battery packet."""
    device = MagicMock(
        device_key="test_device", device_name="Test Device", product_name="Test Product"
    )
    properties = SimpleNamespace(battery_pack=battery_pack)
    coordinator = MagicMock(data={"test_device": {"device": device, "properties": properties}})
    return coordinator, device


def test_battery_voltage_sensor_metadata_and_value() -> None:
    """Battery voltage is exposed as a voltage measurement in volts."""
    description = _sensor_description("battery_voltage")

    assert description.device_class is SensorDeviceClass.VOLTAGE
    assert description.state_class is SensorStateClass.MEASUREMENT
    assert description.native_unit_of_measurement == UnitOfElectricPotential.VOLT
    assert description.suggested_display_precision == 2
    assert description.tsl_property == "host_packet_data_jdb"
    assert description.struct_property == "battery_pack"
    assert description.struct_field == "host_packet_voltage"

    coordinator, device = _sensor_with_battery_pack({"host_packet_voltage": "51.2"})
    sensor = PecronSensor(coordinator, "test_device", device, description)
    assert sensor.native_value == 51.2


def test_battery_current_sensor_metadata_and_value() -> None:
    """Battery current is exposed as a current measurement in amperes."""
    description = _sensor_description("battery_current")

    assert description.device_class is SensorDeviceClass.CURRENT
    assert description.state_class is SensorStateClass.MEASUREMENT
    assert description.native_unit_of_measurement == UnitOfElectricCurrent.AMPERE
    assert description.tsl_property == "host_packet_data_jdb"
    assert description.struct_property == "battery_pack"
    assert description.struct_field == "host_packet_current"

    coordinator, device = _sensor_with_battery_pack({"host_packet_current": "-12.5"})
    sensor = PecronSensor(coordinator, "test_device", device, description)
    assert sensor.native_value == -12.5


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        ("10", 512.0),
        ("-12.5", -640.0),
        ("0", 0.0),
    ],
)
def test_battery_power_sensor_metadata_and_signed_value(current: str, expected: float) -> None:
    """Battery power is voltage times signed current in watts."""
    description = _sensor_description("battery_power")

    assert description.device_class is SensorDeviceClass.POWER
    assert description.state_class is SensorStateClass.MEASUREMENT
    assert description.native_unit_of_measurement == UnitOfPower.WATT
    assert description.suggested_display_precision == 1
    assert description.tsl_property == "host_packet_data_jdb"
    assert description.struct_property == "battery_pack"

    coordinator, device = _sensor_with_battery_pack(
        {"host_packet_voltage": "51.2", "host_packet_current": current}
    )
    sensor = PecronSensor(coordinator, "test_device", device, description)

    assert sensor.native_value == expected


@pytest.mark.parametrize(
    "battery_pack",
    [
        None,
        {},
        {"host_packet_voltage": "51.2"},
        {"host_packet_current": "10"},
        {"host_packet_voltage": None, "host_packet_current": "10"},
        {"host_packet_voltage": "invalid", "host_packet_current": "10"},
        {"host_packet_voltage": "51.2", "host_packet_current": "invalid"},
        {"host_packet_voltage": "nan", "host_packet_current": "10"},
        {"host_packet_voltage": "51.2", "host_packet_current": "inf"},
    ],
)
def test_battery_power_sensor_handles_missing_and_invalid_values(
    battery_pack: dict | None,
) -> None:
    """Battery power is unavailable unless voltage and current are numeric."""
    description = _sensor_description("battery_power")
    coordinator, device = _sensor_with_battery_pack(battery_pack)
    sensor = PecronSensor(coordinator, "test_device", device, description)

    assert sensor.native_value is None


def test_battery_temperature_sensor_metadata_and_value() -> None:
    """Battery temperature is exposed as a temperature measurement in Celsius."""
    description = _sensor_description("battery_temperature")

    assert description.device_class is SensorDeviceClass.TEMPERATURE
    assert description.state_class is SensorStateClass.MEASUREMENT
    assert description.native_unit_of_measurement == UnitOfTemperature.CELSIUS
    assert description.tsl_property == "host_packet_data_jdb"
    assert description.struct_property == "battery_pack"
    assert description.struct_field == "host_packet_temp"

    coordinator, device = _sensor_with_battery_pack({"host_packet_temp": "31.5"})
    sensor = PecronSensor(coordinator, "test_device", device, description)
    assert sensor.native_value == 31.5


@pytest.mark.parametrize(
    ("battery_pack", "expected"),
    [
        (None, None),
        ({}, None),
        ({"host_packet_voltage": None}, None),
        ({"host_packet_voltage": "not-a-number"}, None),
        ({"host_packet_voltage": "24"}, 24),
    ],
)
def test_battery_sensor_handles_missing_and_invalid_values(
    battery_pack: dict | None, expected: int | None
) -> None:
    """Missing or invalid battery pack telemetry produces an unavailable value."""
    description = _sensor_description("battery_voltage")
    coordinator, device = _sensor_with_battery_pack(battery_pack)
    sensor = PecronSensor(coordinator, "test_device", device, description)

    assert sensor.native_value == expected


@pytest.mark.asyncio
async def test_battery_sensors_created_from_battery_packet_tsl() -> None:
    """Battery sensors are created when the device TSL exposes the battery packet."""
    device = MagicMock(
        device_key="test_device",
        device_name="Test Device",
        product_name="Test Product",
    )
    coordinator = MagicMock(
        data={
            "test_device": {
                "device": device,
                "properties": SimpleNamespace(
                    battery_pack={
                        "host_packet_voltage": "51.2",
                        "host_packet_current": "-12.5",
                    }
                ),
                "tsl": [SimpleNamespace(code="host_packet_data_jdb")],
            }
        }
    )
    entry = MagicMock(entry_id="test_entry")
    hass = MagicMock(data={DOMAIN: {entry.entry_id: coordinator}})
    async_add_entities = MagicMock()

    await async_setup_entry(hass, entry, async_add_entities)

    sensors = async_add_entities.call_args.args[0]
    sensor_keys = {sensor.entity_description.key for sensor in sensors}
    assert "battery_voltage" in sensor_keys
    assert "battery_current" in sensor_keys
    assert "battery_power" in sensor_keys
    assert "battery_temperature" in sensor_keys
