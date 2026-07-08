<p align="center">
  <img src="https://raw.githubusercontent.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/main/custom_components/eurevia_regate_rsmart/brand/icon.png" alt="Eurevia" width="128" height="128">
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
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=eurevia-regate-rsmart-integration-hass&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS">
  </a>
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="docs/SUPPORTED_DEVICES.md">Devices</a> ·
  <a href="docs/ROADMAP.md">Roadmap</a> ·
  <a href="https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/releases">Releases</a> ·
  <a href="https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/issues/new?template=bug.yml">Bug</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

> **Disclaimer — unofficial project:** This is a community-maintained integration. It is **not** official, **not** affiliated with, and **not** endorsed by [Eurevia](https://www.eurevia.com). The author and maintainers are **independent** and do **not** work for Eurevia. Full details: [docs/DISCLAIMER.md](docs/DISCLAIMER.md).

The [Eurevia reGATE](https://www.eurevia.com/rsmart/) hub (rSMART ecosystem) exposes a **local MQTT broker**. This integration connects Home Assistant to that broker — no cloud account. Zone and HVAC state is pushed over MQTT; HA subscribes and publishes commands on the same topics.

## Why this integration?

- **Connection** — IP/hostname + port of the reGATE MQTT broker (default `1883`, prefix `local`)
- **Requirements** — reGATE online, climatic zones configured in the rSMART app
- **Architecture** — Local hub (`iot_class: local_push`), lightweight async MQTT 3.1.1 client
- **Discovery** — Zones from `{prefix}/zones`, thermostats via Zigbee inventory + HVAC payloads
- **Auto-classification** — HVAC device IDs inferred from payload key patterns (terminal, purifier, thermostat, …) — nothing hardcoded to `10` / `20`

> **Out of scope:** third-party Zigbee devices paired outside the Eurevia climatic stack → use [Zigbee2MQTT](https://www.zigbee2mqtt.io/) or ZHA. Only reGATE / reSENS climatic zones, hydraulic terminal (Bloc CVC), and integrated air purifier are supported.

## Features

### Supported

- **Global thermostat** — sync mode, setpoint and boost (`fan_mode`) to all zones
- **Per-zone thermostat** — comfort / eco / reduced presets, target temperature, min/max limits, writable setpoints (`number`)
- **Air purifier** on the hydraulic terminal — auto / mini / moyen / maxi presets (`fan`)
- **Terminal (Bloc CVC)** — water/air temperature, fan speed, valve command, PID config, … (`sensor`)
- **Per zone** — humidity, battery, LQI, comms, firmware version, … (`sensor`)
- **Window open** and **presence** per climatic zone (`binary_sensor`)
- **MQTT connectivity** diagnostic sensor on Bloc CVC (`sensor`)

### Beta

- **Actuator / scheduler / system** HVAC roles — discovered and logged; no HA entities yet

Per-device detail: [docs/SUPPORTED_DEVICES.md](docs/SUPPORTED_DEVICES.md) · History: [docs/ROADMAP.md](docs/ROADMAP.md)

## Installation

### HACS (recommended)

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=eurevia-regate-rsmart-integration-hass&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS">
  </a>
</p>

1. **HACS** → **Integrations** → **⋮** → **Custom repositories**
2. URL: `https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass` — category **Integration**
3. **Explore & download repositories** → **Eurevia reGATE (rSmart)** → **Download**
4. **Restart** Home Assistant

Default HACS store (goal): [docs/HACS.md](docs/HACS.md#default-hacs-store)

### Add the integration

1. **Settings** → **Devices & services** → **Add integration**
2. Search for **Eurevia reGATE (rSmart)** — enter reGATE host, port and topic prefix
3. Open **Configure** to select climatic zones, rename them and assign HA areas

### Manual install

Download a [release](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/releases) or clone this repo, copy `custom_components/eurevia_regate_rsmart/` into `config/custom_components/`, restart HA.

## Configuration

**Settings** → **Devices & services** → **Eurevia reGATE (rSmart)** → **Configure**

| Field | Default | Description |
|-------|---------|-------------|
| Host | — | reGATE IP (find via `arp -a` → host `gatexway`, or reGATE app settings) |
| Port | `1883` | MQTT broker port |
| Prefix | `local` | Topic prefix (`local/zones`, `local/hvac/devices/…`) |

- **Zone selection** — Enable/disable climatic zones, custom names, HA areas
- **Reconfigure** — Change host, port or prefix

## Troubleshooting

- **Cannot connect** — Verify reGATE IP and port; broker must be reachable from Home Assistant (same LAN)
- **No zones** — Check topic prefix matches reGATE config (default `local`); zones must appear in the rSMART app
- **Missing entities** — HVAC devices appear when retained MQTT payloads are received; restart integration after reGATE reboot
- **Bug** — [Issue](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/issues/new?template=bug.yml) + `custom_components.eurevia_regate_rsmart` logs

## Resources

- 📋 [Supported devices & entities](docs/SUPPORTED_DEVICES.md)
- 🗺️ [Roadmap](docs/ROADMAP.md)
- ⚠️ [Disclaimer — unofficial project](docs/DISCLAIMER.md)
- 📡 [MQTT protocol](docs/MQTT.md)
- 📊 [Device telemetry (opt-in)](docs/TELEMETRY.md)
- 🛠️ [Development](docs/DEVELOPMENT.md)
- 🏠 [Eurevia rSMART](https://www.eurevia.com/rsmart/)

## Credits & license

Unofficial community integration — see [docs/DISCLAIMER.md](docs/DISCLAIMER.md). Local MQTT bridge, subject to reGATE firmware changes.

- Maintainer: [@cyrilcolinet](https://github.com/cyrilcolinet) — independent, not an Eurevia employee
- Logo from [Eurevia](https://www.eurevia.com) (`brand/icon.png`) — trademark identification only

[MIT](LICENSE) license
