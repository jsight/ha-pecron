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


# TSL code -> (HA property key, select description defaults)
_TSL_SELECT_DEFS = {
    "ac_charging_power_ios": {
        "key": "ac_charge_speed",
        "name": "AC Charge Speed",
        "api_method": "set_ac_charge_speed",
        "icon": "mdi:battery-charging",
    },
}

# Fallback options when TSL specs are unavailable (E300LFP defaults)
_FALLBACK_OPTIONS = {
    "ac_charge_speed": {
        "options": ["0%", "25%", "50%", "75%", "100%"],
        "option_map": {"0%": "0", "25%": "1", "50%": "2", "75%": "3", "100%": "4"},
        "value_to_label": {"0": "0%", "1": "25%", "2": "50%", "3": "75%", "4": "100%"},
    },
}


def _build_select_from_tsl(tsl_prop) -> tuple[PecronSelectDescription, dict[str, str]] | None:
    """Build a PecronSelectDescription from a TSL property with enum specs."""
    defn = _TSL_SELECT_DEFS.get(tsl_prop.code)
    if defn is None:
        return None

    if tsl_prop.enum_values:
        options = [f"{ev.name}%" for ev in tsl_prop.enum_values]
        option_map = {f"{ev.name}%": str(ev.value) for ev in tsl_prop.enum_values}
        value_to_label = {str(ev.value): f"{ev.name}%" for ev in tsl_prop.enum_values}
    else:
        # TSL property exists but has no enum specs — use fallback
        fb = _FALLBACK_OPTIONS[defn["key"]]
        options = fb["options"]
        option_map = fb["option_map"]
        value_to_label = fb["value_to_label"]

    return PecronSelectDescription(
        key=defn["key"],
        name=defn["name"],
        api_method=defn["api_method"],
        icon=defn["icon"],
        options=options,
        option_map=option_map,
    ), value_to_label


def _build_fallback_selects() -> list[tuple[PecronSelectDescription, dict[str, str]]]:
    """Build select descriptions using hardcoded fallback options (no TSL available)."""
    result = []
    for defn in _TSL_SELECT_DEFS.values():
        fb = _FALLBACK_OPTIONS[defn["key"]]
        desc = PecronSelectDescription(
            key=defn["key"],
            name=defn["name"],
            api_method=defn["api_method"],
            icon=defn["icon"],
            options=fb["options"],
            option_map=fb["option_map"],
        )
        result.append((desc, fb["value_to_label"]))
    return result


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
            tsl_by_code = {prop.code: prop for prop in tsl}
            _LOGGER.debug(
                "Filtering selects for %s based on TSL with %d properties",
                device_data["device"].device_name,
                len(tsl_by_code),
            )

            for tsl_code in _TSL_SELECT_DEFS:
                tsl_prop = tsl_by_code.get(tsl_code)
                if tsl_prop is None:
                    _LOGGER.debug(
                        "Skipping select for TSL code '%s' on %s - not in TSL",
                        tsl_code,
                        device_data["device"].device_name,
                    )
                    continue

                result = _build_select_from_tsl(tsl_prop)
                if result:
                    select_desc, value_to_label = result
                    selects.append(
                        PecronSelect(
                            coordinator,
                            device_key,
                            device_data["device"],
                            select_desc,
                            value_to_label,
                        )
                    )
        else:
            # Fallback: create all selects if TSL is not available
            _LOGGER.debug(
                "TSL not available for %s - creating all selects",
                device_data["device"].device_name,
            )
            for select_desc, value_to_label in _build_fallback_selects():
                selects.append(
                    PecronSelect(
                        coordinator,
                        device_key,
                        device_data["device"],
                        select_desc,
                        value_to_label,
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
        value_to_label: dict[str, str],
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._device_key = device_key
        self._device = device
        self._value_to_label = value_to_label
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

        return self._value_to_label.get(str(value), str(value))

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
