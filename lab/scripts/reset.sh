#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cp "$LAB_DIR/app/src/app.original.js" "$LAB_DIR/app/src/app.js"
echo "Reset lab app."

