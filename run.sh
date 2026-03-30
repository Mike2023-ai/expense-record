#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
APP_URL="http://127.0.0.1:5000"

cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found in PATH." >&2
  exit 1
fi

check_python_version() {
  local python_bin="$1"
  local python_label="$2"
  local python_version

  python_version="$("$python_bin" -c 'import sys; print(".".join(str(part) for part in sys.version_info[:3]))')"
  if ! "$python_bin" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
    echo "$python_label 3.12 or newer is required; found $python_version." >&2
    exit 1
  fi
}

check_imports() {
  "$1" -c 'import flask, expense_record, openpyxl, rapidocr_onnxruntime'
}

check_python_version python3 "python3"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

check_python_version "$PYTHON_BIN" ".venv/bin/python"

if ! check_imports "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Installing project dependencies into $VENV_DIR"
  "$PYTHON_BIN" -m pip install -e ".[dev]"
fi

echo "Starting Expense Screenshot Tool at $APP_URL"
exec "$PYTHON_BIN" -m flask --app expense_record.app run
