# run.sh Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a root-level `run.sh` that creates or reuses the virtualenv, installs dependencies if needed, and starts the local expense screenshot tool.

**Architecture:** Use one small POSIX shell script at the repository root. The script should resolve the repo root relative to itself, create `.venv` if missing, perform a lightweight dependency check by importing Flask and the local package from the virtualenv, install `.[dev]` only when needed, print the local URL, and then start Flask with `expense_record.app`.

**Tech Stack:** POSIX shell, Python virtualenv, pip, Flask

---

## File Structure

- Create: `run.sh`
- Modify: `README.md`

## Task 1: Add the launcher script and usage note

**Files:**
- Create: `run.sh`
- Modify: `README.md`

- [ ] **Step 1: Write the failing verification command**

Run:

```bash
bash ./run.sh
```

Expected: FAIL with `No such file or directory`

- [ ] **Step 2: Implement the launcher script**

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
```

- [ ] **Step 3: Update the README with the one-command launcher**

```markdown
# Expense Screenshot Tool

## Quick Start

Run the app with:

```bash
./run.sh
```

The script creates `.venv` if needed, installs dependencies when missing, and starts the Flask app.

## Setup

If you prefer manual setup:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Run

```bash
.venv/bin/flask --app expense_record.app run
```

## Excel Path

Saved rows go to `~/.expense-screenshot-tool/expenses.xlsx` by default. Override the workbook path with:

```bash
export EXPENSE_RECORD_EXCEL_PATH=/absolute/path/to/expenses.xlsx
```

## Test

```bash
.venv/bin/pytest tests/test_api.py::test_index_page_loads_from_installed_package -v
```
```

- [ ] **Step 4: Make the launcher executable**

Run:

```bash
chmod +x run.sh
```

Expected: command succeeds with no output

- [ ] **Step 5: Verify the script parses and the README still reads correctly**

Run:

```bash
bash -n run.sh
```

Expected: PASS with no output

Run:

```bash
sed -n '1,80p' README.md
```

Expected: shows the new `./run.sh` quick-start section

- [ ] **Step 6: Commit**

```bash
git add run.sh README.md
git commit -m "feat: add one-command launcher script"
```

## Self-Review

### Spec coverage

- Root `run.sh`: covered by Task 1 Step 2
- Reuse or create `.venv`: covered by Task 1 Step 2
- Install `.[dev]` when dependencies are missing: covered by Task 1 Step 2
- Start Flask with `expense_record.app`: covered by Task 1 Step 2
- Preserve `EXPENSE_RECORD_EXCEL_PATH`: covered implicitly because the script does not override it
- Print app URL before start: covered by Task 1 Step 2
- README usage note: covered by Task 1 Step 3

### Placeholder scan

No placeholders or deferred steps remain.

### Type consistency

- Script consistently uses `ROOT_DIR`, `VENV_DIR`, `PYTHON_BIN`, and `FLASK_BIN`
- README examples match the script and existing app entrypoint
