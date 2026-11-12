# AGENTS.md

This file guides AI coding agents (Claude Code, Codex, Cursor and others) that work in this repository.

Beacon Battery is a Home Assistant custom integration, installed through the Home Assistant Marketplace (formerly HACS). It adds a battery sensor to each BLE beacon device of a source integration (Bermuda by default). The level is decoded from a service data frame in the beacon's adverts.

## Commands

```sh
make venv     # uv venv with requirements_test.txt
make test     # pytest
make lint     # ruff check + ruff format --check
make format
```

CI runs lint, tests, hassfest and HACS validation. Run `make lint test` before you call a change done.

## Releases

To release, bump `version` in `custom_components/beacon_battery/manifest.json` and add a `## X.Y.Z` section to `CHANGELOG.md` in the same commit. When that reaches `main`, `.github/workflows/release.yaml` runs the CI checks, then creates tag `X.Y.Z` (no `v` prefix, since the Marketplace matches the tag to the manifest version) and a GitHub release with that changelog section as notes. Do not create tags by hand.

## Layout

- `custom_components/beacon_battery/helpers.py`: pure functions (MAC and UUID normalization, byte parsing). No HA state.
- `custom_components/beacon_battery/sensor.py`: `BeaconTracker` maps MACs to source devices, listens for adverts, and creates `BeaconBatterySensor` entities.
- `custom_components/beacon_battery/translations/en.json`: the only UI text source. Custom integrations do not use `strings.json`.
- `custom_components/beacon_battery/config_flow.py`: single-instance config flow. Every setting is an option with a default in `const.py`.
- `tests/conftest.py`: `FakeBluetooth` replaces `bluetooth.async_register_callback`, so tests need no adapter.

## Rules

- Every tunable is an option with a default. Code constants are defaults only.
- Attach sensors to the source device with `entity.device_entry`. Do not use `device_info`: since HA 2026.10 a device belongs to one config entry, so `device_info` creates a second device.
- The Bluetooth matcher must set `connectable: False`. The default is connectable only, and beacons send non-connectable adverts.
- The Bluetooth stack does not call callbacks for adverts with an unchanged payload. The callback handles changes only. The heartbeat timer uses `async_address_present` and `async_last_service_info` to report beacons that are still in range.
- Comments and docs must stand on their own. Never refer to private plans, tickets or chat history.
- The test harness version pins the Home Assistant version. Raise `hacs.json` `homeassistant` only when the code needs it.
