const elements = {
  fileInput: document.getElementById("file-input"),
  pasteZone: document.getElementById("paste-zone"),
  previewImage: document.getElementById("preview-image"),
  previewCaption: document.getElementById("preview-caption"),
  ocrLinesPanel: document.getElementById("ocr-lines-panel"),
  ocrLinesList: document.getElementById("ocr-lines-list"),
  extractButton: document.getElementById("extract-button"),
  saveButton: document.getElementById("save-button"),
  statusMessage: document.getElementById("status-message"),
  reviewBody: document.getElementById("review-body"),
  recordsBody: document.getElementById("records-body"),
};

let selectedFile = null;
let activeSelectionToken = 0;
let latestExtractRequestToken = 0;
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
  activeSelectionToken += 1;
  const selectionToken = activeSelectionToken;
  latestExtractRequestToken = 0;
  resetSelectionState(label);
  elements.extractButton.disabled = false;
  renderPreview(file, selectionToken);
  setStatus(`Loaded ${label}. Ready to extract.`);
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
    td.colSpan = 3;
    td.textContent = "No saved records yet.";
    tr.appendChild(td);
    elements.recordsBody.appendChild(tr);
    return;
  }

  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const key of ["date", "merchant_item", "amount"]) {
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

function collectReviewRows() {
  return Array.from(elements.reviewBody.children).map((row) => ({
    selected: Boolean(row.children[0].children[0].checked),
    date: row.children[1].children[0].value.trim(),
    merchant_item: row.children[2].children[0].value.trim(),
    amount: row.children[3].children[0].value.trim(),
  }));
}

async function saveRows() {
  if (elements.saveButton.disabled || extractedSelectionToken !== activeSelectionToken) {
    setStatus("Extract the current screenshot before saving.", true);
    return;
  }

  const selectionToken = activeSelectionToken;
  elements.saveButton.disabled = true;

  try {
    const response = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rows: collectReviewRows() }),
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
  } catch (_error) {
    if (selectionToken !== activeSelectionToken) {
      return;
    }
    setStatus("Save failed.", true);
  } finally {
    if (selectionToken === activeSelectionToken && extractedSelectionToken === activeSelectionToken) {
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

if (typeof document.addEventListener === "function") {
  document.addEventListener("paste", handlePaste);
}

elements.extractButton.addEventListener("click", () => {
  void extractRows();
});

elements.saveButton.addEventListener("click", () => {
  void saveRows();
});

elements.extractButton.disabled = true;
elements.saveButton.disabled = true;

void loadRows().catch(() => {
  setStatus("Could not load saved rows.", true);
  renderRows([]);
});
