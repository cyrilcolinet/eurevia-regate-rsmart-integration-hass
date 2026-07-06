# Contributing

> **Disclaimer:** Unofficial community project — not affiliated with or endorsed by Eurevia. Maintainers are independent and do not work for Eurevia. [Full disclaimer](docs/DISCLAIMER.md)

Thanks for contributing. For local setup, tests, and CI, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Before you code

1. Check [open issues](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/issues)
2. New MQTT device pattern: open a **feature request** with a redacted diagnostics export or sample payload
3. Protocol context: [docs/MQTT.md](docs/MQTT.md)

## Quality bar

Before any PR:

```bash
ruff check .
ruff format .
pytest tests/unit -v
```

CI runs the same checks plus Hassfest and HACS.

## Code layout

- **`lib/`** — discovery, mapping, conversion, field registry (no Home Assistant imports except `field_registry`)
- **`mqtt/`** — async MQTT 3.1.1 client
- **Root** — HA platform loaders + config flow — full list in `__init__.py` → `PLATFORMS`

Device roles (terminal, purifier, thermostat, …) are inferred from MQTT payload key patterns — never hardcode HVAC device IDs in platform code.

## Language

- **Python code** (comments, docstrings, symbol names): **English**
- **Markdown documentation** (`README.md`, `docs/`, `CONTRIBUTING.md`, …): **English**
- **Home Assistant UI strings** (config flow, `strings.json`, translations): **French and English** via HA translation files (`translations/fr.json`, `translations/en.json`)

## Pull requests

- One PR = one topic
- Conventional commits (`fix:`, `feat:`, `docs:`)
- Unit tests for changed logic
- No credentials in code or commits

Template: [.github/pull_request_template.md](.github/pull_request_template.md)
