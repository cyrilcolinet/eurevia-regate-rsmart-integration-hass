# Roadmap (detailed view)

Short version: [README](../README.md) · detailed view below.

| | |
|---|---|
| **Latest GitHub release** | [releases](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/releases/latest) |
| **Repository `manifest.json`** | 1.0.0 |

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

## v1.0.0 (initial release)

- Local MQTT client (async, MQTT 3.1.1)
- Zone list from `{prefix}/zones` + config flow zone picker
- HVAC device classification by payload keys (terminal, purifier, thermostat, actuator, system, scheduler)
- Climate, fan, sensor, binary_sensor platforms
- Unit tests + optional live MQTT integration tests
- CI: Ruff, pytest, Hassfest, HACS

Entity detail: [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md) · Protocol: [MQTT.md](MQTT.md)
