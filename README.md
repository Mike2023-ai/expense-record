# Family Finance Tool

This app combines three input paths into one local workbook-driven finance tool:

- phone screenshot OCR for one or more transactions
- WeChat `.xlsx` statement import
- Alipay `.csv` statement import

The current version lets you review imported rows, assign `category` and `member`, save manual entries, record monthly asset snapshots, record stock positions, and review dashboard summaries for:

- expense by category
- member by category
- monthly cash flow
- asset trend

## Quick Start

Run the app with:

```bash
./run.sh
```

The script creates `.venv` if needed, installs dependencies when missing, prints the local URL, and starts the Flask app.

## Manual Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Run

```bash
.venv/bin/flask --app expense_record.app run
```

## Workbook Path

The app stores data in `~/.expense-screenshot-tool/expenses.xlsx` by default. Override it with:

```bash
export EXPENSE_RECORD_EXCEL_PATH=/absolute/path/to/expenses.xlsx
```

The workbook now contains separate sheets for:

- raw OCR expense rows
- normalized family ledger entries
- categories
- members
- asset snapshots
- stock records

## Main Workflow

1. Import a WeChat or Alipay statement file, or paste/upload a screenshot.
2. Review the extracted rows.
3. For statement rows, choose both `category` and `member` before saving.
4. Save the selected rows into the workbook.
5. Add manual entries for salary, rent, transfers, or anything not coming from imports.
6. Record monthly asset snapshots and stock positions.
7. Review the dashboard on the same page.

## Supported Inputs

- `image/*` screenshots for OCR
- WeChat statement exports in `.xlsx`
- Alipay statement exports in `.csv`

Statement imports are normalized into signed ledger entries:

- expense values are stored as negative numbers
- income values are stored as positive numbers
- statement rows with absolute amount less than `1` are dropped
- WeChat refund rows are filtered out during import

## Current UI Sections

- screenshot OCR import
- statement file import
- review-and-save table
- manual entry form
- category and member setup
- asset snapshot form
- stock record form
- dashboard summary cards
- saved records table

## Tests

Run the full suite:

```bash
.venv/bin/pytest -q
```

Run the API/browser-focused suite:

```bash
.venv/bin/pytest tests/test_api.py -q
```
