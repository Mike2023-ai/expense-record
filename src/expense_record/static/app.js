const elements = {
  fileInput: document.getElementById("file-input"),
  pasteZone: document.getElementById("paste-zone"),
  previewImage: document.getElementById("preview-image"),
  previewCaption: document.getElementById("preview-caption"),
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
let activeSelectionToken = 0;
let latestExtractRequestToken = 0;
let extractedSelectionToken = 0;

function setStatus(message, isError = false) {
  elements.statusMessage.textContent = message;
  elements.statusMessage.style.color = isError ? "#9d2d22" : "";
}

function clearReviewForm() {
  elements.dateInput.value = "";
  elements.merchantInput.value = "";
  elements.amountInput.value = "";
}

function clearPreview() {
  elements.previewImage.hidden = true;
  elements.previewImage.removeAttribute("src");
}

function resetSelectionState(label) {
  clearPreview();
  elements.previewCaption.textContent = label;
  clearReviewForm();
  elements.saveButton.disabled = true;
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
  elements.recordsBody.innerHTML = "";
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

async function extractRow() {
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
      setStatus(data.error || "Extraction failed.", true);
      return;
    }

    elements.dateInput.value = data.row?.date ?? "";
    elements.merchantInput.value = data.row?.merchant_item ?? "";
    elements.amountInput.value = data.row?.amount ?? "";
    extractedSelectionToken = selectionToken;
    elements.saveButton.disabled = false;
    setStatus("Extraction complete. Review the row before saving.");
  } catch (_error) {
    if (selectionToken !== activeSelectionToken || requestToken !== latestExtractRequestToken) {
      return;
    }
    setStatus("Extraction failed.", true);
  } finally {
    if (selectionToken === activeSelectionToken && requestToken === latestExtractRequestToken) {
      elements.extractButton.disabled = false;
    }
  }
}

async function saveRow(event) {
  event.preventDefault();
  if (elements.saveButton.disabled || extractedSelectionToken !== activeSelectionToken) {
    setStatus("Extract the current screenshot before saving.", true);
    return;
  }

  const selectionToken = activeSelectionToken;
  elements.saveButton.disabled = true;

  const payload = {
    date: elements.dateInput.value.trim(),
    merchant_item: elements.merchantInput.value.trim(),
    amount: elements.amountInput.value.trim(),
  };

  try {
    const response = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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
    setStatus("Row saved to Excel.");
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

elements.fileInput.addEventListener("change", (event) => {
  const [file] = event.target.files;
  handleFileSelection(file);
});

elements.pasteZone.addEventListener("paste", (event) => {
  const item = Array.from(event.clipboardData?.items ?? []).find((entry) => entry.type.startsWith("image/"));
  if (!item) {
    setStatus("Clipboard does not contain an image.", true);
    return;
  }

  const file = item.getAsFile();
  if (!file) {
    setStatus("Clipboard image could not be read.", true);
    return;
  }

  handleFileSelection(new File([file], file.name || "clipboard-snip.png", { type: file.type }));
});

elements.extractButton.addEventListener("click", () => {
  void extractRow();
});

elements.form.addEventListener("submit", (event) => {
  void saveRow(event);
});

elements.extractButton.disabled = true;
elements.saveButton.disabled = true;

void loadRows().catch(() => {
  setStatus("Could not load saved rows.", true);
  renderRows([]);
});
