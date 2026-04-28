#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v rg >/dev/null 2>&1; then
  echo "[privacy-scan] error: rg (ripgrep) is required."
  exit 2
fi

echo "[privacy-scan] scanning repository for sensitive patterns..."

EXCLUDES=(
  "--glob=!.git/*"
  "--glob=!.env.example"
  "--glob=!docs/changes/*.md"
  "--glob=!docs/**"
  "--glob=!CHANGELOG.md"
  "--glob=!README.md"
  "--glob=!tests/**"
  "--glob=!scripts/privacy_scan.sh"
  "--glob=!*.png"
  "--glob=!*.jpg"
  "--glob=!*.jpeg"
  "--glob=!*.gif"
  "--glob=!*.pdf"
  "--glob=!*.db"
  "--glob=!*.sqlite3"
)

PATTERNS=(
  "COOKIES_STR\\s*=\\s*[^\\s\"']{20,}"
  "_m_h5_tk=[A-Za-z0-9%._-]{16,}"
  "_m_h5_tk_enc=[A-Za-z0-9%._-]{16,}"
  "cookie2=[A-Za-z0-9%._-]{12,}"
  "sgcookie=[A-Za-z0-9%._-]{12,}"
  "unb=[0-9]{8,}"
  "cna=[A-Za-z0-9%._-]{8,}"
  "https?://open\\.feishu\\.cn/open-apis/bot/v2/hook/[A-Za-z0-9-]{16,}"
  "1[3-9][0-9]{9}"
)

FOUND=0
for pattern in "${PATTERNS[@]}"; do
  set +e
  rg -n -S "${EXCLUDES[@]}" -- "$pattern" . >/tmp/privacy_scan_hits.txt
  RC=$?
  set -e
  if [[ "$RC" -eq 0 ]]; then
    echo "[privacy-scan] matched pattern: $pattern"
    cat /tmp/privacy_scan_hits.txt
    FOUND=1
  elif [[ "$RC" -ne 1 ]]; then
    echo "[privacy-scan] error: rg failed for pattern $pattern"
    cat /tmp/privacy_scan_hits.txt || true
    rm -f /tmp/privacy_scan_hits.txt
    exit 2
  fi
done

rm -f /tmp/privacy_scan_hits.txt

if [[ "$FOUND" -eq 1 ]]; then
  echo "[privacy-scan] failed: sensitive content detected."
  exit 1
fi

echo "[privacy-scan] passed."
