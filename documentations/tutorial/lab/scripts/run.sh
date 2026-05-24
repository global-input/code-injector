#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CODE_INJECTOR_ROOT="$(cd "$LAB_DIR/../../.." && pwd)"

export HELLO_APP_FOLDER="$LAB_DIR/app"
export PYTHONPATH="$CODE_INJECTOR_ROOT:$LAB_DIR/driver:$LAB_DIR/definition${PYTHONPATH:+:$PYTHONPATH}"

python3 "$LAB_DIR/driver/main.py" --app hello --job boot_reached --branch main --version 1.0.0 --env dev
echo "Injected boot marker into app/src/app.js."

