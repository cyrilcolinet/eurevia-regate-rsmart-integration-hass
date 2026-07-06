# Development

> **Disclaimer:** Unofficial community project — not affiliated with or endorsed by Eurevia. Maintainers are independent and do not work for Eurevia. [Full disclaimer](DISCLAIMER.md)

Technical documentation for contributing, testing, and releasing the integration.

## Prerequisites

- Python 3.12+
- Home Assistant 2025.1+ (for testing on a real instance)

```bash
git clone https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass.git
cd eurevia-regate-rsmart-integration-hass
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Unit and E2E tests

Without a reGATE on the network:

```bash
pytest tests/unit tests/e2e -v
```

E2E tests replay a **synthetic** MQTT snapshot in [`tests/fixtures/regate_snapshot.json`](../tests/fixtures/regate_snapshot.json) (fake IEEE addresses and setpoints — not tied to any real install).

To refresh the snapshot from your LAN (optional):

```bash
mosquitto_sub -h <regate-ip> -t 'local/zones' -C 1 > /tmp/zones.json
# Merge retained HVAC payloads into tests/fixtures/regate_snapshot.json manually
```

## Lint and format

```bash
ruff check .
ruff format --check .   # or ruff format . to fix
```

## Repository language

- **Python code** (comments, docstrings): English — see [CONTRIBUTING.md](../CONTRIBUTING.md#language)
- **Markdown** (`docs/`, `README.md`, …): English
- **Home Assistant UI** (`strings.json`, translations): French and English via translation files

## Testing in Home Assistant

Copy `custom_components/eurevia_regate_rsmart/` into your dev instance `config/custom_components/`, restart, add the integration via the UI.

## CI

Single workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

Triggered on every push to `main` and every pull request:

| Job | Role |
|-----|------|
| Lint | Ruff check + format |
| Unit tests | `pytest tests/unit tests/e2e` |
| Hassfest | HA integration validation |
| HACS | Repository validation (default store eligibility) |

## Publishing a release

1. Update `custom_components/eurevia_regate_rsmart/manifest.json` with the target version (e.g. `1.0.1`)
2. Tag and push:

```bash
git tag v1.0.1
git push origin v1.0.1
```

3. Create the **GitHub Release** from the tag — the [`release.yml`](../.github/workflows/release.yml) workflow attaches `eurevia_regate_rsmart.zip` with the tag version injected into the ZIP manifest (no automatic commit on the repo).

## Technical documentation

| Document | Content |
|----------|---------|
| [MQTT.md](MQTT.md) | reGATE local MQTT topics and payloads |
| [HACS.md](HACS.md) | HACS publication checklist |
| [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md) | Hardware and per-entity status |

## Code structure

Home Assistant requires **platform loaders** and `config_flow.py` at the root of `custom_components/eurevia_regate_rsmart/`. Everything else is organized by layer:

```
custom_components/eurevia_regate_rsmart/
├── __init__.py, manifest.json, config_flow.py, entity.py
├── climate.py, sensor.py, fan.py, binary_sensor.py, diagnostics.py
├── const.py, exceptions.py, strings.json, translations/, brand/
│
├── mqtt/                   # async MQTT 3.1.1 client
│   └── client.py
│
└── lib/                    # pure functions (minimal HA import)
    ├── capabilities.py     # HVAC role auto-discovery
    ├── field_registry.py   # dynamic sensor specs
    ├── mapping.py          # mode / preset conversion
    └── conversion.py
```

Platforms registered in `__init__.py` → `PLATFORMS`: `binary_sensor`, `climate`, `fan`, `number`, `sensor`.

### Import conventions

| Package | Role |
|---------|------|
| `lib.capabilities` | MQTT payload → HVAC device profile |
| `lib.field_registry` | Known MQTT keys → sensor metadata |
| `lib.mapping` | Mode integers ↔ HA presets |
| `mqtt.client` | Subscribe / publish to reGATE broker |

Device roles (terminal, purifier, thermostat, …) are inferred from MQTT payload key patterns — never hardcode HVAC device IDs in platform code.

See also [CONTRIBUTING.md](../CONTRIBUTING.md) for PR conventions.
