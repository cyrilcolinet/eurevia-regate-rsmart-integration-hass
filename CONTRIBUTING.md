# Contributing

## Before you code

1. Check [open issues](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/issues)
2. For new MQTT device patterns, attach a redacted diagnostics export or sample payload

## Quality bar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
ruff format .
pytest tests/unit -v
```

CI runs the same checks plus Hassfest and HACS.

## Code layout

- **`lib/`** — pure discovery, mapping, conversion (no Home Assistant imports except `field_registry`)
- **`mqtt/`** — async MQTT 3.1.1 client
- **Root** — HA platform loaders + config flow

Device roles (terminal, purifier, thermostat, …) are inferred from MQTT payload key patterns — never hardcode HVAC device IDs in platform code.

## Language

- **Python code**: English
- **HA UI strings**: French and English via `strings.json` + `translations/`
