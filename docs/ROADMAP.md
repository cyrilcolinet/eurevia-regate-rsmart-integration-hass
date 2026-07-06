# Roadmap (detailed view)

> **Disclaimer:** Unofficial community project — not affiliated with or endorsed by Eurevia. Maintainers are independent and do not work for Eurevia. [Full disclaimer](DISCLAIMER.md)

Short version: [README](../README.md) · detailed view below.

| | |
|---|---|
| **Latest GitHub release** | [releases](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/releases/latest) |
| **Repository `manifest.json`** | 1.1.0 |

## Status by feature

| Status | Feature | HA entities |
|--------|---------|-------------|
| ✅ Supported | Climatic zones | `climate`, `binary_sensor`, `sensor` |
| ✅ Supported | Global thermostat (Bloc CVC) | `climate` |
| ✅ Supported | Per-zone thermostats | `climate` |
| ✅ Supported | Air purifier (when `P_Mode` present) | `fan` |
| ✅ Supported | Terminal diagnostics | `sensor` (dynamic from MQTT keys) |
| ✅ Supported | Window / presence per zone | `binary_sensor` |
| ✅ Supported | MQTT auto-discovery (pattern-based roles) | — |
| 🔬 Beta | Actuator HVAC role | None yet |
| 🔬 Beta | System / scheduler HVAC roles | None yet |
| ⏳ Planned | Default HACS store | CI green — [PR to `hacs/default`](HACS.md#default-hacs-store) |
| ⏳ Not planned | Third-party Zigbee on reGATE | Use Z2M / ZHA |
| ⏳ Not planned | rSMART mobile app / cloud account | Out of scope |

**Out of scope:** devices outside the Eurevia climatic stack on the reGATE hub.

## v1.1.0

- Per-mode climate setpoints (`Stp_Comf`, `Stp_Eco_C/H`, `Stp_Reduc_C/H`) with dynamic discovery
- `number` entities for writable zone setpoints and `Tmp_Offset`
- Purifier commands published to all terminal devices (`10` + `20`)
- Terminal sensor keys union across all terminal MQTT devices
- Binary sensors and zone sensors only when MQTT keys are present
- Opt-in telemetry (persistent notification + pre-filled GitHub issue for unknown MQTT keys / unimplemented roles)
- Diagnostics enriched with HVAC profiles and key lists

Entity detail: [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md) · Protocol: [MQTT.md](MQTT.md) · Telemetry: [TELEMETRY.md](TELEMETRY.md)

## v1.0.0 (initial release)

- Local MQTT client (async, MQTT 3.1.1)
- Zone list from `{prefix}/zones` + config flow zone picker
- HVAC device classification by payload keys (terminal, purifier, thermostat, actuator, system, scheduler)
- Climate, fan, sensor, binary_sensor platforms
- Unit tests + optional live MQTT integration tests
- CI: Ruff, pytest, Hassfest, HACS

Entity detail: [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md) · Protocol: [MQTT.md](MQTT.md)
