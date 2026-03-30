# Expense Screenshot Tool

## Setup

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

## Test

```bash
.venv/bin/pytest tests/test_api.py::test_index_page_loads -v
```
