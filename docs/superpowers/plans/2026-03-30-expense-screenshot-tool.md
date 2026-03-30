# Expense Screenshot Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web app that accepts one pasted or uploaded phone screenshot, extracts `date`, `merchant/item`, and `amount`, lets the user edit the result, and saves approved rows into a local Excel file.

**Architecture:** Use a small Flask backend to serve a single static web page, expose JSON APIs for extract/save/list actions, run OCR locally through a dedicated OCR service, parse OCR text with a heuristic field parser, and persist rows through an Excel storage service. Keep the frontend as plain HTML/CSS/JavaScript to reduce setup cost while still supporting clipboard paste, file upload, preview, editable fields, and a saved-records table.

**Tech Stack:** Python 3.11+, Flask, rapidocr-onnxruntime, openpyxl, pytest, vanilla HTML/CSS/JavaScript

---

## File Structure

### Application files

- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.gitignore`
- Create: `src/expense_record/__init__.py`
- Create: `src/expense_record/app.py`
- Create: `src/expense_record/api.py`
- Create: `src/expense_record/models.py`
- Create: `src/expense_record/ocr.py`
- Create: `src/expense_record/parser.py`
- Create: `src/expense_record/storage.py`
- Create: `src/expense_record/config.py`
- Create: `src/expense_record/templates/index.html`
- Create: `src/expense_record/static/app.css`
- Create: `src/expense_record/static/app.js`

### Test files

- Create: `tests/test_parser.py`
- Create: `tests/test_storage.py`
- Create: `tests/test_api.py`

### Runtime data

- Create on first run: `data/expenses.xlsx`

## Task 1: Bootstrap the project and application shell

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/expense_record/__init__.py`
- Create: `src/expense_record/config.py`
- Create: `src/expense_record/app.py`
- Create: `src/expense_record/templates/index.html`
- Create: `src/expense_record/static/app.css`
- Create: `src/expense_record/static/app.js`

- [ ] **Step 1: Write the failing application smoke test**

```python
# tests/test_api.py
from expense_record.app import create_app


def test_index_page_loads():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Expense Screenshot Tool" in response.data
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_api.py::test_index_page_loads -v`
Expected: FAIL with `ModuleNotFoundError` for `expense_record`

- [ ] **Step 3: Add project packaging and dependencies**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "expense-record"
version = "0.1.0"
description = "Local web app for extracting expense rows from phone screenshots"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "Flask>=3.0,<4.0",
  "openpyxl>=3.1,<4.0",
  "rapidocr-onnxruntime>=1.3.24,<2.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0,<9.0",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```gitignore
# .gitignore
__pycache__/
.pytest_cache/
.venv/
*.pyc
data/
```

```markdown
# README.md
# Expense Record

Local web app for turning bank-app screenshots into editable expense rows saved to Excel.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run

```bash
flask --app expense_record.app run --debug
```

## Test

```bash
pytest -v
```
```

- [ ] **Step 4: Implement the minimal Flask app shell**

```python
# src/expense_record/config.py
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DEFAULT_EXCEL_PATH = DATA_DIR / "expenses.xlsx"
```

```python
# src/expense_record/app.py
from flask import Flask, render_template


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(TESTING=False)

    if test_config:
        app.config.update(test_config)

    @app.get("/")
    def index():
        return render_template("index.html")

    return app
```

```html
<!-- src/expense_record/templates/index.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Expense Screenshot Tool</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='app.css') }}">
  </head>
  <body>
    <main class="app-shell">
      <h1>Expense Screenshot Tool</h1>
      <p>Paste or upload a screenshot to extract one expense row.</p>
      <div id="app"></div>
    </main>
    <script src="{{ url_for('static', filename='app.js') }}"></script>
  </body>
</html>
```

```css
/* src/expense_record/static/app.css */
body {
  margin: 0;
  font-family: sans-serif;
  background: #f4efe6;
  color: #1f1a17;
}

.app-shell {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 20px 48px;
}
```

```javascript
// src/expense_record/static/app.js
document.getElementById("app").textContent = "UI wiring will appear here.";
```

```python
# src/expense_record/__init__.py
from .app import create_app

__all__ = ["create_app"]
```

- [ ] **Step 5: Run the smoke test to verify it passes**

Run: `pytest tests/test_api.py::test_index_page_loads -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md .gitignore src/expense_record tests/test_api.py
git commit -m "chore: bootstrap expense screenshot app"
```

## Task 2: Implement parser and Excel storage services with tests first

**Files:**
- Create: `src/expense_record/models.py`
- Create: `src/expense_record/parser.py`
- Create: `src/expense_record/storage.py`
- Create: `tests/test_parser.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing parser tests**

```python
# tests/test_parser.py
from expense_record.parser import extract_expense_row


def test_extract_expense_row_parses_chinese_text():
    lines = [
        "交易时间 2026-03-30 08:15",
        "商户名称 瑞幸咖啡",
        "金额 -23.50",
    ]

    row = extract_expense_row(lines)

    assert row.date == "2026-03-30"
    assert row.merchant_item == "瑞幸咖啡"
    assert row.amount == "23.50"


def test_extract_expense_row_leaves_missing_fields_blank():
    lines = ["付款说明 早餐"]

    row = extract_expense_row(lines)

    assert row.date == ""
    assert row.merchant_item == "早餐"
    assert row.amount == ""
```

- [ ] **Step 2: Write failing storage tests**

```python
# tests/test_storage.py
from pathlib import Path

from expense_record.models import ExpenseRow
from expense_record.storage import ExcelExpenseStorage


def test_storage_creates_workbook_and_appends_rows(tmp_path: Path):
    excel_path = tmp_path / "expenses.xlsx"
    storage = ExcelExpenseStorage(excel_path)

    storage.append_row(ExpenseRow(date="2026-03-30", merchant_item="瑞幸咖啡", amount="23.50"))
    storage.append_row(ExpenseRow(date="2026-03-31", merchant_item="地铁", amount="4.00"))

    rows = storage.list_rows()

    assert rows == [
        ExpenseRow(date="2026-03-30", merchant_item="瑞幸咖啡", amount="23.50"),
        ExpenseRow(date="2026-03-31", merchant_item="地铁", amount="4.00"),
    ]
```

- [ ] **Step 3: Run parser and storage tests to verify they fail**

Run: `pytest tests/test_parser.py tests/test_storage.py -v`
Expected: FAIL with missing modules or missing functions

- [ ] **Step 4: Implement the shared data model and parser**

```python
# src/expense_record/models.py
from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ExpenseRow:
    date: str
    merchant_item: str
    amount: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
```

```python
# src/expense_record/parser.py
import re

from .models import ExpenseRow


DATE_RE = re.compile(r"(20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2})")
AMOUNT_RE = re.compile(r"(-?\d+(?:\.\d{1,2})?)")


def _normalize_date(value: str) -> str:
    return value.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-").replace(".", "-")


def _clean_amount(value: str) -> str:
    return value.lstrip("-+")


def extract_expense_row(lines: list[str]) -> ExpenseRow:
    date = ""
    amount = ""
    merchant_item = ""

    for line in lines:
        if not date:
            date_match = DATE_RE.search(line)
            if date_match:
                date = _normalize_date(date_match.group(1))

        if not amount and any(token in line for token in ("金额", "支付", "付款", "¥", "￥")):
            amount_match = AMOUNT_RE.search(line.replace("¥", "").replace("￥", ""))
            if amount_match:
                amount = _clean_amount(amount_match.group(1))

        if not merchant_item and any(token in line for token in ("商户", "名称", "说明", "备注")):
            merchant_item = line.split()[-1].replace("商户名称", "").replace("付款说明", "").strip(" :：")

    if not merchant_item:
        merchant_item = next(
            (
                line.strip()
                for line in lines
                if line.strip() and not DATE_RE.search(line) and not AMOUNT_RE.fullmatch(line.strip())
            ),
            "",
        )

    return ExpenseRow(date=date, merchant_item=merchant_item, amount=amount)
```

- [ ] **Step 5: Implement Excel storage**

```python
# src/expense_record/storage.py
from pathlib import Path

from openpyxl import Workbook, load_workbook

from .models import ExpenseRow


HEADERS = ("date", "merchant/item", "amount")


class ExcelExpenseStorage:
    def __init__(self, excel_path: Path):
        self.excel_path = excel_path

    def _ensure_workbook(self) -> None:
        if self.excel_path.exists():
            return

        self.excel_path.parent.mkdir(parents=True, exist_ok=True)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "expenses"
        sheet.append(HEADERS)
        workbook.save(self.excel_path)

    def append_row(self, row: ExpenseRow) -> None:
        self._ensure_workbook()
        workbook = load_workbook(self.excel_path)
        sheet = workbook.active
        sheet.append([row.date, row.merchant_item, row.amount])
        workbook.save(self.excel_path)

    def list_rows(self) -> list[ExpenseRow]:
        self._ensure_workbook()
        workbook = load_workbook(self.excel_path)
        sheet = workbook.active
        rows: list[ExpenseRow] = []

        for date, merchant_item, amount in sheet.iter_rows(min_row=2, values_only=True):
            rows.append(
                ExpenseRow(
                    date=str(date or ""),
                    merchant_item=str(merchant_item or ""),
                    amount=str(amount or ""),
                )
            )

        return rows
```

- [ ] **Step 6: Run parser and storage tests to verify they pass**

Run: `pytest tests/test_parser.py tests/test_storage.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/expense_record/models.py src/expense_record/parser.py src/expense_record/storage.py tests/test_parser.py tests/test_storage.py
git commit -m "feat: add row parser and excel storage"
```

## Task 3: Add OCR service and extraction/save/list APIs

**Files:**
- Create: `src/expense_record/ocr.py`
- Create: `src/expense_record/api.py`
- Modify: `src/expense_record/app.py`
- Modify: `src/expense_record/config.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests for extract, save, and list**

```python
# tests/test_api.py
from io import BytesIO

from expense_record.app import create_app


def test_extract_endpoint_returns_parsed_row(monkeypatch):
    app = create_app({"TESTING": True})

    def fake_ocr(_image_bytes: bytes) -> list[str]:
        return ["交易时间 2026-03-30", "商户名称 瑞幸咖啡", "金额 -23.50"]

    monkeypatch.setattr("expense_record.api.run_ocr_lines", fake_ocr)
    client = app.test_client()

    response = client.post(
        "/api/extract",
        data={"image": (BytesIO(b"fake image"), "snip.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["row"] == {
        "date": "2026-03-30",
        "merchant_item": "瑞幸咖啡",
        "amount": "23.50",
    }


def test_save_endpoint_persists_row(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"},
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"}
    ]


def test_rows_endpoint_lists_saved_rows(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    client.post(
        "/api/save",
        json={"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"},
    )

    response = client.get("/api/rows")

    assert response.status_code == 200
    assert response.get_json()["rows"][0]["merchant_item"] == "瑞幸咖啡"
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run: `pytest tests/test_api.py -v`
Expected: FAIL with missing routes or missing OCR service

- [ ] **Step 3: Implement the OCR service**

```python
# src/expense_record/ocr.py
from rapidocr_onnxruntime import RapidOCR


_engine: RapidOCR | None = None


def _get_engine() -> RapidOCR:
    global _engine
    if _engine is None:
        _engine = RapidOCR()
    return _engine


def run_ocr_lines(image_bytes: bytes) -> list[str]:
    engine = _get_engine()
    result, _ = engine(image_bytes)
    if not result:
        return []

    return [entry[1] for entry in result if entry and len(entry) > 1 and entry[1].strip()]
```

- [ ] **Step 4: Implement API routes and wire services into the app**

```python
# src/expense_record/api.py
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from .config import DEFAULT_EXCEL_PATH
from .models import ExpenseRow
from .ocr import run_ocr_lines
from .parser import extract_expense_row
from .storage import ExcelExpenseStorage


api = Blueprint("api", __name__, url_prefix="/api")


def _storage() -> ExcelExpenseStorage:
    excel_path = Path(current_app.config.get("EXCEL_PATH", DEFAULT_EXCEL_PATH))
    return ExcelExpenseStorage(excel_path)


@api.get("/rows")
def list_rows():
    rows = [row.to_dict() for row in _storage().list_rows()]
    return jsonify({"rows": rows})


@api.post("/extract")
def extract_row():
    image = request.files.get("image")
    if image is None or image.filename == "":
        return jsonify({"error": "No image provided."}), 400

    lines = run_ocr_lines(image.read())
    row = extract_expense_row(lines)
    return jsonify({"row": row.to_dict(), "lines": lines})


@api.post("/save")
def save_row():
    payload = request.get_json(silent=True) or {}
    row = ExpenseRow(
        date=str(payload.get("date", "")).strip(),
        merchant_item=str(payload.get("merchant_item", "")).strip(),
        amount=str(payload.get("amount", "")).strip(),
    )
    _storage().append_row(row)
    rows = [item.to_dict() for item in _storage().list_rows()]
    return jsonify({"rows": rows})
```

```python
# src/expense_record/app.py
from flask import Flask, render_template

from .api import api
from .config import DEFAULT_EXCEL_PATH


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(TESTING=False, EXCEL_PATH=DEFAULT_EXCEL_PATH)

    if test_config:
        app.config.update(test_config)

    app.register_blueprint(api)

    @app.get("/")
    def index():
        return render_template("index.html")

    return app
```

- [ ] **Step 5: Run the API tests to verify they pass**

Run: `pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/expense_record/app.py src/expense_record/api.py src/expense_record/ocr.py src/expense_record/config.py tests/test_api.py
git commit -m "feat: add extraction and save APIs"
```

## Task 4: Build the browser workflow for paste, upload, preview, edit, and save

**Files:**
- Modify: `src/expense_record/templates/index.html`
- Modify: `src/expense_record/static/app.css`
- Modify: `src/expense_record/static/app.js`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write a failing HTML smoke assertion for the review form container**

```python
# tests/test_api.py
from expense_record.app import create_app


def test_index_page_contains_review_form_container():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert b'id="expense-form"' in response.data
    assert b'id="records-table"' in response.data
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `pytest tests/test_api.py::test_index_page_contains_review_form_container -v`
Expected: FAIL because the UI containers do not exist yet

- [ ] **Step 3: Replace the placeholder page with the full day-one UI**

```html
<!-- src/expense_record/templates/index.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Expense Screenshot Tool</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='app.css') }}">
  </head>
  <body>
    <main class="app-shell">
      <header class="hero">
        <p class="eyebrow">Local OCR to Excel</p>
        <h1>Expense Screenshot Tool</h1>
        <p>Paste a phone snip or upload an image, review the extracted row, then save it into Excel.</p>
      </header>

      <section class="panel">
        <h2>1. Add screenshot</h2>
        <div id="paste-zone" class="paste-zone" tabindex="0">Paste screenshot here with Ctrl+V</div>
        <input id="file-input" type="file" accept="image/*">
        <img id="preview-image" class="preview-image" alt="Selected screenshot preview">
        <button id="extract-button" type="button">Extract</button>
        <p id="status-message" class="status-message"></p>
      </section>

      <section class="panel">
        <h2>2. Review row</h2>
        <form id="expense-form">
          <label>Date <input id="date-input" name="date"></label>
          <label>Merchant/Item <input id="merchant-input" name="merchant_item"></label>
          <label>Amount <input id="amount-input" name="amount"></label>
          <button id="save-button" type="submit">Save to Excel</button>
        </form>
      </section>

      <section class="panel">
        <h2>Saved records</h2>
        <table id="records-table">
          <thead>
            <tr><th>Date</th><th>Merchant/Item</th><th>Amount</th></tr>
          </thead>
          <tbody id="records-body"></tbody>
        </table>
      </section>
    </main>
    <script src="{{ url_for('static', filename='app.js') }}"></script>
  </body>
</html>
```

```css
/* src/expense_record/static/app.css */
:root {
  --bg: #f4efe6;
  --panel: rgba(255, 252, 247, 0.9);
  --ink: #1f1a17;
  --accent: #9c4d16;
  --line: #d8c7b3;
}

body {
  margin: 0;
  font-family: "Helvetica Neue", Arial, sans-serif;
  background:
    radial-gradient(circle at top, rgba(156, 77, 22, 0.18), transparent 36%),
    linear-gradient(180deg, #f7f2ea 0%, var(--bg) 100%);
  color: var(--ink);
}

.app-shell {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 20px 48px;
}

.hero {
  margin-bottom: 24px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent);
  font-size: 12px;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 20px;
  margin-bottom: 20px;
}

.paste-zone,
.preview-image,
input,
button,
table {
  width: 100%;
}

.paste-zone {
  min-height: 110px;
  border: 2px dashed var(--line);
  display: grid;
  place-items: center;
  margin-bottom: 12px;
}

.preview-image {
  display: none;
  max-height: 420px;
  object-fit: contain;
  margin: 12px 0;
}

#expense-form {
  display: grid;
  gap: 12px;
}

label {
  display: grid;
  gap: 6px;
}

input,
button {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--line);
}

button {
  cursor: pointer;
  background: var(--accent);
  color: white;
}

table {
  border-collapse: collapse;
}

th,
td {
  border-bottom: 1px solid var(--line);
  text-align: left;
  padding: 10px 8px;
}
```

```javascript
// src/expense_record/static/app.js
const elements = {
  fileInput: document.getElementById("file-input"),
  pasteZone: document.getElementById("paste-zone"),
  previewImage: document.getElementById("preview-image"),
  extractButton: document.getElementById("extract-button"),
  saveButton: document.getElementById("save-button"),
  statusMessage: document.getElementById("status-message"),
  form: document.getElementById("expense-form"),
  dateInput: document.getElementById("date-input"),
  merchantInput: document.getElementById("merchant-input"),
  amountInput: document.getElementById("amount-input"),
  recordsBody: document.getElementById("records-body"),
};

let selectedFile = null;

function setStatus(message, isError = false) {
  elements.statusMessage.textContent = message;
  elements.statusMessage.style.color = isError ? "#a12222" : "#1f1a17";
}

function renderPreview(file) {
  const reader = new FileReader();
  reader.onload = () => {
    elements.previewImage.src = reader.result;
    elements.previewImage.style.display = "block";
  };
  reader.readAsDataURL(file);
}

function setSelectedFile(file) {
  selectedFile = file;
  renderPreview(file);
  setStatus(`Loaded ${file.name}. Ready to extract.`);
}

async function loadRows() {
  const response = await fetch("/api/rows");
  const data = await response.json();
  elements.recordsBody.innerHTML = "";

  for (const row of data.rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.date}</td><td>${row.merchant_item}</td><td>${row.amount}</td>`;
    elements.recordsBody.appendChild(tr);
  }
}

async function extractRow() {
  if (!selectedFile) {
    setStatus("Select or paste an image before extracting.", true);
    return;
  }

  const formData = new FormData();
  formData.append("image", selectedFile);

  const response = await fetch("/api/extract", { method: "POST", body: formData });
  const data = await response.json();

  if (!response.ok) {
    setStatus(data.error || "Extraction failed.", true);
    return;
  }

  elements.dateInput.value = data.row.date;
  elements.merchantInput.value = data.row.merchant_item;
  elements.amountInput.value = data.row.amount;
  setStatus("Extraction complete. Review the row before saving.");
}

async function saveRow(event) {
  event.preventDefault();

  const payload = {
    date: elements.dateInput.value.trim(),
    merchant_item: elements.merchantInput.value.trim(),
    amount: elements.amountInput.value.trim(),
  };

  const response = await fetch("/api/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();

  if (!response.ok) {
    setStatus(data.error || "Save failed.", true);
    return;
  }

  await loadRows();
  setStatus("Row saved to Excel.");
}

elements.fileInput.addEventListener("change", (event) => {
  const [file] = event.target.files;
  if (file) {
    setSelectedFile(file);
  }
});

elements.pasteZone.addEventListener("paste", (event) => {
  const item = [...event.clipboardData.items].find((entry) => entry.type.startsWith("image/"));
  if (!item) {
    setStatus("Clipboard does not contain an image.", true);
    return;
  }
  const file = item.getAsFile();
  if (file) {
    setSelectedFile(new File([file], "clipboard-snip.png", { type: file.type }));
  }
});

elements.extractButton.addEventListener("click", extractRow);
elements.form.addEventListener("submit", saveRow);

loadRows().catch(() => setStatus("Could not load saved rows.", true));
```

- [ ] **Step 4: Run the smoke test to verify it passes**

Run: `pytest tests/test_api.py::test_index_page_contains_review_form_container -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/expense_record/templates/index.html src/expense_record/static/app.css src/expense_record/static/app.js tests/test_api.py
git commit -m "feat: add screenshot upload review workflow"
```

## Task 5: Add error handling, workbook-path documentation, and full verification

**Files:**
- Modify: `src/expense_record/api.py`
- Modify: `src/expense_record/static/app.js`
- Modify: `README.md`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing error-path tests**

```python
# tests/test_api.py
def test_extract_endpoint_rejects_missing_image():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.post("/api/extract", data={}, content_type="multipart/form-data")

    assert response.status_code == 400
    assert response.get_json()["error"] == "No image provided."


def test_save_endpoint_allows_blank_manual_corrections(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={"date": "", "merchant_item": "手动补录", "amount": ""},
    )

    assert response.status_code == 200
    assert response.get_json()["rows"][0]["merchant_item"] == "手动补录"
```

- [ ] **Step 2: Run the error-path tests to verify current gaps**

Run: `pytest tests/test_api.py::test_extract_endpoint_rejects_missing_image tests/test_api.py::test_save_endpoint_allows_blank_manual_corrections -v`
Expected: FAIL if routes do not yet return the expected payloads consistently

- [ ] **Step 3: Tighten API responses and frontend error messaging**

```python
# src/expense_record/api.py
@api.post("/extract")
def extract_row():
    image = request.files.get("image")
    if image is None or image.filename == "":
        return jsonify({"error": "No image provided."}), 400

    lines = run_ocr_lines(image.read())
    row = extract_expense_row(lines)
    return jsonify(
        {
            "row": row.to_dict(),
            "lines": lines,
            "warning": "" if any(row.to_dict().values()) else "OCR returned no usable fields.",
        }
    )
```

```javascript
// src/expense_record/static/app.js
async function extractRow() {
  if (!selectedFile) {
    setStatus("Select or paste an image before extracting.", true);
    return;
  }

  const formData = new FormData();
  formData.append("image", selectedFile);

  const response = await fetch("/api/extract", { method: "POST", body: formData });
  const data = await response.json();

  if (!response.ok) {
    setStatus(data.error || "Extraction failed.", true);
    return;
  }

  elements.dateInput.value = data.row.date;
  elements.merchantInput.value = data.row.merchant_item;
  elements.amountInput.value = data.row.amount;
  setStatus(data.warning || "Extraction complete. Review the row before saving.", Boolean(data.warning));
}
```

```markdown
# README.md
## Excel output

The app writes saved rows to `data/expenses.xlsx` by default. Set a different path with:

```bash
export FLASK_APP=expense_record.app
export EXPENSE_RECORD_EXCEL_PATH=/absolute/path/to/expenses.xlsx
```
```

- [ ] **Step 4: Update configuration to honor an environment override**

```python
# src/expense_record/config.py
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DEFAULT_EXCEL_PATH = Path(os.environ.get("EXPENSE_RECORD_EXCEL_PATH", DATA_DIR / "expenses.xlsx"))
```

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: PASS

- [ ] **Step 6: Run the app manually for a final local check**

Run: `flask --app expense_record.app run --debug`
Expected: Flask starts on `http://127.0.0.1:5000`, the page loads, rows list loads, and paste/upload plus save workflow is ready for manual screenshot testing

- [ ] **Step 7: Commit**

```bash
git add src/expense_record/api.py src/expense_record/static/app.js src/expense_record/config.py README.md tests/test_api.py
git commit -m "feat: finalize local expense capture workflow"
```

## Self-Review

### Spec coverage

- Single screenshot import: covered by Task 4 upload and paste UI
- Original-language OCR: covered by Task 3 OCR service and Task 2 parser behavior
- Editable review before save: covered by Task 4 review form
- Excel persistence with creation-on-first-save: covered by Task 2 storage
- Saved rows table in the page: covered by Task 3 rows API and Task 4 table rendering
- Error handling for missing image and weak OCR: covered by Task 5

### Placeholder scan

No `TODO`, `TBD`, or deferred implementation markers remain in the plan.

### Type consistency

- Shared row shape is consistently `date`, `merchant_item`, `amount`
- Storage, parser, API, and frontend payload names match
- Default workbook path remains `data/expenses.xlsx`, with environment override added in Task 5
