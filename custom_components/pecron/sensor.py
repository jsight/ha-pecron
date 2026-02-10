"""Sensor platform for Pecron integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
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
class PecronSensorDescription:
    """Describe a Pecron sensor."""

    key: str
    name: str
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    unit: str | None = None
    icon: str | None = None

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
        unit="%",
    ),
    PecronSensorDescription(
        key="total_input_power",
        name="Input Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
    ),
    PecronSensorDescription(
        key="total_output_power",
        name="Output Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
    ),
    PecronSensorDescription(
        key="remain_charging_time",
        name="Time to Full",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
    ),
    PecronSensorDescription(
        key="remain_discharging_time",
        name="Time to Empty",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for Pecron."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    if coordinator.data:
        for device_key, device_data in coordinator.data.items():
            for sensor_desc in PECRON_SENSORS:
                sensors.append(
                    PecronSensor(
                        coordinator,
                        device_key,
                        device_data["device"],
                        sensor_desc,
                    )
                )

    async_add_entities(sensors)


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
        self._attr_device_class = entity_description.device_class
        self._attr_state_class = entity_description.state_class
        self._attr_native_unit_of_measurement = entity_description.unit
        self._attr_icon = entity_description.icon

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
        return getattr(props, self.entity_description.key, None)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
