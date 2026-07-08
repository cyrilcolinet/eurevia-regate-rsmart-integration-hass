# Device profile sharing (opt-in)

> **Disclaimer:** Unofficial community project — not affiliated with or endorsed by Eurevia. Maintainers are independent and do not work for Eurevia. [Full disclaimer](DISCLAIMER.md)

Helps extend reGATE MQTT support **without automatic uploads** and **without secrets**.

## For users

### Diagnostics (no opt-in)

**Settings** → **Devices & services** → **Eurevia reGATE** → ⋮ menu → **Download diagnostics**

Local JSON export: anonymized HVAC profiles (roles, MQTT key names). Attach to an [issue](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/issues/new) if needed.

### Opt-in (notification + pre-filled issue)

During setup or under **reGATE → Configure**, enable:

> Notify me about new or unsupported devices (anonymized; pre-filled GitHub link only — nothing sent without your click)

When a **new** MQTT profile is detected (unique fingerprint) **and support is missing** (unknown keys, unimplemented role such as actuator/system/scheduler):

1. A **persistent notification** appears in Home Assistant
2. The link opens GitHub with a **pre-filled** title and body
3. You **confirm** issue creation — nothing is sent without that click

**Never included:** broker host/IP, zone names, thermostat IDs (`Th_ID`, `Th_Name`).

**Repair issues (Settings → Repairs):** prolonged MQTT disconnect (10 min), silent broker (15 min without messages), unsupported HVAC profiles when telemetry is enabled.

**Diagnostics:** unsupported profiles include a `github_issue_url` field (pre-filled link, nothing sent automatically).

**No notification** if the profile is already fully supported (e.g. a zone thermostat with only known keys).

### Enriched export

Diagnostics and GitHub prefill include:

| Field | Meaning |
|-------|---------|
| `roles` | Detected HVAC roles (`thermostat`, `terminal`, `system`, …) |
| `mqtt_keys` | Key names seen on the device (values excluded) |
| `unknown_keys` | Keys not mapped by the integration yet |
| `ha_platforms` | HA platforms planned or active for these roles |
| `telemetry_reason` | Why a notification was suggested |

## For contributors

See [DEVELOPMENT.md](DEVELOPMENT.md) for unit/E2E tests.

## Technical

- Deduplication by SHA256 fingerprint (local HA storage)
- URL: `github.com/.../issues/new?title=...&body=...&labels=device-telemetry`
- No token, no outbound HTTP from Home Assistant
