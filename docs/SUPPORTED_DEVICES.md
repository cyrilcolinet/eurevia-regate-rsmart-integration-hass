# Supported devices and features

Detail by device type and Home Assistant entities created. HVAC device roles are detected from MQTT **payload key patterns** (see [`lib/capabilities.py`](../custom_components/eurevia_regate_rsmart/lib/capabilities.py)), not hardcoded device IDs.

| | |
|---|---|
| **Latest GitHub release** | [releases](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/releases/latest) |
| **Repository `manifest.json`** | 1.0.0 |

Summary: [ROADMAP.md](ROADMAP.md)

## Scope

This integration covers the **Eurevia reGATE / rSMART climatic stack**:

- Climatic zones (reSENS thermostats, window / presence)
- Hydraulic terminal — **Bloc CVC** (water loop, fan, valve)
- Integrated **air purifier** on the terminal (when `P_Mode` is present in MQTT)

**Out of scope:** Zigbee devices paired on the reGATE outside the climatic ecosystem (Sonoff, Tuya, Aqara, …) → **Zigbee2MQTT** or **ZHA**.

## Climatic zones

Zones are listed on `{prefix}/zones`. Each enabled zone gets a device in Home Assistant after configuration.

**HA entities:** `climate`, `binary_sensor`, `sensor`

| Function | Detail |
|----------|--------|
| Mode | Comfort / eco / reduced / off (mapped from MQTT `Mode`) |
| Setpoint | Target temperature per preset (`Stp_Comf`, `Stp_Eco`, `Stp_Red`) |
| Limits | Min/max setpoint when advertised |
| Window | `binary_sensor` from `Window` / window-open key |
| Presence | `binary_sensor` from occupancy key |
| Humidity | `sensor` when `RH` is in the zone HVAC payload |
| Diagnostics | Battery, LQI, voltage, firmware (`SW_Version`), comms flags — only if keys are present |

Sensors are created **dynamically** from discovered MQTT keys ([`lib/field_registry.py`](../custom_components/eurevia_regate_rsmart/lib/field_registry.py)).

## Global thermostat (Bloc CVC)

**HA entity:** `climate` on the hydraulic terminal device

| Function | Detail |
|----------|--------|
| Mode | Broadcast to all zones |
| Setpoint | Global comfort temperature |
| Boost | HA `fan_mode` → MQTT `Boost` (purifier / fan boost) |

Commands published to `{prefix}/hvac/devices/{id}/set` on the terminal command device (auto-discovered).

## Per-zone thermostats

**HA entity:** `climate` per climatic zone

| Function | Detail |
|----------|--------|
| Presets | Comfort, eco, reduced |
| Temperature | Current + target from zone HVAC payload |
| Detection | Thermostat role when payload matches `Mode` + `Stp_Comf` + `Tmp` + valid `Th_ID` |

Thermostat HVAC device IDs come from `{prefix}/zigbee/devices` inventory filtered by payload shape — not a fixed list.

## Air purifier

**HA entity:** `fan` on the Bloc CVC device (only if a purifier command device is discovered)

| Function | Detail |
|----------|--------|
| Presets | auto, mini, moyen, maxi (from `P_Mode`) |
| Discovery | Device with `P_Mode` in retained HVAC payload |

## Terminal sensors (Bloc CVC)

**HA entities:** `sensor` (diagnostic / measurement)

Created when matching keys appear on the terminal HVAC payload:

| MQTT key | HA surface |
|----------|------------|
| `Water_Temp`, `Air_Temp` | Temperature (°C) |
| `Fan_Speed`, `Valve_Cmd`, `Valve_Cmd_Corrected` | Percentage |
| `Water_Hot`, `Water_Cold`, `Fan_Min`, `Fan_Max` | Config / setpoints |
| `PID_Enable`, `PID_T_Integral`, `PID_T_Derivate`, `DB`, `Hyst` | PID tuning |
| `P_Timer_Left` | Purifier timer (minutes) |
| `Mode`, `Fan_Mode`, `Fan_Cmd` | Raw mode integers |

Full registry: [`lib/field_registry.py`](../custom_components/eurevia_regate_rsmart/lib/field_registry.py).

## Cross-cutting features

- **Auto-discovery** — HVAC profiles recomputed when new retained payloads arrive (`SIGNAL_DISCOVERY_UPDATED`)
- **Local MQTT** — No cloud; broker on the reGATE LAN IP
- **Diagnostics** — JSON export from integration UI (redact host if sharing publicly)

## Discovered but not exposed (yet)

| Role | Signature keys | Status |
|------|----------------|--------|
| Actuator | `Pos_Min`, `Window` | 🔬 Logged only |
| System | `Heating_Mode`, `PAC` | 🔬 Logged only |
| Scheduler | `Day`, `Night`, `Stp` | 🔬 Logged only |

MQTT detail: [MQTT.md](MQTT.md)
