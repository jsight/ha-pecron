"""Config flow for Pecron integration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from unofficial_pecron_api import PecronAPI

from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_REGION,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_REGION,
    DOMAIN,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)


class PecronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pecron."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PecronOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(
                    self._validate_pecron_credentials,
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                    user_input.get(CONF_REGION, DEFAULT_REGION),
                )
            except PecronAuthError as err:
                _LOGGER.error("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except PecronConnectionError as err:
                _LOGGER.error("Connection failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_REGION, default=DEFAULT_REGION): vol.In(REGIONS),
                vol.Optional(
                    CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Import configuration from YAML."""
        return await self.async_step_user(import_data)

    @staticmethod
    def _validate_pecron_credentials(email: str, password: str, region: str) -> None:
        """Validate Pecron credentials."""
        try:
            api = PecronAPI(region=region)
            api.login(email, password)
            devices = api.get_devices()
            api.close()

            if not devices:
                raise PecronAuthError("No devices found on account")
        except Exception as err:
            if "authentication" in str(err).lower() or "401" in str(err):
                raise PecronAuthError(str(err)) from err
            raise PecronConnectionError(str(err)) from err


class PecronOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Pecron integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_refresh = self.config_entry.options.get(
            CONF_REFRESH_INTERVAL,
            self.config_entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=current_refresh,
                ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)


class PecronAuthError(HomeAssistantError):
    """Pecron authentication error."""


class PecronConnectionError(HomeAssistantError):
    """Pecron connection error."""
