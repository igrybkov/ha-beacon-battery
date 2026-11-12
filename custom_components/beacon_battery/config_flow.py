"""Config and options flow for Beacon Battery."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from . import BeaconBatteryConfigEntry
from .const import (
    CONF_BATTERY_BYTE,
    CONF_HEARTBEAT_MINUTES,
    CONF_MAX_LEVEL,
    CONF_SERVICE_DATA_UUID,
    CONF_SOURCE_DOMAIN,
    DEFAULT_OPTIONS,
    DOMAIN,
)
from .helpers import normalize_service_data_uuid


def _number(minimum: int, maximum: int, unit: str | None = None) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
            **({"unit_of_measurement": unit} if unit else {}),
        )
    )


def _options_schema(current: dict[str, Any]) -> vol.Schema:
    values = {**DEFAULT_OPTIONS, **current}
    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE_DOMAIN, default=values[CONF_SOURCE_DOMAIN]
            ): selector.TextSelector(),
            vol.Required(
                CONF_SERVICE_DATA_UUID, default=values[CONF_SERVICE_DATA_UUID]
            ): selector.TextSelector(),
            vol.Required(CONF_BATTERY_BYTE, default=values[CONF_BATTERY_BYTE]): _number(0, 30),
            vol.Required(CONF_MAX_LEVEL, default=values[CONF_MAX_LEVEL]): _number(1, 255, "%"),
            vol.Required(CONF_HEARTBEAT_MINUTES, default=values[CONF_HEARTBEAT_MINUTES]): _number(
                1, 1440, "min"
            ),
        }
    )


def _validate(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Normalize input. Return the cleaned options and any form errors."""
    errors: dict[str, str] = {}
    cleaned = dict(user_input)
    cleaned[CONF_SOURCE_DOMAIN] = user_input[CONF_SOURCE_DOMAIN].strip()
    if not cleaned[CONF_SOURCE_DOMAIN]:
        errors[CONF_SOURCE_DOMAIN] = "required"
    uuid = normalize_service_data_uuid(user_input[CONF_SERVICE_DATA_UUID])
    if uuid is None:
        errors[CONF_SERVICE_DATA_UUID] = "invalid_uuid"
    else:
        cleaned[CONF_SERVICE_DATA_UUID] = uuid
    for key in (CONF_BATTERY_BYTE, CONF_MAX_LEVEL, CONF_HEARTBEAT_MINUTES):
        cleaned[key] = int(user_input[key])
    return cleaned, errors


class BeaconBatteryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up one Beacon Battery instance."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Create the entry. All settings have defaults and live in options."""
        if user_input is not None:
            return self.async_create_entry(
                title="Beacon Battery", data={}, options=dict(DEFAULT_OPTIONS)
            )
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: BeaconBatteryConfigEntry,
    ) -> BeaconBatteryOptionsFlow:
        """Return the options flow."""
        return BeaconBatteryOptionsFlow()


class BeaconBatteryOptionsFlow(OptionsFlow):
    """Change how adverts are matched and decoded."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show and save the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            cleaned, errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(data=cleaned)
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(
                user_input if user_input is not None else dict(self.config_entry.options)
            ),
            errors=errors,
        )
