# Multi-Transaction Screenshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let one screenshot produce multiple editable expense rows in a checkbox-based review table, then save only the selected rows to Excel.

**Architecture:** Extend the backend from single-row parsing to a list-of-rows extraction flow while keeping OCR unchanged. Replace the single-row review form with one editable review table in the frontend, and update the save API/storage path to accept multiple rows in one request.

**Tech Stack:** Flask, vanilla JavaScript, HTML/CSS, pytest, Node-based frontend regression tests, openpyxl-backed storage

---

## File Structure

- `src/expense_record/parser.py`
  Add a new multi-row extraction entrypoint that groups OCR lines into transaction-like row candidates and parses each candidate with the existing single-row parser logic.
- `src/expense_record/api.py`
  Change `/api/extract` to return `rows` instead of a single `row`, and update `/api/save` to accept a list of checked rows.
- `src/expense_record/storage.py`
  Add a bulk-append helper so checked rows can be written in one save action.
- `src/expense_record/templates/index.html`
  Replace the current single-row form with an always-visible editable review table containing `use`, `date`, `merchant/item`, and `amount`.
- `src/expense_record/static/app.js`
  Replace single-row state with extracted-row table state, render editable rows with checkboxes, and submit only checked rows.
- `src/expense_record/static/app.css`
  Style the review table so checkbox, inputs, and empty-state messaging fit the existing page.
- `tests/test_parser.py`
  Add multi-row extraction tests and keep existing single-row parser coverage intact.
- `tests/test_api.py`
  Update API expectations for `rows`, add bulk-save validation coverage, and extend the frontend regression to exercise the table UI.
- `tests/test_storage.py`
  Add storage coverage for bulk append behavior.

### Task 1: Add Multi-Row Parser Extraction

**Files:**
- Modify: `src/expense_record/parser.py`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Write the failing parser tests**

Add one focused multi-row extraction test:

```python
def test_extract_expense_rows_from_transaction_list_lines():
    rows = parser_module.extract_expense_rows(
        [
            "滴滴出行",
            "3月28日11:44",
            "-28.00",
            "扫二维码付款-给早餐",
            "3月29日08:42",
            "-5.00",
        ]
    )

    assert rows == [
        ExpenseRow(date="03-28", merchant_item="滴滴出行", amount="28.00"),
        ExpenseRow(date="03-29", merchant_item="扫二维码付款-给早餐", amount="5.00"),
    ]
```

Add one guard that a single-row screenshot still produces one row:

```python
def test_extract_expense_rows_returns_single_row_for_single_transaction():
    rows = parser_module.extract_expense_rows(
        [
            "滴滴出行",
            "3月28日11:44",
            "-28.00",
        ]
    )

    assert rows == [ExpenseRow(date="03-28", merchant_item="滴滴出行", amount="28.00")]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_parser.py::test_extract_expense_rows_from_transaction_list_lines -q
pytest tests/test_parser.py::test_extract_expense_rows_returns_single_row_for_single_transaction -q
```

Expected:
- FAIL because `extract_expense_rows()` does not exist yet.

- [ ] **Step 3: Write the minimal parser implementation**

In `src/expense_record/parser.py`, add a multi-row entrypoint that groups lines by amount boundaries:

```python
def extract_expense_rows(text_lines: str | Iterable[str]) -> list[ExpenseRow]:
    lines = _normalize_lines(text_lines)
    groups = _group_transaction_lines(lines)
    rows = [parse_expense_row(group) for group in groups]
    return [row for row in rows if any((row.date, row.merchant_item, row.amount))]
```

Add a simple grouping helper that starts a new group after each amount-like line:

```python
def _group_transaction_lines(lines: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        current.append(line)
        if _looks_like_amount_line(line):
            groups.append(current)
            current = []

    if current:
        groups.append(current)

    return [group for group in groups if any(group)]
```

Do not remove or rename `parse_expense_row()`; the multi-row entrypoint should reuse it.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_parser.py::test_extract_expense_rows_from_transaction_list_lines -q
pytest tests/test_parser.py::test_extract_expense_rows_returns_single_row_for_single_transaction -q
pytest tests/test_parser.py -q
```

Expected:
- New multi-row tests pass.
- Existing parser tests still pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/expense_record/parser.py tests/test_parser.py
git commit -m "feat: extract multiple rows from OCR lines"
```

### Task 2: Return Extracted Rows And Support Bulk Save

**Files:**
- Modify: `src/expense_record/api.py`
- Modify: `src/expense_record/storage.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write the failing backend tests**

Add an extract-endpoint test expecting `rows`:

```python
def test_extract_endpoint_returns_multiple_rows(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "EXCEL_PATH": str(tmp_path / "expenses.xlsx")})
    client = app.test_client()

    monkeypatch.setattr("expense_record.api.run_ocr_lines", lambda _bytes: ["滴滴出行", "3月28日11:44", "-28.00", "扫二维码付款-给早餐", "3月29日08:42", "-5.00"])
    monkeypatch.setattr(
        "expense_record.api.extract_expense_rows",
        lambda lines: [
            ExpenseRow(date="03-28", merchant_item="滴滴出行", amount="28.00"),
            ExpenseRow(date="03-29", merchant_item="扫二维码付款-给早餐", amount="5.00"),
        ],
    )

    response = client.post(
        "/api/extract",
        data={"image": (io.BytesIO(b"fake-image"), "screen.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {"date": "03-28", "merchant_item": "滴滴出行", "amount": "28.00"},
        {"date": "03-29", "merchant_item": "扫二维码付款-给早餐", "amount": "5.00"},
    ]
```

Add a bulk-save API test:

```python
def test_save_endpoint_appends_only_checked_rows(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": str(tmp_path / "expenses.xlsx")})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={
            "rows": [
                {"date": "03-28", "merchant_item": "滴滴出行", "amount": "28.00", "selected": True},
                {"date": "03-29", "merchant_item": "早餐", "amount": "5.00", "selected": False},
            ]
        },
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {"date": "03-28", "merchant_item": "滴滴出行", "amount": "28.00"}
    ]
```

Add one storage test:

```python
def test_storage_append_rows_appends_multiple_rows(tmp_path):
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")
    storage.append_rows(
        [
            ExpenseRow(date="03-28", merchant_item="滴滴出行", amount="28.00"),
            ExpenseRow(date="03-29", merchant_item="早餐", amount="5.00"),
        ]
    )

    assert storage.list_rows() == [
        ExpenseRow(date="03-28", merchant_item="滴滴出行", amount="28.00"),
        ExpenseRow(date="03-29", merchant_item="早餐", amount="5.00"),
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_api.py::test_extract_endpoint_returns_multiple_rows -q
pytest tests/test_api.py::test_save_endpoint_appends_only_checked_rows -q
pytest tests/test_storage.py::test_storage_append_rows_appends_multiple_rows -q
```

Expected:
- FAIL because `/api/extract` still returns `row`, `/api/save` only accepts one row, and storage has no bulk append helper.

- [ ] **Step 3: Write the minimal backend implementation**

In `src/expense_record/storage.py`, add:

```python
    def append_rows(self, rows: list[ExpenseRow]) -> None:
        if not rows:
            return
        workbook = self._load_or_create_workbook()
        worksheet = self._get_expenses_sheet(workbook)
        for row in rows:
            worksheet.append([row.date, row.merchant_item, row.amount])
        workbook.save(self.workbook_path)
```

In `src/expense_record/api.py`, import `extract_expense_rows` and update `/api/extract`:

```python
from expense_record.parser import extract_expense_rows
```

```python
        rows = extract_expense_rows(lines)
```

```python
    row_dicts = [row.to_dict() for row in rows]
    payload = {"rows": row_dicts, "lines": lines}
    if not row_dicts:
        payload["warning"] = "OCR returned no usable rows."
    elif any(not all(row.values()) for row in row_dicts):
        payload["warning"] = "OCR returned incomplete rows."
```

Update save payload parsing to accept `payload["rows"]`, filter `selected`, validate each row with `_coerce_save_field()`, and bulk append:

```python
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        return jsonify({"error": "Invalid save payload."}), 400

    selected_rows: list[ExpenseRow] = []
    for item in payload["rows"]:
        if not isinstance(item, dict) or not item.get("selected", False):
            continue
        date = _coerce_save_field(item, "date")
        merchant_item = _coerce_save_field(item, "merchant_item")
        amount = _coerce_save_field(item, "amount")
        if date is None or merchant_item is None or amount is None:
            return jsonify({"error": "Invalid save payload."}), 400
        if not any((date, merchant_item, amount)):
            continue
        selected_rows.append(ExpenseRow(date=date, merchant_item=merchant_item, amount=amount))

    if not selected_rows:
        return jsonify({"error": "At least one checked row is required."}), 400

    storage = _storage()
    storage.append_rows(selected_rows)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_storage.py::test_storage_append_rows_appends_multiple_rows -q
pytest tests/test_api.py::test_extract_endpoint_returns_multiple_rows -q
pytest tests/test_api.py::test_save_endpoint_appends_only_checked_rows -q
pytest tests/test_storage.py -q
pytest tests/test_api.py -q
```

Expected:
- New storage and API tests pass.
- Existing storage/API coverage remains green after the contract change.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/expense_record/api.py src/expense_record/storage.py tests/test_api.py tests/test_storage.py
git commit -m "feat: add multi-row extract and bulk save APIs"
```

### Task 3: Replace The Single-Row Form With An Editable Review Table

**Files:**
- Modify: `src/expense_record/templates/index.html`
- Modify: `src/expense_record/static/app.js`
- Modify: `src/expense_record/static/app.css`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write the failing frontend tests**

Add an index-page structure assertion:

```python
def test_index_page_contains_review_table():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'id="review-table"' in response.data
    assert b'id="review-body"' in response.data
```

Extend the Node-based frontend regression to model extract responses shaped like:

```python
{
  "rows": [
    {"date": "03-28", "merchant_item": "滴滴出行", "amount": "28.00"},
    {"date": "03-29", "merchant_item": "早餐", "amount": "5.00"},
  ],
  "lines": ["..."],
}
```

and assert:

```python
assert.strictEqual(elements["review-body"].children.length, 2);
assert.strictEqual(elements["save-button"].disabled, false);
assert.strictEqual(elements["review-body"].children[0].children[1].children[0].value, "03-28");
```

Add a save-payload assertion that only checked rows are submitted:

```python
assert.deepStrictEqual(JSON.parse(fetchCalls.at(-1).options.body), {
  rows: [
    { selected: true, date: "03-28", merchant_item: "滴滴出行", amount: "28.00" },
    { selected: false, date: "03-29", merchant_item: "早餐", amount: "5.00" },
  ],
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_api.py::test_index_page_contains_review_table -q
pytest tests/test_api.py::test_frontend_ignores_stale_selection_work_and_resets_save_state -q
```

Expected:
- FAIL because the template still exposes the single-row form.
- FAIL because the frontend still expects `data.row` and serializes one row on save.

- [ ] **Step 3: Write the minimal frontend implementation**

In `src/expense_record/templates/index.html`, replace the form block with a table shell:

```html
      <section class="panel">
        <div class="panel-header">
          <h2>2. Review rows</h2>
          <p>Adjust extracted rows before saving.</p>
        </div>

        <div class="table-wrap">
          <table id="review-table">
            <thead>
              <tr>
                <th>Use</th>
                <th>Date</th>
                <th>Merchant / Item</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody id="review-body"></tbody>
          </table>
        </div>
        <div class="form-actions">
          <button id="save-button" type="button" disabled>Save Checked Rows</button>
        </div>
      </section>
```

In `src/expense_record/static/app.js`, replace single-row DOM references with review-table state:

```javascript
  reviewBody: document.getElementById("review-body"),
```

Add helpers:

```javascript
function clearReviewRows() {
  elements.reviewBody.innerHTML = "";
}

function renderReviewRows(rows) {
  clearReviewRows();
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" data-role="selected" checked></td>
      <td><input type="text" data-role="date" value="${row.date ?? ""}"></td>
      <td><input type="text" data-role="merchant_item" value="${row.merchant_item ?? ""}"></td>
      <td><input type="text" data-role="amount" value="${row.amount ?? ""}"></td>
    `;
    elements.reviewBody.appendChild(tr);
  }
}
```

Update extract handling:

```javascript
    renderReviewRows(Array.isArray(data.rows) ? data.rows : []);
    extractedSelectionToken = selectionToken;
    elements.saveButton.disabled = elements.reviewBody.children.length === 0;
```

Update save handling to gather rows from the review table:

```javascript
  const rows = Array.from(elements.reviewBody.children).map((tr) => ({
    selected: tr.querySelector('[data-role="selected"]').checked,
    date: tr.querySelector('[data-role="date"]').value.trim(),
    merchant_item: tr.querySelector('[data-role="merchant_item"]').value.trim(),
    amount: tr.querySelector('[data-role="amount"]').value.trim(),
  }));
```

and submit:

```javascript
  const payload = { rows };
```

Update CSS in `src/expense_record/static/app.css` so `#review-table input[type="text"]` fills cells cleanly and checkbox cells stay compact.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_api.py::test_index_page_contains_review_table -q
pytest tests/test_api.py::test_frontend_ignores_stale_selection_work_and_resets_save_state -q
pytest tests/test_api.py -q
```

Expected:
- Review table structure test passes.
- Frontend regression passes with `rows` extraction and checkbox-based save payload.
- Full API/frontend test file remains green.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/expense_record/templates/index.html src/expense_record/static/app.js src/expense_record/static/app.css tests/test_api.py
git commit -m "feat: review and save multiple extracted rows"
```

