# HACS publication

Checklist aligned with the [official HACS documentation](https://www.hacs.xyz/docs/publish/).

## Custom repository (current install)

Until inclusion in the default store, users add the repo manually or via the **Open in HACS** badge.

1. **Public** GitHub repository
2. [`hacs.json`](../hacs.json) at the root with at least `name`
3. `custom_components/eurevia_regate_rsmart/` structure with `manifest.json`
4. Installation README
5. [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) workflow (lint, tests, HACS, Hassfest) **without errors**

### Quick install link (my.home-assistant.io)

After publishing the repo, generate a link:

[Create a HACS link](https://my.home-assistant.io/create-link/?redirect=hacs_repository&owner=cyrilcolinet&repository=eurevia-regate-rsmart-integration-hass&category=integration)

Example Markdown for the README:

```markdown
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyrilcolinet&repository=eurevia-regate-rsmart-integration-hass&category=integration)
```

## GitHub metadata (required for HACS)

Configure on the repository **Settings** page:

| Field | Example |
|-------|---------|
| **Description** | Home Assistant integration for the Eurevia reGATE (rSMART) hub — local MQTT multi-zone heating, air purifier, and diagnostics. |
| **Topics** | `home-assistant`, `hacs`, `hacs-integration`, `eurevia`, `regate`, `rsmart`, `mqtt`, `smart-home`, `home-automation`, `iot`, `heating`, `climate` |
| **Issues** | Enabled |

## Releases (recommended)

HACS shows the last 5 releases when they exist.

1. Create a semantic tag (`v1.0.1`) aligned with `custom_components/eurevia_regate_rsmart/manifest.json`
2. Publish a **GitHub Release** (not just a tag)
3. The [`release.yml`](../.github/workflows/release.yml) workflow attaches `eurevia_regate_rsmart.zip` with the tag version injected into the ZIP manifest — update `manifest.json` in git manually before tagging

## Default HACS store

Procedure: [Include default repositories](https://www.hacs.xyz/docs/publish/include/)

**Repository status:** technical prerequisites are covered by CI on every push/PR:

| Prerequisite | Status |
|-----------|--------|
| **HACS** action (`hacs/action`, no `ignore: brands`) | ✅ [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| **Hassfest** action | ✅ same |
| `hacs.json` + `country: FR` | ✅ [`hacs.json`](../hacs.json) |
| At least **one** GitHub release | ✅ [releases](https://github.com/cyrilcolinet/eurevia-regate-rsmart-integration-hass/releases) |
| Brand `custom_components/eurevia_regate_rsmart/brand/` | ✅ `icon.png` (128) + `icon@2x.png` (256) |

**Remaining publication step:** PR on [hacs/default](https://github.com/hacs/default) (`integration` file), **alphabetical** entry: `cyrilcolinet/eurevia-regate-rsmart-integration-hass`.

## Local validation

Same checks as the **CI** workflow (ruff, pytest, Hassfest, HACS action) on every push/PR. On GitHub: **Actions** tab → **CI** workflow.
