"""Binary sensor platform for Pecron integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class PecronBinarySensorDescription:
    """Describe a Pecron binary sensor."""

    key: str
    name: str
    device_class: BinarySensorDeviceClass | None = None
    icon_true: str | None = None
    icon_false: str | None = None

    def __post_init__(self) -> None:
        """Post init."""
        if not self.icon_true:
            match self.device_class:
                case BinarySensorDeviceClass.CONNECTIVITY:
                    self.icon_true = "mdi:check-circle"
                    self.icon_false = "mdi:close-circle"
                case _:
                    self.icon_true = "mdi:toggle-switch"
                    self.icon_false = "mdi:toggle-switch-off"


PECRON_BINARY_SENSORS = [
    PecronBinarySensorDescription(
        key="ac_switch",
        name="AC Output",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    PecronBinarySensorDescription(
        key="dc_switch",
        name="DC Output",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    PecronBinarySensorDescription(
        key="ups_status",
        name="UPS Mode",
        icon_true="mdi:uninterruptible-power-supply",
        icon_false="mdi:power-plug-off",
    ),
    PecronBinarySensorDescription(
        key="online",
        name="Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors for Pecron."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    binary_sensors = []
    if coordinator.data:
        for device_key, device_data in coordinator.data.items():
            for sensor_desc in PECRON_BINARY_SENSORS:
                binary_sensors.append(
                    PecronBinarySensor(
                        coordinator,
                        device_key,
                        device_data["device"],
                        sensor_desc,
                    )
                )

    async_add_entities(binary_sensors)


class PecronBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Pecron binary sensor."""

    entity_description: PecronBinarySensorDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_key: str,
        device: Any,
        entity_description: PecronBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._device_key = device_key
        self._device = device

        self._attr_unique_id = f"{DOMAIN}_{device_key}_{entity_description.key}"
        self._attr_name = f"{device.device_name} {entity_description.name}"
        self._attr_device_class = entity_description.device_class

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
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        if not self.coordinator.data or self._device_key not in self.coordinator.data:
            return None

        data = self.coordinator.data[self._device_key]

        # Special handling for online status from device object
        if self.entity_description.key == "online":
            return data["device"].online

        # Get from properties
        props = data["properties"]
        value = getattr(props, self.entity_description.key, None)
        return value

    @property
    def icon(self) -> str | None:
        """Return the icon of the binary sensor."""
        is_on = self.is_on
        if is_on is None:
            return None
        if is_on:
            return self.entity_description.icon_true
        return self.entity_description.icon_false

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
