#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p src
if ! command -v vcs >/dev/null 2>&1; then
  echo "[ERR] vcs not found. Install python3-vcstool first." >&2
  exit 1
fi
vcs import src < third_party.repos

echo "[OK] third-party repositories imported."
echo "[NOTE] If lf_sentry submodules are required, run: git -C src/lf_sentry submodule update --init --recursive"
