<p align="center">
  <img src="https://raw.githubusercontent.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/main/custom_components/eurevia_regate_rsmart/brand/logo-eurevia.png" alt="Eurevia" width="120">
</p>

<h1 align="center">Eurevia reGATE (rSmart) for Home Assistant</h1>

<p align="center">
  <strong>Local MQTT integration for the Eurevia reGATE hub</strong><br>
  Multi-zone heating, air purifier, terminal diagnostics, window and presence sensors — directly from your reGATE broker.
</p>

<p align="center">
  <a href="https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/actions/workflows/ci.yml"><img src="https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/cyrilcolinet/eurevia-regate-rsmart-integration-hass" alt="License MIT"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-2025.1+-41BDF5?logo=home-assistant&logoColor=white" alt="Home Assistant 2025.1+"></a>
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="#entities">Entities</a> ·
  <a href="#mqtt-protocol">MQTT</a> ·
  <a href="#development">Development</a>
</p>

---

This integration connects Home Assistant to the **local MQTT broker** exposed by the [Eurevia reGATE](https://www.eurevia.com/rsmart/) hub (rSMART ecosystem). No cloud account — the reGATE pushes zone and HVAC state over MQTT; HA subscribes and publishes commands on the same topics.

## Why this integration?

- **Connection** — IP/hostname + port of the reGATE MQTT broker (default `1883`, prefix `local`)
- **Architecture** — Local hub (`iot_class: local_push`), lightweight async MQTT 3.1.1 client
- **Discovery** — Zones from `{prefix}/zones`, thermostats via Zigbee inventory + HVAC payloads
- **Auto-classification** — HVAC device IDs are inferred from payload key patterns (terminal, purifier, thermostat, actuator, system) — nothing hardcoded to `10` / `20`

> **Scope:** Eurevia reGATE / reSENS climatic zones, hydraulic terminal (Bloc CVC), air purifier. Third-party Zigbee devices paired outside the climatic stack are out of scope.

## Features

### Climate

- **Global thermostat** — sync mode, setpoint and boost (fan_mode) to all zones
- **Per-zone thermostat** — comfort / eco / reduced presets, target temperature, min/max limits

### Fan

- **Air purifier** on the hydraulic terminal — auto / mini / moyen / maxi presets

### Sensors

- **Terminal (Bloc CVC)** — water/air temperature, fan speed, valve command, PID config, …
- **Per zone** — humidity, battery, LQI, comms, firmware version, …

### Binary sensors

- **Window open** and **presence** per climatic zone

## Installation

### HACS (recommended)

1. **HACS** → **Integrations** → **⋮** → **Custom repositories**
2. URL: `https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass` — category **Integration**
3. **Explore & download repositories** → **Eurevia reGATE (rSmart)** → **Download**
4. **Restart** Home Assistant
5. **Settings** → **Devices & services** → **Add integration** → **Eurevia reGATE (rSmart)**

### Manual

Copy `custom_components/eurevia_regate_rsmart/` into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

| Field | Default | Description |
|-------|---------|-------------|
| Host | — | reGATE IP (find via `arp -a` → host `gatexway`, or reGATE app settings) |
| Port | `1883` | MQTT broker port |
| Prefix | `local` | Topic prefix (`local/zones`, `local/hvac/devices/…`) |

After setup, open **Configure** to select climatic zones, rename them and assign HA areas.

## Entities

| Platform | Device | Description |
|----------|--------|-------------|
| `climate` | Bloc CVC | Global thermostat + boost |
| `climate` | Zone | Per-room thermostat |
| `fan` | Bloc CVC | Air purifier |
| `sensor` | Bloc CVC / Zone | Terminal + zone diagnostics |
| `binary_sensor` | Zone | Window, presence |

## MQTT protocol

| Topic | Direction | Content |
|-------|-----------|---------|
| `{prefix}/zones` | Subscribe | JSON array of climatic zones |
| `{prefix}/zigbee/devices` | Subscribe | Zigbee inventory (thermostat filter) |
| `{prefix}/hvac/devices/+` | Subscribe | HVAC device state (retained) |
| `{prefix}/hvac/devices/{id}/set` | Publish | Commands (mode, setpoint, boost, purifier) |

Example command — set comfort 21.5 °C on zone HVAC device `102`:

```json
{"Mode": 1, "Stp_Comf": 21.5}
```

Global boost:

```json
{"Boost": true}
```

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest tests/unit -v
```

Live MQTT tests (optional, against your reGATE):

```bash
REGATE_MQTT_HOST=192.168.1.40 REGATE_MQTT_PREFIX=local pytest tests/integration -m integration -v
```

## Credits

- Logo from [Eurevia](https://www.eurevia.com) (`brand/logo-eurevia.svg`)
- Not affiliated with Eurevia — community integration, use at your own risk

## License

MIT — see [LICENSE](LICENSE).
