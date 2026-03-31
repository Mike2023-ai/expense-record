# Short Date Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize extracted screenshot dates to `MM-DD` only, ignoring any OCR time suffix, and reflect that format in the review form.

**Architecture:** Keep the change local to the parser and the existing HTML form. Update the month-day parser so it recognizes Chinese month-day strings with or without an attached time suffix and canonicalizes them to zero-padded `MM-DD`, while leaving amount and merchant extraction untouched.

**Tech Stack:** Python parser helpers, Flask template, pytest

---

## File Structure

- `src/expense_record/parser.py`
  Update month-day matching and canonicalization so Chinese month-day dates normalize to `MM-DD` and ignore trailing time.
- `src/expense_record/templates/index.html`
  Change the date input placeholder from `YYYY-MM-DD` to `MM-DD`.
- `tests/test_parser.py`
  Update existing month-day expectations and add a regression for the no-space OCR form `3月29日08:42`.
- `tests/test_api.py`
  Add a small index-page assertion for the updated `MM-DD` placeholder.

### Task 1: Normalize OCR Dates To MM-DD

**Files:**
- Modify: `src/expense_record/parser.py`
- Modify: `src/expense_record/templates/index.html`
- Modify: `tests/test_parser.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write the failing tests**

Add a parser regression for the OCR variant without a space before time:

```python
def test_parse_expense_row_supports_month_day_date_with_attached_time():
    row = parse_expense_row(
        [
            "3月29日08:42",
            "扫二维码付款-给早餐",
            "-5.00",
        ]
    )

    assert row == ExpenseRow(
        date="03-29",
        merchant_item="扫二维码付款-给早餐",
        amount="5.00",
    )
```

Update existing month-day parser assertions so they expect `MM-DD` instead of a synthesized year:

```python
assert row.date == "03-29"
```

for:
- `test_parse_expense_row_supports_month_day_date_with_time`
- `test_parse_expense_row_supports_month_day_date_without_time`
- `test_parse_expense_row_supports_realistic_month_day_row`

Add an index-page placeholder assertion:

```python
def test_index_page_uses_short_date_placeholder():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'placeholder="MM-DD"' in response.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_parser.py::test_parse_expense_row_supports_month_day_date_with_attached_time -q
pytest tests/test_parser.py::test_parse_expense_row_supports_realistic_month_day_row -q
pytest tests/test_api.py::test_index_page_uses_short_date_placeholder -q
```

Expected:
- The attached-time parser test fails because `3月29日08:42` is not matched yet.
- The realistic month-day row test fails because the parser still emits a year-based date.
- The placeholder test fails because the form still shows `YYYY-MM-DD`.

- [ ] **Step 3: Write the minimal implementation**

In `src/expense_record/parser.py`, widen the Chinese month-day regex so it accepts an optional trailing time without requiring a separating space:

```python
MONTH_DAY_WITH_CHINESE_RE = re.compile(
    r"(?:^|[\s(（\[\{【<,，:：;；])"
    r"(?P<date>(?:0?[1-9]|1[0-2])月(?:0?[1-9]|[12]\d|3[01])日)"
    r"(?:\s*(?P<time>\d{1,2}:\d{2}(?::\d{2})?))?"
    r"(?=$|[\s)）\]\}】>,，。.!！？?])"
)
```

Keep `_match_date_text()` returning only the captured `date` group for Chinese month-day matches:

```python
    match = MONTH_DAY_WITH_CHINESE_RE.search(line)
    if match:
        return match.group("date")
```

Change `_canonicalize_month_day()` so it returns `MM-DD` while still validating calendar correctness against the current year:

```python
def _canonicalize_month_day(month: int, day: int) -> str:
    year = date.today().year
    try:
        date(year, month, day)
    except ValueError:
        return ""
    return f"{month:02d}-{day:02d}"
```

In `src/expense_record/templates/index.html`, update the date input placeholder:

```html
            <input id="date-input" name="date" type="text" placeholder="MM-DD" autocomplete="off">
```

Update `tests/test_parser.py` so month-day expectations use `MM-DD`, including leap-day validation:

```python
    assert row.date == "02-29"
```

for `test_parse_expense_row_allows_leap_day_month_day_date`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_parser.py -q
pytest tests/test_api.py::test_index_page_uses_short_date_placeholder -q
pytest tests/test_api.py -q
```

Expected:
- Parser tests pass with `MM-DD` output for month-day OCR inputs, including `3月29日08:42`.
- The index-page placeholder test passes with `MM-DD`.
- The full API test file still passes.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/expense_record/parser.py src/expense_record/templates/index.html tests/test_parser.py tests/test_api.py
git commit -m "feat: store OCR dates as month-day"
```

