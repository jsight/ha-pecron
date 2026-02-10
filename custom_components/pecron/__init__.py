"""Pecron Home Assistant integration."""

import asyncio
import logging
from datetime import timedelta
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from unofficial_pecron_api import PecronAPI

from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_REGION,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_REGION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS: Final = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pecron from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    region = entry.data.get(CONF_REGION, DEFAULT_REGION)
    refresh_interval = entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)

    coordinator = PecronDataUpdateCoordinator(
        hass, email, password, region, refresh_interval
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok


class PecronDataUpdateCoordinator(DataUpdateCoordinator):
    """Update coordinator for Pecron data."""

    def __init__(
        self,
        hass: HomeAssistant,
        email: str,
        password: str,
        region: str,
        refresh_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        self.email = email
        self.password = password
        self.region = region
        self.api: PecronAPI | None = None
        self.devices = []

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=refresh_interval),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from Pecron API."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_data)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Pecron API: {err}") from err

    def _fetch_data(self) -> dict:
        """Fetch device data from API."""
        if self.api is None:
            _LOGGER.info("Initializing Pecron API connection for region: %s", self.region)
            self.api = PecronAPI(region=self.region)
            self.api.login(self.email, self.password)
            self.devices = self.api.get_devices()
            _LOGGER.info("Found %d Pecron device(s) on account", len(self.devices))

            if not self.devices:
                _LOGGER.warning(
                    "No Pecron devices found on account %s. "
                    "Please check that devices are registered in the Pecron app.",
                    self.email
                )
            else:
                for device in self.devices:
                    _LOGGER.info(
                        "Discovered device: %s (key: %s, product: %s)",
                        device.device_name,
                        device.device_key,
                        getattr(device, "product_name", "unknown"),
                    )

        data = {}
        for device in self.devices:
            try:
                props = self.api.get_device_properties(device)
                data[device.device_key] = {
                    "device": device,
                    "properties": props,
                }
                _LOGGER.debug(
                    "Successfully fetched properties for %s: %s",
                    device.device_name,
                    props,
                )
            except Exception as err:
                _LOGGER.error(
                    "Error fetching properties for %s (key: %s): %s",
                    device.device_name,
                    device.device_key,
                    err,
                    exc_info=True,
                )

        if data:
            _LOGGER.debug("Successfully fetched data for %d device(s)", len(data))
        else:
            _LOGGER.warning("No device data could be fetched")

        return data

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and close API connection."""
        if self.api is not None:
            await self.hass.async_add_executor_job(self.api.close)
            self.api = None
