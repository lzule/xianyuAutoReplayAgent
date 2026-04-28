#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_TESTS=1
if [[ "${1:-}" == "--skip-tests" ]]; then
  RUN_TESTS=0
fi

echo "[preflight] step 1/3 privacy scan"
bash scripts/privacy_scan.sh

echo "[preflight] step 2/3 docs check"
if [[ ! -f CHANGELOG.md ]]; then
  echo "[preflight] failed: CHANGELOG.md not found."
  exit 1
fi

if [[ ! -d docs/changes ]]; then
  echo "[preflight] failed: docs/changes/ not found."
  exit 1
fi

echo "[preflight] step 3/3 test check"
if [[ "$RUN_TESTS" -eq 1 ]]; then
  if command -v pytest >/dev/null 2>&1; then
    pytest -q
  else
    echo "[preflight] skipped: pytest not installed."
  fi
else
  echo "[preflight] skipped by flag: --skip-tests"
fi

echo "[preflight] passed."
