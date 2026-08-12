# Release — trunk + release-please

## Flow

```
feat/fix/* ──PR──► main ──► CI (ruff, pytest, HACS, Hassfest)
                    │
                    └──► release-please (PR "chore: release X.Y.Z")
                              │
                         merge ──► tag vX.Y.Z + GitHub Release + zip
```

| Step | Trigger | Result |
|------|---------|--------|
| Integration | Merge PR → `main` | CI green |
| Version | Merge release-please PR | Tag + GitHub Release + `CHANGELOG.md` + `manifest.json` bump |
| HACS asset | Same workflow (`publish-release` job) | `eurevia_regate_rsmart.zip` uploaded; install note appended via `append_body` |
| Issues | Merge release-please PR | Open issues labelled `pending release` → `released` + comment |

Uses the default `GITHUB_TOKEN` only — no App secrets. release-please creates
the GitHub Release; `softprops/action-gh-release` uploads the zip and appends
the install note in one step.

## Workflows

| Workflow | Role |
|----------|------|
| **CI** | Lint, tests, HACS validation, Hassfest on PR and push `main` |
| **CodeQL** | Security analysis (python) on PR, push `main`, weekly |
| **Pending release** | Label issues referenced by a merged PR `pending release` |
| **Release please** | Release PR, tag, GitHub Release, zip, install note, `released` relabel |
| **Stale** | Mark inactive issues / PRs `stale` weekly |

## Conventional Commits

PR titles / commits (imperative):

```
feat(config): add reconfigure flow to edit host/port/prefix
fix(telemetry): skip actuator-only repair false positives
```

release-please fills `CHANGELOG.md` and the GitHub Release body (Features / Bug
Fixes sections). Squash merges should keep a conventional PR title so the squash
commit is parseable.

## release-please config

Files: `release-please-config.json`, `.release-please-manifest.json`.

| Option | Role |
|--------|------|
| `bootstrap-sha` | Start point for the changelog — only commits **after** this SHA are included |
| `exclude-paths` | Commits touching only `.github/`, `docs/`, `scripts/`, or `tests/` do not bump the version |
| `extra-files` | Bumps `custom_components/eurevia_regate_rsmart/manifest.json` → `version` |
| `label` / `release-label` | `pending release` → `released` after merge |

One-off version override: empty commit on `main` with `Release-As: 1.7.0` in the
message (release-please honours the requested version).

After changing `bootstrap-sha`, close the open release PR and let release-please
open a fresh one on the next `feat`/`fix`.

## Issue lifecycle

1. A PR merges with `Refs #N` / `Fixes #N` → **Pending release** labels `#N`
   `pending release`.
2. The release-please PR merges and ships → **Release please** relabels `#N`
   `released`, comments the version, and leaves it open for the maintainer to
   close.

## Manual zip re-upload

If `eurevia_regate_rsmart.zip` is missing from a release:

```bash
git checkout vX.Y.Z
cd custom_components/eurevia_regate_rsmart && zip -r eurevia_regate_rsmart.zip .
gh release upload vX.Y.Z eurevia_regate_rsmart.zip --clobber
```

## HACS

After the GitHub Release is published:

1. HACS shows an **Update** badge when a new release exists
2. Users click **Update**, then restart Home Assistant

See [HACS.md](HACS.md).
