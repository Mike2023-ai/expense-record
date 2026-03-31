# Webpage Version Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the current app version under the main title on the webpage.

**Architecture:** Keep the version in one source of truth from project metadata/config, expose it through Flask config, pass it into the index template, and render a small secondary line below the page heading. Limit the change to the existing Flask config/template flow without adding new endpoints.

**Tech Stack:** Python 3.12, Flask, Jinja2, pytest, HTML/CSS

---

## File Structure

- Modify: `src/expense_record/config.py`
- Modify: `src/expense_record/app.py`
- Modify: `src/expense_record/templates/index.html`
- Modify: `src/expense_record/static/app.css`
- Modify: `tests/test_api.py`

## Task 1: Render the app version in the page header

**Files:**
- Modify: `src/expense_record/config.py`
- Modify: `src/expense_record/app.py`
- Modify: `src/expense_record/templates/index.html`
- Modify: `src/expense_record/static/app.css`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write the failing page assertion**

```python
# tests/test_api.py
from expense_record.app import create_app


def test_index_page_shows_app_version():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert b"Version 0.1.0" in response.data
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_api.py::test_index_page_shows_app_version -v
```

Expected: FAIL because the template does not render the version yet

- [ ] **Step 3: Expose the version through config and render it**

```python
# src/expense_record/config.py
from importlib import metadata


def resolve_app_version() -> str:
    try:
        return metadata.version("expense-screenshot-tool")
    except metadata.PackageNotFoundError:
        return "0.1.0"


class Config:
    APP_VERSION = resolve_app_version()
```

```python
# src/expense_record/app.py
@app.get("/")
def index() -> str:
    return render_template("index.html", app_version=app.config["APP_VERSION"])
```

```html
<!-- src/expense_record/templates/index.html -->
<header class="hero">
  <p class="eyebrow">Local OCR to Excel</p>
  <h1>Expense Screenshot Tool</h1>
  <p class="app-version">Version {{ app_version }}</p>
  <p class="hero-copy">
    Paste or upload a phone screenshot, review the extracted row, then save it into Excel.
  </p>
</header>
```

```css
/* src/expense_record/static/app.css */
.app-version {
  margin: 4px 0 0;
  font-size: 14px;
  color: rgba(53, 36, 23, 0.68);
}
```

- [ ] **Step 4: Run the targeted test to verify it passes**

Run:

```bash
.venv/bin/python -m pytest tests/test_api.py::test_index_page_shows_app_version -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/expense_record/config.py src/expense_record/app.py src/expense_record/templates/index.html src/expense_record/static/app.css tests/test_api.py
git commit -m "feat: show app version in page header"
```

## Self-Review

### Spec coverage

- Expose version from Flask configuration: covered by Task 1 Step 3
- Pass version into index template: covered by Task 1 Step 3
- Render small version line under title: covered by Task 1 Step 3
- Style as metadata: covered by Task 1 Step 3

### Placeholder scan

No placeholders remain.

### Type consistency

- The config key is consistently `APP_VERSION`
- The template variable is consistently `app_version`
