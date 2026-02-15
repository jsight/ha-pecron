"""Switch platform for Pecron integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
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
class PecronSwitchDescription(SwitchEntityDescription):
    """Describe a Pecron switch."""

    api_method: str | None = None


PECRON_SWITCHES = [
    PecronSwitchDescription(
        key="ac_switch",
        name="AC Output",
        device_class=SwitchDeviceClass.OUTLET,
        api_method="set_ac_output",
        icon="mdi:power-socket-us",
    ),
    PecronSwitchDescription(
        key="dc_switch",
        name="DC Output",
        device_class=SwitchDeviceClass.OUTLET,
        api_method="set_dc_output",
        icon="mdi:power-socket-dc",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches for Pecron."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track which devices we've created entities for
    known_device_keys: set[str] = set()

    def create_switches_for_device(device_key: str, device_data: dict) -> list:
        """Create all switch entities for a device."""
        switches = []
        tsl = device_data.get("tsl")

        # If TSL is available, filter switches based on supported properties
        if tsl:
            tsl_property_codes = {prop.code for prop in tsl}
            _LOGGER.debug(
                "Filtering switches for %s based on TSL with %d properties",
                device_data["device"].device_name,
                len(tsl_property_codes),
            )

            for switch_desc in PECRON_SWITCHES:
                # Check both the property name and the _hm variant
                # (API maps ac_switch_hm -> ac_switch in properties)
                if switch_desc.key in tsl_property_codes or f"{switch_desc.key}_hm" in tsl_property_codes:
                    switches.append(
                        PecronSwitch(
                            coordinator,
                            device_key,
                            device_data["device"],
                            switch_desc,
                        )
                    )
                else:
                    _LOGGER.debug(
                        "Skipping switch '%s' for %s - not in TSL (checked '%s' and '%s_hm')",
                        switch_desc.key,
                        device_data["device"].device_name,
                        switch_desc.key,
                        switch_desc.key,
                    )
        else:
            # Fallback: create all switches if TSL is not available
            _LOGGER.debug(
                "TSL not available for %s - creating all switches",
                device_data["device"].device_name,
            )
            for switch_desc in PECRON_SWITCHES:
                switches.append(
                    PecronSwitch(
                        coordinator,
                        device_key,
                        device_data["device"],
                        switch_desc,
                    )
                )

        return switches

    # Create initial switches
    switches = []
    if coordinator.data is not None:
        for device_key, device_data in coordinator.data.items():
            switches.extend(create_switches_for_device(device_key, device_data))
            known_device_keys.add(device_key)

        if not switches:
            _LOGGER.warning(
                "No Pecron devices with valid data found. Check that your account has devices and they are online."
            )

    async_add_entities(switches)

    # Add listener for new devices
    def check_for_new_devices() -> None:
        """Check for new devices and add entities for them."""
        if not coordinator.data:
            return

        new_device_keys = set(coordinator.data.keys()) - known_device_keys
        if new_device_keys:
            _LOGGER.info("Adding switches for %d new device(s)", len(new_device_keys))
            new_switches = []
            for device_key in new_device_keys:
                device_data = coordinator.data[device_key]
                new_switches.extend(create_switches_for_device(device_key, device_data))
                known_device_keys.add(device_key)

            if new_switches:
                async_add_entities(new_switches)

    # Register the listener
    entry.async_on_unload(coordinator.async_add_listener(check_for_new_devices))


class PecronSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Pecron switch."""

    entity_description: PecronSwitchDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_key: str,
        device: Any,
        entity_description: PecronSwitchDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._device_key = device_key
        self._device = device
        self._attr_is_on = None  # Will be set from coordinator data

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
        """Return the state of the switch."""
        # Return optimistic state if set, otherwise read from coordinator
        if self._attr_is_on is not None:
            return self._attr_is_on

        if not self.coordinator.data or self._device_key not in self.coordinator.data:
            return None

        data = self.coordinator.data[self._device_key]
        props = data["properties"]
        value = getattr(props, self.entity_description.key, None)

        if value is None and not hasattr(props, self.entity_description.key):
            _LOGGER.debug(
                "Property '%s' not found for device %s",
                self.entity_description.key,
                data["device"].device_name,
            )

        return value

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_state(False)

    async def _async_set_state(self, enabled: bool) -> None:
        """Set the switch state."""
        api = self.coordinator.api
        if api is None:
            _LOGGER.error("API not available for %s", self._attr_name)
            self.hass.components.persistent_notification.async_create(
                f"Failed to control {self._attr_name}: API not initialized",
                title="Pecron: Control Failed",
                notification_id=f"{DOMAIN}_control_failed_{self._attr_unique_id}",
            )
            return

        # Get the API method to call
        method_name = self.entity_description.api_method
        if not method_name:
            _LOGGER.error("No API method defined for %s", self._attr_name)
            return

        method = getattr(api, method_name, None)
        if not method:
            _LOGGER.error("API method %s not found", method_name)
            return

        # Optimistic update: Set state immediately for instant UI feedback
        old_state = self._attr_is_on
        self._attr_is_on = enabled
        self.async_write_ha_state()

        try:
            # Call the API method in executor
            result = await self.hass.async_add_executor_job(
                method, self._device, enabled
            )

            if not result.success:
                _LOGGER.error(
                    "Failed to %s %s: %s",
                    "enable" if enabled else "disable",
                    self._attr_name,
                    result.message or "Unknown error",
                )
                # Revert optimistic update on failure
                self._attr_is_on = old_state
                self.async_write_ha_state()
                self.hass.components.persistent_notification.async_create(
                    f"Failed to {'turn on' if enabled else 'turn off'} {self._attr_name}: "
                    f"{result.message or 'Unknown error'}",
                    title="Pecron: Control Failed",
                    notification_id=f"{DOMAIN}_control_failed_{self._attr_unique_id}",
                )
            else:
                _LOGGER.info(
                    "Successfully %s %s",
                    "enabled" if enabled else "disabled",
                    self._attr_name,
                )
                # Request immediate refresh
                await self.coordinator.async_request_refresh()

                # Schedule additional refreshes at 5s and 15s to ensure UI syncs
                # (Device may take time to actually change state)
                async def delayed_refresh(delay: int) -> None:
                    """Refresh coordinator after delay."""
                    await asyncio.sleep(delay)
                    _LOGGER.debug(
                        "Delayed refresh (%ds) for %s after state change",
                        delay,
                        self._attr_name,
                    )
                    await self.coordinator.async_request_refresh()

                # Create background tasks for delayed refreshes
                asyncio.create_task(delayed_refresh(5))
                asyncio.create_task(delayed_refresh(15))

        except Exception as err:
            _LOGGER.error(
                "Error controlling %s: %s",
                self._attr_name,
                err,
                exc_info=True,
            )
            # Revert optimistic update on error
            self._attr_is_on = old_state
            self.async_write_ha_state()
            self.hass.components.persistent_notification.async_create(
                f"Error controlling {self._attr_name}: {err}",
                title="Pecron: Control Error",
                notification_id=f"{DOMAIN}_control_error_{self._attr_unique_id}",
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear optimistic state and use real state from coordinator
        self._attr_is_on = None
        self.async_write_ha_state()
