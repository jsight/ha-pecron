"""Sensor platform for Pecron integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricPotential, UnitOfEnergy, UnitOfFrequency, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_DEVICE_KEY,
    ATTR_FIRMWARE_VERSION,
    ATTR_PRODUCT_KEY,
    ATTR_PRODUCT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class PecronSensorDescription(SensorEntityDescription):
    """Describe a Pecron sensor."""

    def __post_init__(self) -> None:
        """Post init."""
        if not self.icon:
            match self.device_class:
                case SensorDeviceClass.BATTERY:
                    self.icon = "mdi:battery"
                case SensorDeviceClass.POWER:
                    self.icon = "mdi:flash"
                case SensorDeviceClass.VOLTAGE:
                    self.icon = "mdi:sine-wave"
                case _:
                    self.icon = "mdi:gauge"


PECRON_SENSORS = [
    PecronSensorDescription(
        key="battery_percentage",
        name="Battery Percentage",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
    ),
    PecronSensorDescription(
        key="total_input_power",
        name="Input Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    PecronSensorDescription(
        key="total_output_power",
        name="Output Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    PecronSensorDescription(
        key="remain_charging_time",
        name="Time to Full",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    PecronSensorDescription(
        key="remain_discharging_time",
        name="Time to Empty",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for Pecron."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track which devices we've created entities for
    known_device_keys: set[str] = set()

    def create_sensors_for_device(device_key: str, device_data: dict) -> list:
        """Create all sensor entities for a device."""
        sensors = []
        for sensor_desc in PECRON_SENSORS:
            sensors.append(
                PecronSensor(
                    coordinator,
                    device_key,
                    device_data["device"],
                    sensor_desc,
                )
            )
        return sensors

    # Create initial sensors
    sensors = []
    if coordinator.data is not None:
        for device_key, device_data in coordinator.data.items():
            sensors.extend(create_sensors_for_device(device_key, device_data))
            known_device_keys.add(device_key)

        if not sensors:
            _LOGGER.warning(
                "No Pecron devices with valid data found. Check that your account has devices and they are online."
            )

    async_add_entities(sensors)

    # Add listener for new devices
    def check_for_new_devices() -> None:
        """Check for new devices and add entities for them."""
        if not coordinator.data:
            return

        new_device_keys = set(coordinator.data.keys()) - known_device_keys
        if new_device_keys:
            _LOGGER.info("Adding sensors for %d new device(s)", len(new_device_keys))
            new_sensors = []
            for device_key in new_device_keys:
                device_data = coordinator.data[device_key]
                new_sensors.extend(create_sensors_for_device(device_key, device_data))
                known_device_keys.add(device_key)

            if new_sensors:
                async_add_entities(new_sensors)

    # Register the listener
    entry.async_on_unload(coordinator.async_add_listener(check_for_new_devices))


class PecronSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Pecron sensor."""

    entity_description: PecronSensorDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_key: str,
        device: Any,
        entity_description: PecronSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._device_key = device_key
        self._device = device

        self._attr_unique_id = f"{DOMAIN}_{device_key}_{entity_description.key}"
        self._attr_name = f"{device.device_name} {entity_description.name}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device_key)},
            "name": self._device.device_name,
            "manufacturer": "Pecron",
            "model": self._device.product_name,
            "hw_version": self._device.device_key,
        }

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data or self._device_key not in self.coordinator.data:
            return None

        props = self.coordinator.data[self._device_key]["properties"]
        value = getattr(props, self.entity_description.key, None)

        if value is None and not hasattr(props, self.entity_description.key):
            _LOGGER.debug(
                "Property '%s' not found for device %s. Available: %s",
                self.entity_description.key,
                self._device.device_name,
                dir(props) if hasattr(props, "__dir__") else "unknown",
            )

        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
