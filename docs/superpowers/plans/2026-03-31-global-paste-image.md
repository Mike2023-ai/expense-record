# Global Paste Image Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Ctrl+V` image paste work anywhere on the page while preserving normal text paste inside the editable review inputs.

**Architecture:** Move image-paste handling from the focused paste zone to a single document-level handler in the existing frontend script. Keep the current file-selection flow intact by routing pasted images through the existing `handleFileSelection()` path, and update the page copy to match the broader paste behavior.

**Tech Stack:** Flask template, vanilla JavaScript, pytest, Node-based frontend regression script

---

## File Structure

- `src/expense_record/templates/index.html`
  Update the upload instructions and paste-zone helper copy so they no longer imply the box must have focus for paste to work.
- `src/expense_record/static/app.js`
  Replace the element-scoped paste listener with a document-level listener that accepts image clipboard items and ignores paste events targeting the review text inputs.
- `tests/test_api.py`
  Extend the frontend regression harness so it can exercise document-level paste handling and verify text-input paste is left alone.

### Task 1: Move Image Paste Handling To The Whole Page

**Files:**
- Modify: `src/expense_record/templates/index.html`
- Modify: `src/expense_record/static/app.js`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing tests**

Add one HTML assertion for the updated helper copy:

```python
def test_index_page_mentions_paste_anywhere():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Paste a screenshot anywhere on the page" in response.data
```

Extend the existing Node-based frontend regression with a document-level paste dispatcher and assertions that:

```python
documentListeners.paste({
  clipboardData: {
    items: [
      {
        type: "image/png",
        getAsFile() {
          return { name: "clip.png", type: "image/png" };
        },
      },
    ],
  },
  target: { tagName: "DIV" },
  preventDefault() {
    pastePrevented = true;
  },
});

assert.strictEqual(pastePrevented, true);
assert.strictEqual(elements["preview-caption"].textContent, "clip.png");
assert.strictEqual(elements["extract-button"].disabled, false);
```

Also assert that text-input paste is ignored:

```python
pastePrevented = false;
documentListeners.paste({
  clipboardData: {
    items: [
      {
        type: "image/png",
        getAsFile() {
          return { name: "ignored.png", type: "image/png" };
        },
      },
    ],
  },
  target: elements["merchant-input"],
  preventDefault() {
    pastePrevented = true;
  },
});

assert.strictEqual(pastePrevented, false);
assert.strictEqual(elements["preview-caption"].textContent, "clip.png");
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_api.py::test_index_page_mentions_paste_anywhere -q
pytest tests/test_api.py::test_frontend_ignores_stale_selection_work_and_resets_save_state -q
```

Expected:
- The template test fails because the current upload copy still tells the user to focus the paste box.
- The frontend test fails because the current code only registers `paste` on `paste-zone`, not on `document`.

- [ ] **Step 3: Write the minimal implementation**

Update the upload instructions in `src/expense_record/templates/index.html`:

```html
          <p>Use the file picker or paste an image anywhere on the page.</p>
```

and update the paste-zone helper text:

```html
          <span>Paste a screenshot anywhere on the page with Ctrl+V</span>
```

In `src/expense_record/static/app.js`, add a small helper for editable-text targets:

```javascript
function isEditableTextTarget(target) {
  if (!target || typeof target.tagName !== "string") {
    return false;
  }

  const tagName = target.tagName.toUpperCase();
  return tagName === "INPUT" || tagName === "TEXTAREA";
}
```

Replace the `elements.pasteZone.addEventListener("paste", ...)` block with a document-level listener:

```javascript
document.addEventListener("paste", (event) => {
  const items = Array.from(event.clipboardData?.items ?? []);
  const imageItem = items.find((entry) => entry.type.startsWith("image/"));

  if (!imageItem || isEditableTextTarget(event.target)) {
    return;
  }

  const file = imageItem.getAsFile();
  if (!file) {
    setStatus("Clipboard image could not be read.", true);
    return;
  }

  event.preventDefault();
  handleFileSelection(new File([file], file.name || "clipboard-snip.png", { type: file.type }));
});
```

Extend the Node sandbox in `tests/test_api.py` so it can capture document listeners:

```javascript
        const documentListeners = {};
```

```javascript
          document: {
            getElementById(id) {
              return elements[id];
            },
            createElement(tag) {
              return {
                tagName: String(tag).toUpperCase(),
                textContent: "",
                colSpan: 0,
                children: [],
                appendChild(child) {
                  this.children.push(child);
                },
              };
            },
            addEventListener(type, handler) {
              documentListeners[type] = handler;
            },
          },
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_api.py::test_index_page_mentions_paste_anywhere -q
pytest tests/test_api.py::test_frontend_ignores_stale_selection_work_and_resets_save_state -q
pytest tests/test_api.py -q
```

Expected:
- All three commands pass.
- The document-level paste regression proves image paste works without focusing the paste zone.
- The text-input assertion proves review-form paste is still left alone.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/expense_record/templates/index.html src/expense_record/static/app.js tests/test_api.py
git commit -m "feat: accept pasted screenshots anywhere"
```

