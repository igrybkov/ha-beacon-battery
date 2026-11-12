# Beacon Battery

A Home Assistant integration that adds battery sensors to BLE beacons. It reads the level from the beacon's own adverts, so you don't need an extra gateway or app.

It finds the beacon devices of another integration ([Bermuda](https://github.com/agittins/bermuda) by default). When one of them sends a battery frame, it adds a battery sensor to that device. You never list MAC addresses. A beacon you add to Bermuda later gets its sensor by itself.

## How it works

1. It reads the device registry for devices of the source integration that are identified by MAC address. Devices tracked by iBeacon UUID are skipped, because adverts carry only the MAC.
2. It listens through Home Assistant's Bluetooth stack for adverts with the configured service data UUID. Every adapter and ESPHome Bluetooth proxy feeds this stack.
3. It reads one byte of that service data as battery %, capped at a maximum.
4. It shows the sensor on the existing device, for example `sensor.trash_bin_battery` on the Bermuda "Trash Bin" device.

The sensor keeps its last value across restarts and while the beacon is out of range. It writes a new state when the level changes. On each heartbeat interval it writes the level again for every beacon that is still in range. So tools such as [Battery Notes](https://github.com/andrew-codechimp/HA-Battery-Notes) can tell that the beacon still works. They can also alert when it goes silent.

## Supported beacons

The defaults fit KKM beacons (also sold as Blue Charm, for example the BC04P and BC08). In iBeacon mode they send service data `0x2080` with the battery % in the first byte:

```
69 1c 0e fe 13 55
│  │  └──┬┘ └──┬┘
│  │   major  minor
│  └ unknown
└ battery % (0x69 = 105, shown as 100)
```

Other beacons work if they send battery % in one byte of a service data frame. Set the UUID and byte position under options.

## Install

1. In HACS, add this repository as a custom repository with type **Integration**.
2. Install **Beacon Battery** and restart Home Assistant.
3. Add the integration under **Settings → Devices & services**.

## Options

| Option | Default | What it does |
|---|---|---|
| Source integration | `bermuda` | Integration whose MAC-based devices get a battery sensor. |
| Service data UUID | `0x2080` (as full UUID) | Service data that carries the level. A 16-bit form such as `2080` works too. |
| Battery byte position | `0` | Byte with the level, counting from 0. |
| Maximum level | `100` | Higher readings are capped to this value. |
| Heartbeat interval | `30` min | How often the level of each beacon in range is written again. |

## Requirements

- Home Assistant 2026.10 or later.
- Bluetooth that can hear the beacon: a local adapter or an ESPHome Bluetooth proxy.
- If the frame comes in the scan response (KKM sends it there), the proxy or adapter must scan in active mode. ESPHome Bluetooth proxies use active mode by default.

## Development

```sh
make venv    # uv venv with the pinned test harness
make test
make lint
```

## License

MIT
