# Month-Day Date Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the parser so cropped transaction screenshots with dates like `3月29日 08:42` or `3月29日` can extract a normalized current-year `date`.

**Architecture:** Keep the fix inside the existing parser. Add month-day date patterns alongside the existing full-year patterns, normalize them to `YYYY-MM-DD` using the current year, and cover the new behavior with focused parser regression tests.

**Tech Stack:** Python 3.12, pytest

---

## File Structure

- Modify: `src/expense_record/parser.py`
- Modify: `tests/test_parser.py`

## Task 1: Add current-year month-day parsing

**Files:**
- Modify: `src/expense_record/parser.py`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Write failing parser tests for month-day dates**

```python
from datetime import date

from expense_record.models import ExpenseRow
from expense_record.parser import parse_expense_row


def test_parse_expense_row_supports_month_day_with_time_without_year():
    current_year = date.today().year

    row = parse_expense_row(
        [
            "扫二维码付款-给早餐",
            "3月29日 08:42",
            "-5.00",
        ]
    )

    assert row == ExpenseRow(
        date=f"{current_year}-03-29",
        merchant_item="扫二维码付款-给早餐",
        amount="5.00",
    )


def test_parse_expense_row_supports_month_day_without_year():
    current_year = date.today().year

    row = parse_expense_row(
        [
            "瑞幸咖啡",
            "3月29日",
            "￥23.50",
        ]
    )

    assert row.date == f"{current_year}-03-29"


def test_parse_expense_row_supports_slash_month_day_without_year():
    current_year = date.today().year

    row = parse_expense_row(
        [
            "早餐",
            "3/29 08:42",
            "5.00",
        ]
    )

    assert row.date == f"{current_year}-03-29"
```

- [ ] **Step 2: Run the targeted parser tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_parser.py -v
```

Expected: FAIL because month-day dates without a year are not parsed yet

- [ ] **Step 3: Implement month-day parsing in the parser**

```python
# src/expense_record/parser.py
from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date

from expense_record.models import ExpenseRow


DATE_PATTERNS = (
    re.compile(r"(?P<date>\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"),
    re.compile(r"(?P<date>\d{4}年\d{1,2}月\d{1,2}日)"),
)
MONTH_DAY_PATTERNS = (
    re.compile(r"(?P<month>\d{1,2})月(?P<day>\d{1,2})日(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"),
    re.compile(r"(?P<month>\d{1,2})/(?P<day>\d{1,2})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"),
    re.compile(r"(?P<month>\d{1,2})\.(?P<day>\d{1,2})"),
)


def _extract_date(lines: list[str]) -> str:
    for line in lines:
        for pattern in DATE_PATTERNS:
            match = pattern.search(line)
            if match:
                return _canonicalize_date(match.group("date"))

        for pattern in MONTH_DAY_PATTERNS:
            match = pattern.search(line)
            if match:
                return _canonicalize_month_day(match.group("month"), match.group("day"))
    return ""


def _canonicalize_month_day(month: str, day: str) -> str:
    current_year = date.today().year
    return f"{current_year:04d}-{int(month):02d}-{int(day):02d}"
```

- [ ] **Step 4: Run the parser tests to verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_parser.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/expense_record/parser.py tests/test_parser.py
git commit -m "fix: support month-day dates without year"
```

## Self-Review

### Spec coverage

- Support `3月29日 08:42`: covered by Task 1 Step 1 and Step 3
- Support `3月29日`: covered by Task 1 Step 1 and Step 3
- Support common OCR-like variants such as `3/29 08:42`: covered by Task 1 Step 1 and Step 3
- Use current year: covered by `_canonicalize_month_day()`
- Preserve existing full-year parsing: covered by keeping `DATE_PATTERNS` and its extraction path first

### Placeholder scan

No placeholders remain.

### Type consistency

- Parser continues returning `ExpenseRow`
- Date normalization remains `YYYY-MM-DD`
