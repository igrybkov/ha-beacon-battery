# Beacon Battery

A Home Assistant integration that adds battery sensors to BLE beacons. It reads the level from the beacon's own adverts, so you don't need an extra gateway or app.

It finds the beacon devices of another integration ([Bermuda](https://github.com/agittins/bermuda) by default). When one of them sends a battery frame, it adds a battery sensor to that device. You never list MAC addresses. A beacon you add to Bermuda later gets its sensor by itself.

## How it works

1. It reads the device registry for devices of the source integration that are identified by MAC address. Devices tracked by iBeacon UUID are skipped, because adverts carry only the MAC.
2. It listens through Home Assistant's Bluetooth stack for adverts with the configured battery frames. Every adapter and ESPHome Bluetooth proxy feeds this stack.
3. It reads one byte of the frame as battery %, capped at a maximum.
4. It shows the sensor on the existing device, for example `sensor.trash_bin_battery` on the Bermuda "Trash Bin" device.

The sensor keeps its last value across restarts and while the beacon is out of range. It writes a new state when the level changes. On each heartbeat interval it writes the level again for every beacon that is still in range. So tools such as [Battery Notes](https://github.com/andrew-codechimp/HA-Battery-Notes) can tell that the beacon still works. They can also alert when it goes silent.

## Supported beacons

The defaults fit KKM beacons (also sold as Blue Charm, for example the BC04P and BC08). They send battery % in two frames.

In iBeacon mode, service data `0x2080` (frame spec `2080:0`):

```
69 1c 0e fe 13 55
│  │  └──┬┘ └──┬┘
│  │   major  minor
│  └ unknown
└ battery % (0x69 = 105, shown as 100)
```

In a "System" slot, Eddystone service data `0xFEAA` that starts with `0x22` (frame spec `feaa:2:22`). The beacon also sends this for 30 seconds after a battery is put in:

```
22 2f 69 dd 34 02 0a 42 e7 06 40
│  │  │  └───────┬───────┘ └─┬─┘
│  │  │         MAC        model / firmware
│  │  └ battery %
│  └ unknown
└ frame type (KKM system)
```

Other beacons work if they send battery % in one byte of a service data frame. Add a frame spec under options.

### Which frame is read

Home Assistant's Bluetooth stack merges service data across adverts. A frame the beacon stopped sending stays in the merged data until the beacon goes out of range. So the integration reads the frame whose data changed most recently. When several change at once, for example after a restart, it reads the lowest level, because a battery only drains and a stale frame holds an older, higher value.

## Install

1. In **Settings → Marketplace** (HACS before Home Assistant 2026.11), add this repository as a custom repository with type **Integration**.
2. Install **Beacon Battery** and restart Home Assistant.
3. Add the integration under **Settings → Devices & services**.

## Options

| Option | Default | What it does |
|---|---|---|
| Source integration | `bermuda` | Integration whose MAC-based devices get a battery sensor. |
| Battery frames | `feaa:2:22`, `2080:0` | Frames that carry battery %, as `uuid:byte` or `uuid:byte:prefix`. `uuid` is 16-bit (`2080`) or full 128-bit. `byte` counts from 0. `prefix` (hex) must start the data, which tells apart frames that share a UUID, such as Eddystone. List order breaks ties. |
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
