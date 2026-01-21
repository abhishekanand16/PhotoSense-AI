#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 -m PyInstaller backend.spec --clean --noconfirm --distpath "src-tauri/bin" --workpath "build"
