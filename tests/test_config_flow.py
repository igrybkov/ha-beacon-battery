"""Tests for the config and options flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.beacon_battery.const import (
    CONF_BATTERY_BYTE,
    CONF_HEARTBEAT_MINUTES,
    CONF_MAX_LEVEL,
    CONF_SERVICE_DATA_UUID,
    CONF_SOURCE_DOMAIN,
    DEFAULT_OPTIONS,
    DOMAIN,
)

from .conftest import UUID_2080, FakeBluetooth


async def test_user_flow_creates_entry_with_defaults(
    hass: HomeAssistant, fake_bluetooth: FakeBluetooth
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == DEFAULT_OPTIONS


async def test_single_instance(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow_normalizes_uuid(
    hass: HomeAssistant, fake_bluetooth: FakeBluetooth, entry: MockConfigEntry
) -> None:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_DOMAIN: "bermuda",
            CONF_SERVICE_DATA_UUID: "bad",
            CONF_BATTERY_BYTE: 0,
            CONF_MAX_LEVEL: 100,
            CONF_HEARTBEAT_MINUTES: 30,
        },
    )
    assert result["errors"] == {CONF_SERVICE_DATA_UUID: "invalid_uuid"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_DOMAIN: "bermuda",
            CONF_SERVICE_DATA_UUID: "0x2080",
            CONF_BATTERY_BYTE: 1,
            CONF_MAX_LEVEL: 100,
            CONF_HEARTBEAT_MINUTES: 15,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_SERVICE_DATA_UUID] == UUID_2080
    assert entry.options[CONF_BATTERY_BYTE] == 1
