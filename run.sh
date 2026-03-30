#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
FLASK_BIN="$VENV_DIR/bin/flask"
APP_URL="http://127.0.0.1:5000"
REQUIRED_IMPORTS=(flask expense_record openpyxl rapidocr_onnxruntime)

cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found in PATH." >&2
  exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print(".".join(str(part) for part in sys.version_info[:3]))')"
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "python3 3.12 or newer is required; found $PYTHON_VERSION." >&2
  exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

if ! "$PYTHON_BIN" -c 'import importlib.util, sys
missing = [name for name in sys.argv[1:] if importlib.util.find_spec(name) is None]
raise SystemExit(1 if missing else 0)' "${REQUIRED_IMPORTS[@]}" >/dev/null 2>&1; then
  echo "Installing project dependencies into $VENV_DIR"
  "$PYTHON_BIN" -m pip install -e ".[dev]"
fi

echo "Starting Expense Screenshot Tool at $APP_URL"
exec "$FLASK_BIN" --app expense_record.app run
