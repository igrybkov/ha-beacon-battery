"""Tests for the battery sensors."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_report_event
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from custom_components.beacon_battery.const import (
    CONF_FRAMES,
    CONF_HEARTBEAT_MINUTES,
    DEFAULT_OPTIONS,
)

from .conftest import (
    RECYCLE_MAC,
    RECYCLE_PAYLOAD,
    TRASH_MAC,
    TRASH_PAYLOAD,
    TRASH_SYSTEM,
    UUID_2080,
    UUID_FEAA,
    FakeBluetooth,
)


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_registers_non_connectable_matcher(
    hass: HomeAssistant, fake_bluetooth: FakeBluetooth, entry: MockConfigEntry
) -> None:
    await _setup(hass, entry)
    matchers = [matcher for _, matcher in fake_bluetooth.callbacks]
    assert matchers == [
        {"service_data_uuid": UUID_FEAA, "connectable": False},
        {"service_data_uuid": UUID_2080, "connectable": False},
    ]


async def test_sensor_attaches_to_source_device(
    hass: HomeAssistant,
    fake_bluetooth: FakeBluetooth,
    bin_devices: dict[str, str],
    entry: MockConfigEntry,
) -> None:
    await _setup(hass, entry)
    fake_bluetooth.advert(TRASH_MAC, {UUID_2080: TRASH_PAYLOAD})
    fake_bluetooth.advert(RECYCLE_MAC, {UUID_2080: RECYCLE_PAYLOAD})
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    trash = ent_reg.async_get_entity_id("sensor", "beacon_battery", f"{TRASH_MAC}_battery")
    assert trash == "sensor.trash_bin_battery"
    assert ent_reg.async_get(trash).device_id == bin_devices[TRASH_MAC]
    state = hass.states.get(trash)
    assert state.state == "100"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.BATTERY
    assert hass.states.get("sensor.recycle_bin_battery").state == "100"

    # The sensor joins the existing device: no second device, name unchanged.
    dev_reg = dr.async_get(hass)
    assert len(dev_reg.devices) == 4
    assert dev_reg.async_get(bin_devices[TRASH_MAC]).name == "Trash Bin"


async def test_ignores_unknown_and_non_mac_devices(
    hass: HomeAssistant,
    fake_bluetooth: FakeBluetooth,
    bin_devices: dict[str, str],
    entry: MockConfigEntry,
) -> None:
    await _setup(hass, entry)
    fake_bluetooth.advert("aa:bb:cc:dd:ee:ff", {UUID_2080: TRASH_PAYLOAD})
    await hass.async_block_till_done()
    assert hass.states.async_entity_ids("sensor") == []


async def test_device_added_later_is_picked_up(
    hass: HomeAssistant,
    fake_bluetooth: FakeBluetooth,
    source_entry: MockConfigEntry,
    entry: MockConfigEntry,
) -> None:
    await _setup(hass, entry)
    fake_bluetooth.advert(TRASH_MAC, {UUID_2080: TRASH_PAYLOAD})
    await hass.async_block_till_done()
    assert hass.states.async_entity_ids("sensor") == []

    dr.async_get(hass).async_get_or_create(
        config_entry_id=source_entry.entry_id,
        identifiers={("bermuda", TRASH_MAC)},
        name="Trash Bin",
    )
    await hass.async_block_till_done()
    fake_bluetooth.advert(TRASH_MAC, {UUID_2080: TRASH_PAYLOAD})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.trash_bin_battery").state == "100"


async def test_frames_option(
    hass: HomeAssistant,
    fake_bluetooth: FakeBluetooth,
    bin_devices: dict[str, str],
) -> None:
    entry = MockConfigEntry(
        domain="beacon_battery", options={**DEFAULT_OPTIONS, CONF_FRAMES: ["2080:1"]}, version=2
    )
    entry.add_to_hass(hass)
    await _setup(hass, entry)
    fake_bluetooth.advert(TRASH_MAC, {UUID_2080: TRASH_PAYLOAD})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.trash_bin_battery").state == str(0x1C)


async def test_system_frame_alone_creates_sensor(
    hass: HomeAssistant,
    fake_bluetooth: FakeBluetooth,
    bin_devices: dict[str, str],
    entry: MockConfigEntry,
) -> None:
    await _setup(hass, entry)
    fake_bluetooth.advert(TRASH_MAC, {UUID_FEAA: TRASH_SYSTEM})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.trash_bin_battery").state == "100"


async def test_live_frame_beats_stale_merged_frame(
    hass: HomeAssistant,
    fake_bluetooth: FakeBluetooth,
    bin_devices: dict[str, str],
) -> None:
    entry = MockConfigEntry(
        domain="beacon_battery", options={**DEFAULT_OPTIONS, "max_level": 255}, version=2
    )
    entry.add_to_hass(hass)
    await _setup(hass, entry)
    # Merged data: a system frame the beacon no longer sends, plus 0x2080.
    stale = {UUID_FEAA: TRASH_SYSTEM}
    fake_bluetooth.advert(TRASH_MAC, {**stale, UUID_2080: TRASH_PAYLOAD})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.trash_bin_battery").state == "105"

    # Only 0x2080 changes, so it wins over the stale system frame.
    fake_bluetooth.advert(TRASH_MAC, {**stale, UUID_2080: bytes.fromhex("5a1c0efe1355")})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.trash_bin_battery").state == "90"


async def test_writes_only_on_change_from_adverts(
    hass: HomeAssistant,
    fake_bluetooth: FakeBluetooth,
    bin_devices: dict[str, str],
    entry: MockConfigEntry,
) -> None:
    await _setup(hass, entry)
    fake_bluetooth.advert(TRASH_MAC, {UUID_2080: TRASH_PAYLOAD})
    await hass.async_block_till_done()
    reports = []
    async_track_state_report_event(hass, "sensor.trash_bin_battery", reports.append)

    fake_bluetooth.advert(TRASH_MAC, {UUID_2080: TRASH_PAYLOAD})
    await hass.async_block_till_done()
    assert reports == []

    fake_bluetooth.advert(TRASH_MAC, {UUID_2080: bytes.fromhex("501c0efe1355")})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.trash_bin_battery").state == "80"


async def test_heartbeat_reports_present_beacons(
    hass: HomeAssistant,
    fake_bluetooth: FakeBluetooth,
    bin_devices: dict[str, str],
) -> None:
    entry = MockConfigEntry(
        domain="beacon_battery", options={**DEFAULT_OPTIONS, CONF_HEARTBEAT_MINUTES: 30}
    )
    entry.add_to_hass(hass)
    await _setup(hass, entry)
    fake_bluetooth.advert(TRASH_MAC, {UUID_2080: TRASH_PAYLOAD})
    fake_bluetooth.advert(RECYCLE_MAC, {UUID_2080: RECYCLE_PAYLOAD})
    await hass.async_block_till_done()
    trash, recycle = [], []
    async_track_state_report_event(hass, "sensor.trash_bin_battery", trash.append)
    async_track_state_report_event(hass, "sensor.recycle_bin_battery", recycle.append)

    # The recycle bin went out of range; only the trash bin is reported.
    fake_bluetooth.present.discard(RECYCLE_MAC.upper())
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert len(trash) == 1
    assert recycle == []
    assert hass.states.get("sensor.recycle_bin_battery").state == "100"


async def test_restores_after_restart(
    hass: HomeAssistant,
    fake_bluetooth: FakeBluetooth,
    bin_devices: dict[str, str],
    entry: MockConfigEntry,
) -> None:
    er.async_get(hass).async_get_or_create(
        "sensor",
        "beacon_battery",
        f"{TRASH_MAC}_battery",
        config_entry=entry,
        device_id=bin_devices[TRASH_MAC],
        suggested_object_id="trash_bin_battery",
    )
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State("sensor.trash_bin_battery", "87"),
                {"native_value": 87, "native_unit_of_measurement": "%"},
            )
        ],
    )
    await _setup(hass, entry)
    # No advert yet, the last level is back.
    assert hass.states.get("sensor.trash_bin_battery").state == "87"


async def test_unload_stops_listening(
    hass: HomeAssistant, fake_bluetooth: FakeBluetooth, entry: MockConfigEntry
) -> None:
    await _setup(hass, entry)
    assert fake_bluetooth.callbacks
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert fake_bluetooth.callbacks == []
