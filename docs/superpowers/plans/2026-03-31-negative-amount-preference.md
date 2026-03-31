# Negative Amount Preference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prefer the actual charged negative amount when OCR returns both a real expense amount and an old crossed-out positive amount.

**Architecture:** Keep the change local to amount extraction in the parser. Gather all amount-like OCR lines first, choose the first negative amount if one exists, and otherwise fall back to the current reverse-scan behavior so existing single-amount cases remain stable.

**Tech Stack:** Python parser helpers, pytest

---

## File Structure

- `src/expense_record/parser.py`
  Update amount extraction to rank negative amounts ahead of positive amounts when multiple candidates exist.
- `tests/test_parser.py`
  Add a regression for the crossed-out old-price OCR case and keep existing single-amount coverage intact.

### Task 1: Prefer Negative Amounts When OCR Returns Multiple Values

**Files:**
- Modify: `src/expense_record/parser.py`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Write the failing test**

Add a parser regression for the crossed-out old-price screenshot pattern:

```python
def test_parse_expense_row_prefers_negative_amount_over_old_positive_amount():
    row = parse_expense_row(
        [
            "滴滴出行",
            "-28.00",
            "3月28日11:44",
            "31.00",
        ]
    )

    assert row == ExpenseRow(
        date="03-28",
        merchant_item="滴滴出行",
        amount="28.00",
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_parser.py::test_parse_expense_row_prefers_negative_amount_over_old_positive_amount -q
```

Expected:
- FAIL because `_extract_amount()` currently scans from the end and returns `31.00`.

- [ ] **Step 3: Write the minimal implementation**

In `src/expense_record/parser.py`, keep `_match_amount()` unchanged and update `_extract_amount()` so it collects all candidate amount lines first:

```python
def _extract_amount(lines: list[str]) -> str:
    candidates: list[tuple[str, bool]] = []

    for line in lines:
        if _looks_like_date_or_time(line):
            continue

        amount = _match_amount(line)
        if amount:
            candidates.append((amount, line.strip().startswith("-")))

    for amount, is_negative in candidates:
        if is_negative:
            return amount

    for amount, _is_negative in reversed(candidates):
        return amount

    return ""
```

This preserves current fallback behavior when no negative amounts exist, but prefers the first negative OCR amount when one is present.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_parser.py::test_parse_expense_row_prefers_negative_amount_over_old_positive_amount -q
pytest tests/test_parser.py -q
```

Expected:
- The new regression passes with amount `28.00`.
- The full parser suite still passes, showing existing single-amount cases remain stable.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/expense_record/parser.py tests/test_parser.py
git commit -m "feat: prefer negative OCR amounts"
```

