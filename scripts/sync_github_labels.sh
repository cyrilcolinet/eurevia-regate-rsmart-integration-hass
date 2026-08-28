#!/usr/bin/env bash
# Reconcile the repository's GitHub labels with scripts/github_labels.py.
# Upserts every defined label (create or edit) and deletes orphaned ones.
# Requires the `gh` CLI authenticated against this repository.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "${ROOT}/scripts/github_labels.py" | while IFS=$'\t' read -r action name color description; do
  case "${action}" in
    upsert)
      if gh label create "${name}" --color "${color}" --description "${description}" 2>/dev/null; then
        echo "created  ${name}"
      else
        gh label edit "${name}" --color "${color}" --description "${description}"
        echo "updated  ${name}"
      fi
      ;;
    delete)
      if gh label delete "${name}" --yes 2>/dev/null; then
        echo "deleted  ${name}"
      else
        echo "absent   ${name}"
      fi
      ;;
  esac
done
