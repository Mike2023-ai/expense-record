# Expense Screenshot Tool

## Quick Start

Run the app with:

```bash
./run.sh
```

The script creates `.venv` if needed, installs dependencies when missing, prints the local URL, and starts the Flask app.

## Setup

If you prefer manual setup:

1. Create a virtual environment.
2. Install the project in editable mode with the dev extras:

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
