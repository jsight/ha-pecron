"""Config flow for Pecron integration."""

import logging
from typing import Any

import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from unofficial_pecron_api import PecronAPI
from unofficial_pecron_api.exceptions import AuthenticationError

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


def _minutes_to_seconds(minutes: int | float) -> int:
    """Convert a user-facing refresh interval in minutes to seconds."""
    return round(minutes * 60)


def _seconds_to_minutes(seconds: int) -> float:
    """Convert a stored refresh interval in seconds to minutes."""
    return seconds / 60


class PecronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pecron."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PecronOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
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
                entry_data = dict(user_input)
                entry_data[CONF_REFRESH_INTERVAL] = _minutes_to_seconds(
                    entry_data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL / 60)
                )
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data=entry_data,
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_REGION, default=DEFAULT_REGION): vol.In(REGIONS),
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=DEFAULT_REFRESH_INTERVAL / 60,
                ): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=60)
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Import configuration from YAML."""
        import_data = dict(import_data)
        if CONF_REFRESH_INTERVAL in import_data:
            # Older imports used the integration's internal unit: seconds.
            import_data[CONF_REFRESH_INTERVAL] = _seconds_to_minutes(
                int(import_data[CONF_REFRESH_INTERVAL])
            )
        return await self.async_step_user(import_data)

    @staticmethod
    def _validate_pecron_credentials(email: str, password: str, region: str) -> None:
        """Validate Pecron credentials.

        The login endpoint rejects a request with an ``AuthenticationError``
        both for a wrong password and for a wrong region: each region signs
        requests with a different secret, so picking the wrong region looks
        identical to bad credentials from the API's point of view. Surface
        both as ``invalid_auth`` (with a region hint in the error string)
        rather than the generic ``cannot_connect``, which previously misled
        users into thinking it was a network problem. See GH#6.
        """
        try:
            api = PecronAPI(region=region)
            api.login(email, password)
            devices = api.get_devices()
            api.close()
        except AuthenticationError as err:
            raise PecronAuthError(str(err)) from err
        except requests.exceptions.RequestException as err:
            raise PecronConnectionError(str(err)) from err

        if not devices:
            raise PecronAuthError("No devices found on account")


class PecronOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Pecron integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        current_refresh = self.config_entry.options.get(
            CONF_REFRESH_INTERVAL,
            self.config_entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        )
        current_refresh_minutes = _seconds_to_minutes(current_refresh)

        if user_input is not None:
            options_data = dict(user_input)
            options_data[CONF_REFRESH_INTERVAL] = _minutes_to_seconds(
                options_data.get(CONF_REFRESH_INTERVAL, current_refresh_minutes)
            )
            return self.async_create_entry(title="", data=options_data)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=current_refresh_minutes,
                ): vol.All(vol.Coerce(float), vol.Range(min=1, max=60)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)


class PecronAuthError(HomeAssistantError):
    """Pecron authentication error."""


class PecronConnectionError(HomeAssistantError):
    """Pecron connection error."""
