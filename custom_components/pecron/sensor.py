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

    always_create: bool = False  # Bypass TSL filtering
    smart_availability: bool = False  # Use smart logic for availability

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
        always_create=True,
        smart_availability=True,
    ),
    PecronSensorDescription(
        key="remain_discharging_time",
        name="Time to Empty",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        always_create=True,
        smart_availability=True,
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
        tsl = device_data.get("tsl")

        # If TSL is available, filter sensors based on supported properties
        if tsl:
            tsl_property_codes = {prop.code for prop in tsl}
            _LOGGER.debug(
                "Filtering sensors for %s based on TSL with %d properties",
                device_data["device"].device_name,
                len(tsl_property_codes),
            )

            for sensor_desc in PECRON_SENSORS:
                # Always create sensors marked with always_create flag
                # Otherwise check both property name and _hm variant (API maps xxx_hm -> xxx)
                if (sensor_desc.always_create or
                    sensor_desc.key in tsl_property_codes or
                    f"{sensor_desc.key}_hm" in tsl_property_codes):
                    sensors.append(
                        PecronSensor(
                            coordinator,
                            device_key,
                            device_data["device"],
                            sensor_desc,
                        )
                    )
                else:
                    _LOGGER.debug(
                        "Skipping sensor '%s' for %s - not in TSL (checked '%s' and '%s_hm')",
                        sensor_desc.key,
                        device_data["device"].device_name,
                        sensor_desc.key,
                        sensor_desc.key,
                    )
        else:
            # Fallback: create all sensors if TSL is not available
            _LOGGER.debug(
                "TSL not available for %s - creating all sensors",
                device_data["device"].device_name,
            )
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

        # Smart availability logic for time sensors
        if self.entity_description.smart_availability and value is not None:
            # Get power values to determine device state (handle missing/None/negative)
            input_power = getattr(props, "total_input_power", None)
            output_power = getattr(props, "total_output_power", None)

            # Treat None or negative as 0
            input_power = max(0, input_power) if input_power is not None else 0
            output_power = max(0, output_power) if output_power is not None else 0

            # Determine device state
            is_idle = input_power == 0 and output_power == 0
            is_charging_only = input_power > 0 and output_power == 0
            is_discharging_only = input_power == 0 and output_power > 0
            is_ups_mode = input_power > 0 and output_power > 0

            # Time to Full logic
            if self.entity_description.key == "remain_charging_time":
                if is_discharging_only or is_idle:
                    _LOGGER.debug(
                        "Time to Full N/A for %s - device state: idle=%s discharging=%s",
                        self._device.device_name,
                        is_idle,
                        is_discharging_only,
                    )
                    return None
                # Show value for charging_only or ups_mode

            # Time to Empty logic
            elif self.entity_description.key == "remain_discharging_time":
                if is_charging_only or is_idle:
                    _LOGGER.debug(
                        "Time to Empty N/A for %s - device state: idle=%s charging=%s",
                        self._device.device_name,
                        is_idle,
                        is_charging_only,
                    )
                    return None
                # Show value for discharging_only or ups_mode

        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
