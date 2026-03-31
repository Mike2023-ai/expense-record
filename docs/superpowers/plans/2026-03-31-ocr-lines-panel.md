# OCR Lines Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the raw OCR lines returned by `/api/extract` on the webpage so extraction failures can be diagnosed from the UI.

**Architecture:** Reuse the existing `lines` payload from the extract API and render it in a small read-only panel inside the upload section. Keep the backend unchanged; the work is limited to the template, client-side rendering/reset behavior, a small CSS treatment, and a focused frontend regression test.

**Tech Stack:** Flask templates, vanilla JavaScript, CSS, pytest, Node-based frontend regression script

---

## File Structure

- `src/expense_record/templates/index.html`
  Add a hidden OCR lines block under the screenshot preview with a heading and container the client can fill.
- `src/expense_record/static/app.js`
  Add DOM references plus helper functions to render and clear OCR lines; call them on extract success, extract failure, and screenshot reselection.
- `src/expense_record/static/app.css`
  Style the OCR lines block as support/debug text that is visually secondary to the main workflow.
- `tests/test_api.py`
  Extend the existing Node-based frontend regression to assert OCR lines render in order and clear when a new screenshot is selected.

### Task 1: Render And Reset OCR Lines In The Upload Panel

**Files:**
- Modify: `src/expense_record/templates/index.html`
- Modify: `src/expense_record/static/app.js`
- Modify: `src/expense_record/static/app.css`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing tests**

Add a new index-page assertion so the HTML exposes a dedicated OCR panel:

```python
def test_index_page_contains_ocr_lines_panel():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'id="ocr-lines-panel"' in response.data
    assert b'id="ocr-lines-list"' in response.data
```

Extend `test_frontend_ignores_stale_selection_work_and_resets_save_state` so it asserts three behaviors:

```python
assert.strictEqual(elements["ocr-lines-panel"].hidden, true);
assert.deepStrictEqual(
  elements["ocr-lines-list"].children.map((child) => child.textContent),
  ["扫二维码付款-给早餐", "3月29日 08:42", "-5.00"],
);
assert.strictEqual(elements["ocr-lines-panel"].hidden, false);
```

Then, after selecting a new screenshot, assert the panel clears immediately:

```python
assert.strictEqual(elements["ocr-lines-panel"].hidden, true);
assert.strictEqual(elements["ocr-lines-list"].children.length, 0);
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_api.py::test_index_page_contains_ocr_lines_panel -q
pytest tests/test_api.py::test_frontend_ignores_stale_selection_work_and_resets_save_state -q
```

Expected:
- The template test fails because the OCR panel markup does not exist yet.
- The frontend test fails because `ocr-lines-panel` / `ocr-lines-list` are missing from the mocked DOM or because no lines are rendered.

- [ ] **Step 3: Write the minimal implementation**

Add the OCR panel markup directly after the preview card in `src/expense_record/templates/index.html`:

```html
        <div id="ocr-lines-panel" class="ocr-lines" hidden>
          <p class="ocr-lines-title">OCR lines</p>
          <div id="ocr-lines-list" class="ocr-lines-list"></div>
        </div>

        <p id="status-message" class="status-message" aria-live="polite"></p>
```

In `src/expense_record/static/app.js`, register the new elements and add explicit render/clear helpers:

```javascript
  ocrLinesPanel: document.getElementById("ocr-lines-panel"),
  ocrLinesList: document.getElementById("ocr-lines-list"),
```

```javascript
function clearOcrLines() {
  elements.ocrLinesList.innerHTML = "";
  elements.ocrLinesPanel.hidden = true;
}

function renderOcrLines(lines) {
  clearOcrLines();

  if (!Array.isArray(lines) || !lines.length) {
    return;
  }

  for (const line of lines) {
    const item = document.createElement("div");
    item.className = "ocr-line";
    item.textContent = String(line ?? "");
    elements.ocrLinesList.appendChild(item);
  }

  elements.ocrLinesPanel.hidden = false;
}
```

Call `clearOcrLines()` from `resetSelectionState()`. In `extractRow()`, render lines from the API response before setting status:

```javascript
    renderOcrLines(data.lines);
```

On non-OK extract responses and caught network failures, clear the panel:

```javascript
      clearOcrLines();
```

Style the panel in `src/expense_record/static/app.css`:

```css
.ocr-lines {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px dashed rgba(160, 79, 23, 0.28);
  background: rgba(255, 248, 240, 0.72);
}

.ocr-lines-title {
  margin: 0 0 8px;
  color: var(--accent-strong);
  font-size: 0.9rem;
  font-weight: 700;
}

.ocr-lines-list {
  display: grid;
  gap: 6px;
}

.ocr-line {
  font-family: "Courier New", Courier, monospace;
  font-size: 0.92rem;
  color: var(--muted);
  white-space: pre-wrap;
  word-break: break-word;
}
```

Update the Node test fixture in `tests/test_api.py` so the mocked DOM includes:

```javascript
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
```

and so the mocked extract success response supplies `lines`:

```javascript
          firstPendingExtract(makeResponse({
            date: "2026-03-30",
            merchant_item: "old",
            amount: "1.00",
          }, ["旧商户", "3月30日 09:15", "-1.00"]));
```

with `makeResponse` updated to:

```javascript
        function makeResponse(row, lines = []) {
          return {
            ok: true,
            json: async () => ({ row, lines }),
          };
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_api.py::test_index_page_contains_ocr_lines_panel -q
pytest tests/test_api.py::test_frontend_ignores_stale_selection_work_and_resets_save_state -q
pytest tests/test_api.py -q
```

Expected:
- All three commands pass.
- The frontend regression confirms OCR lines appear after extract and disappear when a new screenshot is chosen.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/expense_record/templates/index.html src/expense_record/static/app.js src/expense_record/static/app.css tests/test_api.py
git commit -m "feat: show OCR lines in upload panel"
```

