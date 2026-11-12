"""Tests for the config and options flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.beacon_battery.const import (
    CONF_FRAMES,
    CONF_HEARTBEAT_MINUTES,
    CONF_MAX_LEVEL,
    CONF_SOURCE_DOMAIN,
    DEFAULT_OPTIONS,
    DOMAIN,
)

from .conftest import FakeBluetooth


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


def _options(frames: list[str], heartbeat: int = 30) -> dict:
    return {
        CONF_SOURCE_DOMAIN: "bermuda",
        CONF_FRAMES: frames,
        CONF_MAX_LEVEL: 100,
        CONF_HEARTBEAT_MINUTES: heartbeat,
    }


async def test_options_flow_validates_and_normalizes_frames(
    hass: HomeAssistant, fake_bluetooth: FakeBluetooth, entry: MockConfigEntry
) -> None:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _options(["2080:0", "bad"])
    )
    assert result["errors"] == {CONF_FRAMES: "invalid_frame"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _options(["", " "])
    )
    assert result["errors"] == {CONF_FRAMES: "required"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _options(["0x2080:1", "FEAA:2:0x22"], heartbeat=15)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_FRAMES] == ["2080:1", "feaa:2:22"]
    assert entry.options[CONF_HEARTBEAT_MINUTES] == 15


async def test_migrates_version_1_options(
    hass: HomeAssistant, fake_bluetooth: FakeBluetooth
) -> None:
    default_v1 = {
        CONF_SOURCE_DOMAIN: "bermuda",
        "service_data_uuid": "00002080-0000-1000-8000-00805f9b34fb",
        "battery_byte": 0,
        CONF_MAX_LEVEL: 100,
        CONF_HEARTBEAT_MINUTES: 30,
    }
    entry = MockConfigEntry(domain=DOMAIN, options=default_v1, version=1)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.version == 2
    assert entry.options == DEFAULT_OPTIONS


async def test_migration_keeps_a_custom_frame_first(
    hass: HomeAssistant, fake_bluetooth: FakeBluetooth
) -> None:
    custom_v1 = {
        CONF_SOURCE_DOMAIN: "bermuda",
        "service_data_uuid": "2080",
        "battery_byte": 1,
        CONF_MAX_LEVEL: 100,
        CONF_HEARTBEAT_MINUTES: 30,
    }
    entry = MockConfigEntry(domain=DOMAIN, options=custom_v1, version=1)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.options[CONF_FRAMES] == ["2080:1", "feaa:2:22", "2080:0"]
    assert "service_data_uuid" not in entry.options
