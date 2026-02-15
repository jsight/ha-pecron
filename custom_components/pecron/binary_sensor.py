"""Binary sensor platform for Pecron integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
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
class PecronBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Pecron binary sensor."""

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

    # Track which devices we've created entities for
    known_device_keys: set[str] = set()

    def create_binary_sensors_for_device(device_key: str, device_data: dict) -> list:
        """Create all binary sensor entities for a device."""
        sensors = []
        tsl = device_data.get("tsl")

        # If TSL is available, filter sensors based on supported properties
        if tsl:
            tsl_property_codes = {prop.code for prop in tsl}
            _LOGGER.debug(
                "Filtering binary sensors for %s based on TSL with %d properties",
                device_data["device"].device_name,
                len(tsl_property_codes),
            )

            for sensor_desc in PECRON_BINARY_SENSORS:
                # Special case: 'online' is from device object, not TSL
                # Check both property name and _hm variant (API maps xxx_hm -> xxx)
                if (sensor_desc.key == "online" or
                    sensor_desc.key in tsl_property_codes or
                    f"{sensor_desc.key}_hm" in tsl_property_codes):
                    sensors.append(
                        PecronBinarySensor(
                            coordinator,
                            device_key,
                            device_data["device"],
                            sensor_desc,
                        )
                    )
                else:
                    _LOGGER.debug(
                        "Skipping binary sensor '%s' for %s - not in TSL (checked '%s' and '%s_hm')",
                        sensor_desc.key,
                        device_data["device"].device_name,
                        sensor_desc.key,
                        sensor_desc.key,
                    )
        else:
            # Fallback: create all sensors if TSL is not available
            _LOGGER.debug(
                "TSL not available for %s - creating all binary sensors",
                device_data["device"].device_name,
            )
            for sensor_desc in PECRON_BINARY_SENSORS:
                sensors.append(
                    PecronBinarySensor(
                        coordinator,
                        device_key,
                        device_data["device"],
                        sensor_desc,
                    )
                )

        return sensors

    # Create initial binary sensors
    binary_sensors = []
    if coordinator.data is not None:
        for device_key, device_data in coordinator.data.items():
            binary_sensors.extend(create_binary_sensors_for_device(device_key, device_data))
            known_device_keys.add(device_key)

        if not binary_sensors:
            _LOGGER.warning(
                "No Pecron devices with valid data found. Check that your account has devices and they are online."
            )

    async_add_entities(binary_sensors)

    # Add listener for new devices
    def check_for_new_devices() -> None:
        """Check for new devices and add entities for them."""
        if not coordinator.data:
            return

        new_device_keys = set(coordinator.data.keys()) - known_device_keys
        if new_device_keys:
            _LOGGER.info("Adding binary sensors for %d new device(s)", len(new_device_keys))
            new_sensors = []
            for device_key in new_device_keys:
                device_data = coordinator.data[device_key]
                new_sensors.extend(create_binary_sensors_for_device(device_key, device_data))
                known_device_keys.add(device_key)

            if new_sensors:
                async_add_entities(new_sensors)

    # Register the listener
    entry.async_on_unload(coordinator.async_add_listener(check_for_new_devices))


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

        if value is None and not hasattr(props, self.entity_description.key):
            _LOGGER.debug(
                "Property '%s' not found for device %s. Available: %s",
                self.entity_description.key,
                data["device"].device_name,
                dir(props) if hasattr(props, "__dir__") else "unknown",
            )

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
