"""Select platform for Pecron integration."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class PecronSelectDescription(SelectEntityDescription):
    """Describe a Pecron select entity."""

    api_method: str | None = None
    option_map: dict[str, str] = field(default_factory=dict)


PECRON_SELECTS = [
    PecronSelectDescription(
        key="ac_charge_speed",
        name="AC Charge Speed",
        api_method="set_ac_charge_speed",
        icon="mdi:battery-charging",
        # TSL code is ac_charging_power_ios; mapped to ac_charge_speed on DeviceProperties
        options=["10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"],
        option_map={
            "10%": "1",
            "20%": "2",
            "30%": "3",
            "40%": "4",
            "50%": "5",
            "60%": "6",
            "70%": "7",
            "80%": "8",
            "90%": "9",
            "100%": "10",
        },
    ),
]

# Reverse map: API value -> display label
_VALUE_TO_LABEL = {
    "1": "10%",
    "2": "20%",
    "3": "30%",
    "4": "40%",
    "5": "50%",
    "6": "60%",
    "7": "70%",
    "8": "80%",
    "9": "90%",
    "10": "100%",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities for Pecron."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track which devices we've created entities for
    known_device_keys: set[str] = set()

    def create_selects_for_device(device_key: str, device_data: dict) -> list:
        """Create all select entities for a device."""
        selects = []
        tsl = device_data.get("tsl")

        if tsl:
            tsl_property_codes = {prop.code for prop in tsl}
            _LOGGER.debug(
                "Filtering selects for %s based on TSL with %d properties",
                device_data["device"].device_name,
                len(tsl_property_codes),
            )

            for select_desc in PECRON_SELECTS:
                # ac_charge_speed maps to ac_charging_power_ios in the TSL
                tsl_code = "ac_charging_power_ios" if select_desc.key == "ac_charge_speed" else select_desc.key
                if (tsl_code in tsl_property_codes or
                        f"{tsl_code}_hm" in tsl_property_codes or
                        select_desc.key in tsl_property_codes or
                        f"{select_desc.key}_hm" in tsl_property_codes):
                    selects.append(
                        PecronSelect(
                            coordinator,
                            device_key,
                            device_data["device"],
                            select_desc,
                        )
                    )
                else:
                    _LOGGER.debug(
                        "Skipping select '%s' for %s - not in TSL",
                        select_desc.key,
                        device_data["device"].device_name,
                    )
        else:
            # Fallback: create all selects if TSL is not available
            _LOGGER.debug(
                "TSL not available for %s - creating all selects",
                device_data["device"].device_name,
            )
            for select_desc in PECRON_SELECTS:
                selects.append(
                    PecronSelect(
                        coordinator,
                        device_key,
                        device_data["device"],
                        select_desc,
                    )
                )

        return selects

    # Create initial selects
    selects = []
    if coordinator.data is not None:
        for device_key, device_data in coordinator.data.items():
            selects.extend(create_selects_for_device(device_key, device_data))
            known_device_keys.add(device_key)

    async_add_entities(selects)

    # Add listener for new devices
    def check_for_new_devices() -> None:
        """Check for new devices and add entities for them."""
        if not coordinator.data:
            return

        new_device_keys = set(coordinator.data.keys()) - known_device_keys
        if new_device_keys:
            _LOGGER.info("Adding selects for %d new device(s)", len(new_device_keys))
            new_selects = []
            for device_key in new_device_keys:
                device_data = coordinator.data[device_key]
                new_selects.extend(create_selects_for_device(device_key, device_data))
                known_device_keys.add(device_key)

            if new_selects:
                async_add_entities(new_selects)

    # Register the listener
    entry.async_on_unload(coordinator.async_add_listener(check_for_new_devices))


class PecronSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Pecron select entity."""

    entity_description: PecronSelectDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_key: str,
        device: Any,
        entity_description: PecronSelectDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._device_key = device_key
        self._device = device
        self._attr_current_option = None
        self._last_change_time = None

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
    def current_option(self) -> str | None:
        """Return the current selected option."""
        # Return optimistic state if set
        if self._attr_current_option is not None:
            return self._attr_current_option

        if not self.coordinator.data or self._device_key not in self.coordinator.data:
            return None

        props = self.coordinator.data[self._device_key]["properties"]
        value = getattr(props, self.entity_description.key, None)

        if value is None:
            return None

        return _VALUE_TO_LABEL.get(str(value), str(value))

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        api = self.coordinator.api
        if api is None:
            _LOGGER.error("API not available for %s", self._attr_name)
            self.hass.components.persistent_notification.async_create(
                f"Failed to control {self._attr_name}: API not initialized",
                title="Pecron: Control Failed",
                notification_id=f"{DOMAIN}_control_failed_{self._attr_unique_id}",
            )
            return

        method_name = self.entity_description.api_method
        if not method_name:
            _LOGGER.error("No API method defined for %s", self._attr_name)
            return

        method = getattr(api, method_name, None)
        if not method:
            _LOGGER.error("API method %s not found", method_name)
            return

        # Convert display label to API value
        api_value = self.entity_description.option_map.get(option, option)

        # Optimistic update
        old_option = self._attr_current_option
        self._attr_current_option = option
        self._last_change_time = time.time()
        self.async_write_ha_state()

        try:
            result = await self.hass.async_add_executor_job(
                method, self._device, api_value
            )

            if not result.success:
                _LOGGER.error(
                    "Failed to set %s to %s: %s",
                    self._attr_name,
                    option,
                    result.error_message or "Unknown error",
                )
                self._attr_current_option = old_option
                self.async_write_ha_state()
                self.hass.components.persistent_notification.async_create(
                    f"Failed to set {self._attr_name} to {option}: "
                    f"{result.error_message or 'Unknown error'}",
                    title="Pecron: Control Failed",
                    notification_id=f"{DOMAIN}_control_failed_{self._attr_unique_id}",
                )
            else:
                _LOGGER.info("Successfully set %s to %s", self._attr_name, option)
                await self.coordinator.async_request_refresh()

                async def delayed_refresh(delay: int) -> None:
                    """Refresh coordinator after delay."""
                    await asyncio.sleep(delay)
                    await self.coordinator.async_request_refresh()

                asyncio.create_task(delayed_refresh(5))
                asyncio.create_task(delayed_refresh(15))

        except Exception as err:
            _LOGGER.error(
                "Error controlling %s: %s",
                self._attr_name,
                err,
                exc_info=True,
            )
            self._attr_current_option = old_option
            self.async_write_ha_state()
            self.hass.components.persistent_notification.async_create(
                f"Error controlling {self._attr_name}: {err}",
                title="Pecron: Control Error",
                notification_id=f"{DOMAIN}_control_error_{self._attr_unique_id}",
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._last_change_time is None or (time.time() - self._last_change_time) >= 20:
            self._attr_current_option = None
        else:
            _LOGGER.debug(
                "Ignoring coordinator update for %s (%.1fs since change, waiting for device to settle)",
                self._attr_name,
                time.time() - self._last_change_time,
            )
        self.async_write_ha_state()
