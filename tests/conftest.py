"""Fixtures for Beacon Battery tests."""

from __future__ import annotations

from collections.abc import Callable, Generator
from unittest.mock import patch

import pytest
from home_assistant_bluetooth import BluetoothServiceInfo
from homeassistant.components.bluetooth import BluetoothChange
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.beacon_battery.const import DEFAULT_OPTIONS, DOMAIN

UUID_2080 = "00002080-0000-1000-8000-00805f9b34fb"
UUID_FEAA = "0000feaa-0000-1000-8000-00805f9b34fb"
TRASH_MAC = "dd:34:02:0a:42:e7"
RECYCLE_MAC = "dd:34:02:0a:43:81"
# Captured from the real beacons: [battery, ?, major, minor]
TRASH_PAYLOAD = bytes.fromhex("691c0efe1355")
RECYCLE_PAYLOAD = bytes.fromhex("661c1c601c61")
# KKM system frame on the Eddystone UUID: [0x22, ?, battery, MAC, ...]
TRASH_SYSTEM = bytes.fromhex("222f69dd34020a42e70640")
RECYCLE_SYSTEM = bytes.fromhex("222f66dd34020a43810640")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components in every test."""


class FakeBluetooth:
    """Stand-in for the bluetooth integration's callback registry."""

    def __init__(self) -> None:
        self.callbacks: list[tuple[Callable, dict]] = []
        # Latest advert per uppercase address, like the real stack keeps.
        self.last: dict[str, BluetoothServiceInfo] = {}
        self.present: set[str] = set()

    def address_present(self, _hass, address: str, connectable: bool = True) -> bool:
        assert connectable is False
        return address in self.present

    def last_service_info(self, _hass, address: str, connectable: bool = True):
        assert connectable is False
        return self.last.get(address)

    def register(self, _hass, callback, matcher, _mode, **_kwargs):
        entry = (callback, matcher)
        self.callbacks.append(entry)
        return lambda: self.callbacks.remove(entry)

    def advert(self, mac: str, service_data: dict[str, bytes]) -> None:
        info = BluetoothServiceInfo(
            name="",
            address=mac.upper(),
            rssi=-70,
            manufacturer_data={},
            service_data=service_data,
            service_uuids=[],
            source="aa:bb:cc:dd:ee:ff",
        )
        self.last[info.address] = info
        self.present.add(info.address)
        for callback, matcher in list(self.callbacks):
            if matcher["service_data_uuid"] in service_data:
                callback(info, BluetoothChange.ADVERTISEMENT)


@pytest.fixture
def fake_bluetooth(hass: HomeAssistant) -> Generator[FakeBluetooth]:
    """Mark bluetooth as loaded and capture registered callbacks."""
    hass.config.components.add("bluetooth")
    fake = FakeBluetooth()
    bt = "homeassistant.components.bluetooth"
    with (
        patch(f"{bt}.async_register_callback", fake.register),
        patch(f"{bt}.async_address_present", fake.address_present),
        patch(f"{bt}.async_last_service_info", fake.last_service_info),
    ):
        yield fake


@pytest.fixture
def source_entry(hass: HomeAssistant) -> MockConfigEntry:
    """A config entry that stands in for Bermuda."""
    entry = MockConfigEntry(domain="bermuda", title="Bermuda")
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def bin_devices(hass: HomeAssistant, source_entry: MockConfigEntry) -> dict[str, str]:
    """Bermuda devices: two MAC-based bins and one iBeacon-ID based device."""
    reg = dr.async_get(hass)
    ids = {}
    for name, mac in (("Trash Bin", TRASH_MAC), ("Recycle Bin", RECYCLE_MAC)):
        ids[mac] = reg.async_get_or_create(
            config_entry_id=source_entry.entry_id,
            identifiers={("bermuda", mac)},
            name=name,
        ).id
    reg.async_get_or_create(
        config_entry_id=source_entry.entry_id,
        identifiers={("bermuda", "526db0c2f719410d90e4847ebd88759b_7264_7265")},
        name="Old iBeacon",
    )
    # Some integrations store three-part identifiers. They must not break setup.
    other = MockConfigEntry(domain="other_integration")
    other.add_to_hass(hass)
    reg.async_get_or_create(
        config_entry_id=other.entry_id,
        identifiers={("other_integration", "hub", "1")},
        name="Odd Identifier Device",
    )
    return ids


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    """Beacon Battery config entry with default options."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="Beacon Battery", options=dict(DEFAULT_OPTIONS), version=2
    )
    entry.add_to_hass(hass)
    return entry
