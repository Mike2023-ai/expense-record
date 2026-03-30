#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
FLASK_BIN="$VENV_DIR/bin/flask"
APP_URL="http://127.0.0.1:5000"

cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found in PATH." >&2
  exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

if ! "$PYTHON_BIN" -c "import flask, expense_record" >/dev/null 2>&1; then
  echo "Installing project dependencies into $VENV_DIR"
  "$PYTHON_BIN" -m pip install -e ".[dev]"
fi

echo "Starting Expense Screenshot Tool at $APP_URL"
exec "$FLASK_BIN" --app expense_record.app run
