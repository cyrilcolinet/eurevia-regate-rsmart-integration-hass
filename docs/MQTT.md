# MQTT protocol

Technical reference for the reGATE local MQTT API used by this integration.

## Broker

| Setting | Default | Notes |
|---------|---------|-------|
| Host | reGATE LAN IP | Often `gatexway` in ARP / DHCP |
| Port | `1883` | Plain MQTT (no TLS in current integration) |
| Prefix | `local` | Configurable in HA config flow |

## Topics

| Topic | Direction | Content |
|-------|-----------|---------|
| `{prefix}/zones` | Subscribe | JSON array of climatic zones |
| `{prefix}/zigbee/devices` | Subscribe | Zigbee inventory (thermostat filter) |
| `{prefix}/hvac/devices/+` | Subscribe | HVAC device state (retained) |
| `{prefix}/hvac/devices/{id}/set` | Publish | Commands (mode, setpoint, boost, purifier) |

Payloads are JSON objects. HVAC state topics use a numeric or string device id as the final segment.

## Device role detection

Roles are inferred from keys present in each `{prefix}/hvac/devices/{id}` payload ([`lib/capabilities.py`](../custom_components/eurevia_regate_rsmart/lib/capabilities.py)):

| Role | Signature keys |
|------|----------------|
| Thermostat | `Mode`, `Stp_Comf`, `Tmp`, valid `Th_ID` |
| Terminal | `Water_Temp`, `Air_Temp`, `Valve_Cmd`, `Assembly`, `Fan_Speed`, … |
| Purifier | `P_Mode` |
| Actuator | `Pos_Min`, `Window` |
| System | `Heating_Mode`, `PAC` |
| Scheduler | `Day`, `Night`, `Stp` |

A device may match multiple roles. The integration picks command/read IDs for terminal, purifier and thermostats at discovery time.

## Command examples

Set comfort 21.5 °C on zone HVAC device `102`:

```json
{"Mode": 1, "Stp_Comf": 21.5}
```

Global boost:

```json
{"Boost": true}
```

Air purifier preset (values depend on reGATE firmware):

```json
{"P_Mode": 2}
```

Mode integers and preset mapping: [`lib/mapping.py`](../custom_components/eurevia_regate_rsmart/lib/mapping.py).

## Live debugging

From a machine on the same LAN:

```bash
mosquitto_sub -h <regate-ip> -t 'local/#' -v
```

Or with the integration test harness ([DEVELOPMENT.md](DEVELOPMENT.md#live-mqtt-tests-optional)):

```bash
REGATE_MQTT_HOST=192.168.1.40 REGATE_MQTT_PREFIX=local pytest tests/integration -m integration -v
```

## Related docs

| Document | Content |
|----------|---------|
| [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md) | HA entities per device type |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Tests and CI |
