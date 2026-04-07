const elements = {
  fileInput: document.getElementById("file-input"),
  pasteZone: document.getElementById("paste-zone"),
  previewImage: document.getElementById("preview-image"),
  previewCaption: document.getElementById("preview-caption"),
  statementFileInput: document.getElementById("statement-file-input"),
  importStatementButton: document.getElementById("import-statement-button"),
  ocrLinesPanel: document.getElementById("ocr-lines-panel"),
  ocrLinesList: document.getElementById("ocr-lines-list"),
  extractButton: document.getElementById("extract-button"),
  saveButton: document.getElementById("save-button"),
  statusMessage: document.getElementById("status-message"),
  reviewBody: document.getElementById("review-body"),
  reviewHeader: document.getElementById("review-header"),
  recordsBody: document.getElementById("records-body"),
  copyAllButton: document.getElementById("copy-all-button"),
  clearHistoryButton: document.getElementById("clear-history-button"),
};

let selectedFile = null;
let selectedStatementFile = null;
let activeMode = "image";
let activeSelectionToken = 0;
let latestExtractRequestToken = 0;
let latestImportRequestToken = 0;
let extractedSelectionToken = 0;

function setStatus(message, isError = false) {
  elements.statusMessage.textContent = message;
  elements.statusMessage.style.color = isError ? "#9d2d22" : "";
}

function clearPreview() {
  elements.previewImage.hidden = true;
  elements.previewImage.removeAttribute("src");
}

function clearChildren(element) {
  while (element.children.length) {
    element.removeChild(element.children[0]);
  }
}

function clearOcrLines() {
  elements.ocrLinesPanel.hidden = true;
  clearChildren(elements.ocrLinesList);
}

function renderOcrLines(lines) {
  clearOcrLines();
  const visibleLines = Array.isArray(lines) ? lines : [];
  if (!visibleLines.length) {
    return;
  }

  for (const line of visibleLines) {
    const item = document.createElement("li");
    item.textContent = String(line ?? "");
    elements.ocrLinesList.appendChild(item);
  }
  elements.ocrLinesPanel.hidden = false;
}

function clearReviewRows() {
  clearChildren(elements.reviewBody);
}

function renderReviewHeader(mode) {
  if (!elements.reviewHeader) {
    return;
  }

  const headers =
    mode === "statement"
      ? ["Use", "Transaction Time", "Counterparty", "Direction", "Amount"]
      : ["Use", "Date", "Merchant / Item", "Amount"];

  clearChildren(elements.reviewHeader);
  for (const label of headers) {
    const th = document.createElement("th");
    th.textContent = label;
    elements.reviewHeader.appendChild(th);
  }
}

function createInputCell(value, placeholder) {
  const td = document.createElement("td");
  const input = document.createElement("input");
  input.type = "text";
  input.value = String(value ?? "");
  input.placeholder = placeholder;
  td.appendChild(input);
  return td;
}

function renderReviewRows(rows) {
  renderReviewHeader("image");
  clearReviewRows();
  const normalizedRows = Array.isArray(rows) ? rows : [];
  for (const row of normalizedRows) {
    const tr = document.createElement("tr");

    const checkboxCell = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkboxCell.appendChild(checkbox);
    tr.appendChild(checkboxCell);

    tr.appendChild(createInputCell(row.date, "MM-DD"));
    tr.appendChild(createInputCell(row.merchant_item, "Merchant or description"));
    tr.appendChild(createInputCell(row.amount, "0.00"));

    elements.reviewBody.appendChild(tr);
  }

  elements.saveButton.disabled = normalizedRows.length === 0;
}

function renderStatementReviewRows(rows) {
  renderReviewHeader("statement");
  clearReviewRows();
  const normalizedRows = Array.isArray(rows) ? rows : [];
  for (const row of normalizedRows) {
    const tr = document.createElement("tr");

    const checkboxCell = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkboxCell.appendChild(checkbox);
    tr.appendChild(checkboxCell);

    tr.appendChild(createInputCell(row.transaction_time, "YYYY-MM-DD HH:MM:SS"));
    tr.appendChild(createInputCell(row.counterparty, "Counterparty"));
    tr.appendChild(createInputCell(row.direction, "支出 / 收入 / 不计收支"));
    tr.appendChild(createInputCell(row.amount, "0.00"));

    elements.reviewBody.appendChild(tr);
  }

  elements.saveButton.disabled = normalizedRows.length === 0;
}

function clearReviewState() {
  clearReviewRows();
  elements.saveButton.disabled = true;
}

function resetSelectionState(label) {
  clearPreview();
  clearOcrLines();
  elements.previewCaption.textContent = label;
  clearReviewState();
  extractedSelectionToken = 0;
}

function setSelectedFile(file, label = file.name) {
  selectedFile = file;
  selectedStatementFile = null;
  activeMode = "image";
  activeSelectionToken += 1;
  const selectionToken = activeSelectionToken;
  latestExtractRequestToken = 0;
  latestImportRequestToken = 0;
  resetSelectionState(label);
  elements.statementFileInput.value = "";
  elements.importStatementButton.disabled = true;
  elements.extractButton.disabled = false;
  renderReviewHeader("image");
  renderPreview(file, selectionToken);
  setStatus(`Loaded ${label}. Ready to extract.`);
}

function setSelectedStatementFile(file, label = file.name) {
  selectedStatementFile = file;
  selectedFile = null;
  activeMode = "statement";
  activeSelectionToken += 1;
  latestExtractRequestToken = 0;
  latestImportRequestToken = 0;
  resetSelectionState("No screenshot selected yet.");
  elements.fileInput.value = "";
  elements.extractButton.disabled = true;
  elements.importStatementButton.disabled = false;
  renderReviewHeader("statement");
  setStatus(`Loaded ${label}. Ready to import.`);
}

function renderPreview(file, selectionToken) {
  const reader = new FileReader();
  reader.onload = () => {
    if (selectionToken !== activeSelectionToken) {
      return;
    }
    elements.previewImage.src = String(reader.result);
    elements.previewImage.hidden = false;
  };
  reader.onerror = () => {
    if (selectionToken !== activeSelectionToken) {
      return;
    }
    setStatus("Could not read the selected image.", true);
  };
  reader.readAsDataURL(file);
}

function clearRows() {
  clearChildren(elements.recordsBody);
}

function renderRows(rows) {
  clearRows();

  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 4;
    td.textContent = "No saved records yet.";
    tr.appendChild(td);
    elements.recordsBody.appendChild(tr);
    return;
  }

  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const key of ["date", "merchant_item", "amount", "direction"]) {
      const td = document.createElement("td");
      td.textContent = row[key] ?? "";
      tr.appendChild(td);
    }
    elements.recordsBody.appendChild(tr);
  }
}

async function loadRows() {
  const response = await fetch("/api/rows");
  const data = await response.json();
  renderRows(Array.isArray(data.rows) ? data.rows : []);
}

async function extractRows() {
  if (!selectedFile) {
    setStatus("Select or paste an image before extracting.", true);
    return;
  }

  const selectionToken = activeSelectionToken;
  const requestToken = ++latestExtractRequestToken;
  elements.extractButton.disabled = true;
  setStatus("Extracting screenshot text...");

  const formData = new FormData();
  formData.append("image", selectedFile, selectedFile.name || "screenshot.png");

  try {
    const response = await fetch("/api/extract", { method: "POST", body: formData });
    const data = await response.json();

    if (selectionToken !== activeSelectionToken || requestToken !== latestExtractRequestToken) {
      return;
    }

    if (!response.ok) {
      clearOcrLines();
      clearReviewState();
      setStatus(data.error || "Extraction failed.", true);
      return;
    }

    activeMode = "image";
    renderReviewRows(data.rows);
    renderOcrLines(data.lines);
    extractedSelectionToken = Array.isArray(data.rows) && data.rows.length > 0 ? selectionToken : 0;
    setStatus(
      data.warning || "Extraction complete. Review the rows before saving.",
      Boolean(data.warning)
    );
  } catch (_error) {
    if (selectionToken !== activeSelectionToken || requestToken !== latestExtractRequestToken) {
      return;
    }
    clearOcrLines();
    clearReviewState();
    setStatus("Extraction failed.", true);
  } finally {
    if (selectionToken === activeSelectionToken && requestToken === latestExtractRequestToken) {
      elements.extractButton.disabled = false;
    }
  }
}

async function importStatementRows() {
  if (!selectedStatementFile) {
    setStatus("Choose a statement file before importing.", true);
    return;
  }

  const selectionToken = activeSelectionToken;
  const requestToken = ++latestImportRequestToken;
  elements.importStatementButton.disabled = true;
  setStatus("Importing statement file...");

  const formData = new FormData();
  formData.append("statement_file", selectedStatementFile, selectedStatementFile.name);

  try {
    const response = await fetch("/api/import-statement", { method: "POST", body: formData });
    const data = await response.json();

    if (selectionToken !== activeSelectionToken || requestToken !== latestImportRequestToken) {
      return;
    }

    if (!response.ok) {
      clearReviewState();
      setStatus(data.error || "Statement import failed.", true);
      return;
    }

    activeMode = "statement";
    extractedSelectionToken = 0;
    renderStatementReviewRows(data.rows);
    setStatus("Statement imported. Review the rows before saving.");
  } catch (_error) {
    if (selectionToken !== activeSelectionToken || requestToken !== latestImportRequestToken) {
      return;
    }
    clearReviewState();
    setStatus("Statement import failed.", true);
  } finally {
    if (selectionToken === activeSelectionToken && requestToken === latestImportRequestToken) {
      elements.importStatementButton.disabled = false;
    }
  }
}

function collectReviewRows() {
  if (activeMode === "statement") {
    return Array.from(elements.reviewBody.children).map((row) => ({
      selected: Boolean(row.children[0].children[0].checked),
      transaction_time: row.children[1].children[0].value.trim(),
      counterparty: row.children[2].children[0].value.trim(),
      direction: row.children[3].children[0].value.trim(),
      amount: row.children[4].children[0].value.trim(),
    }));
  }

  return Array.from(elements.reviewBody.children).map((row) => ({
    selected: Boolean(row.children[0].children[0].checked),
    date: row.children[1].children[0].value.trim(),
    merchant_item: row.children[2].children[0].value.trim(),
    amount: row.children[3].children[0].value.trim(),
  }));
}

async function saveRows() {
  if (elements.saveButton.disabled) {
    setStatus(
      activeMode === "statement"
        ? "Import a statement before saving."
        : "Extract the current screenshot before saving.",
      true
    );
    return;
  }

  if (activeMode === "image" && extractedSelectionToken !== activeSelectionToken) {
    setStatus("Extract the current screenshot before saving.", true);
    return;
  }

  const selectionToken = activeSelectionToken;
  elements.saveButton.disabled = true;
  let saveSucceeded = false;

  try {
    const response = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: activeMode, rows: collectReviewRows() }),
    });
    const data = await response.json();

    if (selectionToken !== activeSelectionToken) {
      return;
    }

    if (!response.ok) {
      setStatus(data.error || "Save failed.", true);
      return;
    }

    renderRows(Array.isArray(data.rows) ? data.rows : []);
    clearReviewState();
    extractedSelectionToken = 0;
    setStatus("Rows saved to Excel.");
    saveSucceeded = true;
  } catch (_error) {
    if (selectionToken !== activeSelectionToken) {
      return;
    }
    setStatus("Save failed.", true);
  } finally {
    if (selectionToken === activeSelectionToken && !saveSucceeded) {
      elements.saveButton.disabled = false;
    }
  }
}

function handleFileSelection(file) {
  if (!file) {
    return;
  }
  setSelectedFile(file);
}

function handleStatementFileSelection(file) {
  if (!file) {
    return;
  }
  setSelectedStatementFile(file);
}

function isEditablePasteTarget(target) {
  if (!target) {
    return false;
  }
  const tagName = String(target.tagName ?? "").toUpperCase();
  return tagName === "INPUT" || tagName === "TEXTAREA" || target.isContentEditable === true;
}

function handlePaste(event) {
  if (isEditablePasteTarget(event.target)) {
    return;
  }

  const item = Array.from(event.clipboardData?.items ?? []).find((entry) => entry.type.startsWith("image/"));
  if (!item) {
    return;
  }

  const file = item.getAsFile();
  if (!file) {
    setStatus("Clipboard image could not be read.", true);
    return;
  }

  event.preventDefault();
  handleFileSelection(new File([file], file.name || "clipboard-snip.png", { type: file.type }));
}

elements.fileInput.addEventListener("change", (event) => {
  const [file] = event.target.files;
  handleFileSelection(file);
});

elements.statementFileInput.addEventListener("change", (event) => {
  const [file] = event.target.files;
  handleStatementFileSelection(file);
});

if (typeof document.addEventListener === "function") {
  document.addEventListener("paste", handlePaste);
}

elements.extractButton.addEventListener("click", () => {
  void extractRows();
});

elements.importStatementButton.addEventListener("click", () => {
  void importStatementRows();
});

elements.saveButton.addEventListener("click", () => {
  void saveRows();
});

async function clearHistory() {
  if (!confirm("Are you sure you want to clear all saved records?")) {
    return;
  }
  try {
    const response = await fetch("/api/rows", { method: "DELETE" });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || "Clear failed.", true);
      return;
    }
    renderRows([]);
    setStatus("All records cleared.");
  } catch (_error) {
    setStatus("Clear failed.", true);
  }
}

function copyAllRows() {
  const rows = Array.from(elements.recordsBody.children);
  const hasOnlyEmptyStateRow =
    rows.length === 1 &&
    rows[0].children.length === 1 &&
    Number(rows[0].children[0].colSpan || 0) > 1;

  if (!rows.length || hasOnlyEmptyStateRow) {
    setStatus("No records to copy.", true);
    return;
  }
  const header = "Date\tMerchant / Item\tAmount\tDirection";
  const lines = rows.map((tr) =>
    Array.from(tr.children).map((td) => td.textContent).join("\t")
  );
  const text = [header, ...lines].join("\n");
  navigator.clipboard.writeText(text).then(
    () => setStatus("Copied all records to clipboard."),
    () => setStatus("Copy failed.", true)
  );
}

elements.extractButton.disabled = true;
elements.importStatementButton.disabled = true;
elements.saveButton.disabled = true;

elements.clearHistoryButton.addEventListener("click", () => {
  void clearHistory();
});

elements.copyAllButton.addEventListener("click", () => {
  copyAllRows();
});

void loadRows().catch(() => {
  setStatus("Could not load saved rows.", true);
  renderRows([]);
});
