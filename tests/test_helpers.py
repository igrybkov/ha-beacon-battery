"""Tests for the pure helpers."""

from custom_components.beacon_battery.helpers import (
    Frame,
    FrameChooser,
    format_frame,
    mac_identifiers,
    normalize_mac,
    normalize_service_data_uuid,
    parse_frame,
)

from .conftest import TRASH_MAC, TRASH_PAYLOAD, TRASH_SYSTEM, UUID_2080, UUID_FEAA

FRAME_2080 = Frame(UUID_2080, 0)
FRAME_SYSTEM = Frame(UUID_FEAA, 2, b"\x22")


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


def test_mac_identifiers_skips_other_shapes() -> None:
    found = mac_identifiers(
        [
            ("bermuda", "dd:34:02:0a:42:e7", "extra"),
            ("bermuda",),
            ("bermuda", 12345),
            ("bermuda", "dd:34:02:0a:43:81"),
        ],
        "bermuda",
    )
    assert found == {"dd:34:02:0a:43:81": ("bermuda", "dd:34:02:0a:43:81")}


def test_parse_frame() -> None:
    assert parse_frame("2080:0") == FRAME_2080
    assert parse_frame(" FEAA:2:0x22 ") == FRAME_SYSTEM
    assert parse_frame(f"{UUID_2080}:1") == Frame(UUID_2080, 1)
    for bad in ("2080", "2080:x", "zz:0", "2080:0:zz", "2080:0:", "2080:0:22:1"):
        assert parse_frame(bad) is None, bad


def test_format_frame_round_trips() -> None:
    assert format_frame(FRAME_2080) == "2080:0"
    assert format_frame(FRAME_SYSTEM) == "feaa:2:22"
    custom = Frame("12345678-1234-1234-1234-123456789abc", 3)
    assert parse_frame(format_frame(custom)) == custom


def test_frame_payload_and_level() -> None:
    assert FRAME_2080.level(FRAME_2080.payload({UUID_2080: TRASH_PAYLOAD}), 100) == 100
    assert FRAME_2080.level(TRASH_PAYLOAD, 255) == 105
    assert FRAME_SYSTEM.level(FRAME_SYSTEM.payload({UUID_FEAA: TRASH_SYSTEM}), 255) == 105
    # An Eddystone TLM frame (0x20) shares the UUID but not the prefix.
    assert FRAME_SYSTEM.payload({UUID_FEAA: bytes.fromhex("20000bb8")}) is None
    assert Frame(UUID_2080, 6).payload({UUID_2080: TRASH_PAYLOAD}) is None
    assert FRAME_2080.payload({}) is None


def test_chooser_prefers_the_frame_that_changed() -> None:
    chooser = FrameChooser([FRAME_SYSTEM, FRAME_2080], 255)
    system = bytes.fromhex("222f50dd34020a42e70640")  # 80
    ibeacon = bytes.fromhex("501c0efe1355")  # 80

    # First sight: both are new, so list order decides.
    assert chooser.level(TRASH_MAC, {UUID_FEAA: system, UUID_2080: ibeacon}, track=True) == 80
    # The beacon stopped sending the system frame; the merged data keeps the
    # old one. The live 0x2080 frame changes and wins from now on.
    live = bytes.fromhex("4b1c0efe1355")  # 75
    assert chooser.level(TRASH_MAC, {UUID_FEAA: system, UUID_2080: live}, track=True) == 75
    assert chooser.level(TRASH_MAC, {UUID_FEAA: system, UUID_2080: live}, track=False) == 75


def test_chooser_picks_lowest_level_when_all_frames_are_new() -> None:
    # After a restart every frame looks new. A stale frame holds an older,
    # higher level, so the lower one is the live reading.
    chooser = FrameChooser([FRAME_SYSTEM, FRAME_2080], 255)
    stale_system = bytes.fromhex("222f69dd34020a42e70640")  # 105
    live_ibeacon = bytes.fromhex("5a1c0efe1355")  # 90
    data = {UUID_FEAA: stale_system, UUID_2080: live_ibeacon}
    assert chooser.level(TRASH_MAC, data, track=True) == 90
    assert chooser.level(TRASH_MAC, data, track=False) == 90


def test_chooser_falls_back_when_preferred_frame_is_gone() -> None:
    chooser = FrameChooser([FRAME_SYSTEM, FRAME_2080], 100)
    assert chooser.level(TRASH_MAC, {UUID_FEAA: TRASH_SYSTEM}, track=True) == 100
    # Merge history cleared (beacon left range); only 0x2080 is there now.
    assert chooser.level(TRASH_MAC, {UUID_2080: TRASH_PAYLOAD}, track=False) == 100
    assert chooser.level(TRASH_MAC, {}, track=True) is None
    assert chooser.uuids == [UUID_FEAA, UUID_2080]
