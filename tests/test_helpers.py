"""Tests for the pure helpers."""

from custom_components.beacon_battery.helpers import (
    mac_identifiers,
    normalize_mac,
    normalize_service_data_uuid,
    parse_battery,
)

from .conftest import TRASH_PAYLOAD, UUID_2080


def test_normalize_mac() -> None:
    assert normalize_mac("DD:34:02:0A:42:E7") == "dd:34:02:0a:42:e7"
    assert normalize_mac("dd-34-02-0a-42-e7") == "dd:34:02:0a:42:e7"
    assert normalize_mac("526db0c2f719410d90e4847ebd88759b_7264_7265") is None


def test_normalize_service_data_uuid() -> None:
    assert normalize_service_data_uuid("2080") == UUID_2080
    assert normalize_service_data_uuid("0x2080") == UUID_2080
    assert normalize_service_data_uuid(UUID_2080.upper()) == UUID_2080
    assert normalize_service_data_uuid("nope") is None


def test_mac_identifiers_keeps_only_source_macs() -> None:
    found = mac_identifiers(
        {
            ("bermuda", "dd:34:02:0a:42:e7"),
            ("bermuda", "526db0c2f719410d90e4847ebd88759b_7264_7265"),
            ("other", "aa:bb:cc:dd:ee:ff"),
        },
        "bermuda",
    )
    assert found == {"dd:34:02:0a:42:e7": ("bermuda", "dd:34:02:0a:42:e7")}


def test_parse_battery() -> None:
    data = {UUID_2080: TRASH_PAYLOAD}
    assert parse_battery(data, UUID_2080, 0, 100) == 100  # 0x69 = 105, capped
    assert parse_battery(data, UUID_2080, 0, 255) == 105
    assert parse_battery(data, UUID_2080, 1, 100) == 0x1C
    assert parse_battery(data, UUID_2080, 6, 100) is None
    assert parse_battery({}, UUID_2080, 0, 100) is None
