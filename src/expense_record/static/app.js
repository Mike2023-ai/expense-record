function byId(id) {
  return typeof document.getElementById === "function" ? document.getElementById(id) : null;
}

const elements = {
  fileInput: byId("file-input"),
  pasteZone: byId("paste-zone"),
  previewImage: byId("preview-image"),
  previewCaption: byId("preview-caption"),
  statementFileInput: byId("statement-file-input"),
  importStatementButton: byId("import-statement-button"),
  ocrLinesPanel: byId("ocr-lines-panel"),
  ocrLinesList: byId("ocr-lines-list"),
  extractButton: byId("extract-button"),
  saveButton: byId("save-button"),
  statusMessage: byId("status-message"),
  reviewBody: byId("review-body"),
  reviewHeader: byId("review-header"),
  recordsBody: byId("records-body"),
  copyAllButton: byId("copy-all-button"),
  clearHistoryButton: byId("clear-history-button"),
  manualEntryDate: byId("manual-entry-date"),
  manualEntryDescription: byId("manual-entry-description"),
  manualEntryDirection: byId("manual-entry-direction"),
  manualEntryAmount: byId("manual-entry-amount"),
  manualEntryCategory: byId("manual-entry-category"),
  manualEntryMember: byId("manual-entry-member"),
  manualEntryEntryType: byId("manual-entry-entry-type"),
  manualEntryNote: byId("manual-entry-note"),
  manualEntryButton: byId("manual-entry-button"),
  categoryName: byId("category-name"),
  addCategoryButton: byId("add-category-button"),
  memberName: byId("member-name"),
  addMemberButton: byId("add-member-button"),
  assetSnapshotDate: byId("asset-snapshot-date"),
  assetSnapshotCash: byId("asset-snapshot-cash"),
  assetSnapshotStock: byId("asset-snapshot-stock"),
  assetSnapshotNote: byId("asset-snapshot-note"),
  assetSnapshotButton: byId("asset-snapshot-button"),
  stockRecordDate: byId("stock-record-date"),
  stockRecordName: byId("stock-record-name"),
  stockRecordQuantity: byId("stock-record-quantity"),
  stockRecordPrice: byId("stock-record-price"),
  stockRecordTotalValue: byId("stock-record-total-value"),
  stockRecordNote: byId("stock-record-note"),
  stockRecordButton: byId("stock-record-button"),
  categoryOptions: byId("category-options"),
  memberOptions: byId("member-options"),
  dashboardExpenseCategory: byId("dashboard-expense-category"),
  dashboardMemberCategory: byId("dashboard-member-category"),
  dashboardCashFlow: byId("dashboard-cash-flow"),
  dashboardAssets: byId("dashboard-assets"),
};

const referenceData = {
  categories: [],
  members: [],
};

let selectedFile = null;
let selectedStatementFile = null;
let activeMode = "image";
let activeSelectionToken = 0;
let latestExtractRequestToken = 0;
let latestImportRequestToken = 0;
let extractedSelectionToken = 0;

function setStatus(message, isError = false) {
  if (!elements.statusMessage) {
    return;
  }
  elements.statusMessage.textContent = message;
  elements.statusMessage.style.color = isError ? "#9d2d22" : "";
}

function setDisabled(element, disabled) {
  if (element) {
    element.disabled = disabled;
  }
}

function clearChildren(element) {
  if (!element) {
    return;
  }
  if (typeof element.replaceChildren === "function") {
    element.replaceChildren();
    return;
  }
  while (element.children.length) {
    element.removeChild(element.children[0]);
  }
}

function clearPreview() {
  if (!elements.previewImage) {
    return;
  }
  elements.previewImage.hidden = true;
  if (typeof elements.previewImage.removeAttribute === "function") {
    elements.previewImage.removeAttribute("src");
  }
}

function clearOcrLines() {
  if (elements.ocrLinesPanel) {
    elements.ocrLinesPanel.hidden = true;
  }
  clearChildren(elements.ocrLinesList);
}

function renderOcrLines(lines) {
  clearOcrLines();
  if (!elements.ocrLinesPanel || !elements.ocrLinesList) {
    return;
  }
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

function renderReviewHeader(mode) {
  if (!elements.reviewHeader) {
    return;
  }
  const headers =
    mode === "statement"
      ? ["Use", "Date", "Description", "Amount", "Direction", "Category", "Member", "Source", "Entry Type", "Note"]
      : ["Use", "Date", "Merchant / Item", "Amount"];
  clearChildren(elements.reviewHeader);
  for (const label of headers) {
    const th = document.createElement("th");
    th.textContent = label;
    elements.reviewHeader.appendChild(th);
  }
}

function createTextInput(value, placeholder) {
  const input = document.createElement("input");
  input.type = "text";
  input.value = String(value ?? "");
  input.placeholder = placeholder;
  return input;
}

function createInputCell(value, placeholder) {
  const td = document.createElement("td");
  td.appendChild(createTextInput(value, placeholder));
  return td;
}

function createSelectWithOptions(options, selectedValue, placeholder) {
  const select = document.createElement("select");
  const emptyOption = document.createElement("option");
  emptyOption.value = "";
  emptyOption.textContent = placeholder;
  select.appendChild(emptyOption);
  for (const optionValue of options) {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = optionValue;
    if (optionValue === selectedValue) {
      option.selected = true;
    }
    select.appendChild(option);
  }
  select.value = selectedValue || "";
  return select;
}

function createSelectCell(options, selectedValue, placeholder) {
  const td = document.createElement("td");
  td.appendChild(createSelectWithOptions(options, selectedValue, placeholder));
  return td;
}

function clearReviewRows() {
  clearChildren(elements.reviewBody);
}

function clearReviewState() {
  clearReviewRows();
  setDisabled(elements.saveButton, true);
}

function renderImageReviewRows(rows) {
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
  setDisabled(elements.saveButton, normalizedRows.length === 0);
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
    tr.appendChild(createInputCell(row.date, "YYYY-MM-DD HH:MM:SS"));
    tr.appendChild(createInputCell(row.description, "Description"));
    tr.appendChild(createInputCell(row.amount, "+0.00 / -0.00"));
    tr.appendChild(createInputCell(row.direction, "expense / income"));
    tr.appendChild(createSelectCell(referenceData.categories, row.category, "Category"));
    tr.appendChild(createSelectCell(referenceData.members, row.member, "Member"));
    tr.appendChild(createInputCell(row.source, "Source"));
    tr.appendChild(createInputCell(row.entry_type, "Entry type"));
    tr.appendChild(createInputCell(row.note, "Note"));
    elements.reviewBody.appendChild(tr);
  }
  setDisabled(elements.saveButton, normalizedRows.length === 0);
}

function resetSelectionState(label) {
  clearPreview();
  clearOcrLines();
  if (elements.previewCaption) {
    elements.previewCaption.textContent = label;
  }
  clearReviewState();
  extractedSelectionToken = 0;
}

function renderPreview(file, selectionToken) {
  if (!elements.previewImage || typeof FileReader !== "function") {
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    if (selectionToken !== activeSelectionToken || !elements.previewImage) {
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
  if (typeof reader.readAsDataURL === "function") {
    reader.readAsDataURL(file);
  }
}

function setSelectedFile(file, label = file.name) {
  selectedFile = file;
  selectedStatementFile = null;
  activeMode = "image";
  activeSelectionToken += 1;
  latestExtractRequestToken = 0;
  latestImportRequestToken = 0;
  resetSelectionState(label);
  if (elements.statementFileInput) {
    elements.statementFileInput.value = "";
  }
  setDisabled(elements.importStatementButton, true);
  setDisabled(elements.extractButton, false);
  renderReviewHeader("image");
  renderPreview(file, activeSelectionToken);
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
  if (elements.fileInput) {
    elements.fileInput.value = "";
  }
  setDisabled(elements.extractButton, true);
  setDisabled(elements.importStatementButton, false);
  renderReviewHeader("statement");
  setStatus(`Loaded ${label}. Ready to import.`);
}

function renderRows(rows) {
  if (!elements.recordsBody) {
    return;
  }
  clearChildren(elements.recordsBody);
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
    for (const value of [row.date ?? "", row.merchant_item ?? row.description ?? "", row.amount ?? "", row.direction ?? ""]) {
      const td = document.createElement("td");
      td.textContent = value;
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

async function safeFetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `${url} failed.`);
  }
  return data;
}

function normalizeArray(values, key) {
  if (!Array.isArray(values)) {
    return [];
  }
  return values
    .map((value) => (typeof value === "string" ? value : value?.[key]))
    .filter((value) => typeof value === "string" && value.trim())
    .map((value) => value.trim());
}

function replaceSelectOptions(selectElement, values, placeholder) {
  if (!selectElement) {
    return;
  }
  const currentValue = selectElement.value || "";
  clearChildren(selectElement);
  const select = createSelectWithOptions(values, currentValue, placeholder);
  selectElement.children = select.children;
  if (typeof selectElement.replaceChildren === "function") {
    selectElement.replaceChildren(...select.children);
  } else {
    for (const child of select.children) {
      selectElement.appendChild(child);
    }
  }
  selectElement.value = values.includes(currentValue) ? currentValue : "";
}

function renderReferenceLists(values, element) {
  if (!element) {
    return;
  }
  clearChildren(element);
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = value;
    element.appendChild(item);
  }
}

function refreshReviewSelects() {
  if (!elements.reviewBody) {
    return;
  }
  for (const row of Array.from(elements.reviewBody.children)) {
    if (row.children.length < 7) {
      continue;
    }
    const categorySelect = row.children[5]?.children?.[0];
    const memberSelect = row.children[6]?.children?.[0];
    if (categorySelect && categorySelect.tagName === "SELECT") {
      replaceSelectOptions(categorySelect, referenceData.categories, "Category");
    }
    if (memberSelect && memberSelect.tagName === "SELECT") {
      replaceSelectOptions(memberSelect, referenceData.members, "Member");
    }
  }
}

async function loadReferenceData() {
  try {
    const [categoriesData, membersData] = await Promise.all([
      safeFetchJson("/api/categories"),
      safeFetchJson("/api/members"),
    ]);
    referenceData.categories = normalizeArray(categoriesData.categories, "category");
    referenceData.members = normalizeArray(membersData.members, "member");
    replaceSelectOptions(elements.manualEntryCategory, referenceData.categories, "Category");
    replaceSelectOptions(elements.manualEntryMember, referenceData.members, "Member");
    renderReferenceLists(referenceData.categories, elements.categoryOptions);
    renderReferenceLists(referenceData.members, elements.memberOptions);
    refreshReviewSelects();
  } catch (_error) {
    referenceData.categories = [];
    referenceData.members = [];
  }
}

function renderDashboardList(element, values, formatter) {
  if (!element) {
    return;
  }
  clearChildren(element);
  const rows = Array.isArray(values) ? values : [];
  if (!rows.length) {
    const item = document.createElement("li");
    item.textContent = "No data yet.";
    element.appendChild(item);
    return;
  }
  for (const row of rows) {
    const item = document.createElement("li");
    item.textContent = formatter(row);
    element.appendChild(item);
  }
}

async function loadDashboard() {
  try {
    const data = await safeFetchJson("/api/dashboard");
    renderDashboardList(elements.dashboardExpenseCategory, data.expense_by_category, (row) => `${row.category}: ${row.amount}`);
    renderDashboardList(
      elements.dashboardMemberCategory,
      data.expense_by_member_category,
      (row) => `${row.member} / ${row.category}: ${row.amount}`
    );
    renderDashboardList(
      elements.dashboardCashFlow,
      data.cash_flow,
      (row) => `${row.month}: income ${row.income_total}, expense ${row.expense_total}, net ${row.net_total}`
    );
    renderDashboardList(
      elements.dashboardAssets,
      data.asset_trend,
      (row) => `${row.month}: cash ${row.cash_or_balance_total}, stock ${row.stock_total_value}, total ${row.total_assets}`
    );
  } catch (_error) {
    renderDashboardList(elements.dashboardExpenseCategory, [], () => "");
    renderDashboardList(elements.dashboardMemberCategory, [], () => "");
    renderDashboardList(elements.dashboardCashFlow, [], () => "");
    renderDashboardList(elements.dashboardAssets, [], () => "");
  }
}

async function extractRows() {
  if (!selectedFile) {
    setStatus("Select or paste an image before extracting.", true);
    return;
  }
  const selectionToken = activeSelectionToken;
  const requestToken = ++latestExtractRequestToken;
  setDisabled(elements.extractButton, true);
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
    renderImageReviewRows(data.rows);
    renderOcrLines(data.lines);
    extractedSelectionToken = Array.isArray(data.rows) && data.rows.length > 0 ? selectionToken : 0;
    setStatus(data.warning || "Extraction complete. Review the rows before saving.", Boolean(data.warning));
  } catch (_error) {
    if (selectionToken !== activeSelectionToken || requestToken !== latestExtractRequestToken) {
      return;
    }
    clearOcrLines();
    clearReviewState();
    setStatus("Extraction failed.", true);
  } finally {
    if (selectionToken === activeSelectionToken && requestToken === latestExtractRequestToken) {
      setDisabled(elements.extractButton, false);
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
  setDisabled(elements.importStatementButton, true);
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
      setDisabled(elements.importStatementButton, false);
    }
  }
}

function collectReviewRows() {
  if (!elements.reviewBody) {
    return [];
  }
  if (activeMode === "statement") {
    return Array.from(elements.reviewBody.children).map((row) => ({
      selected: Boolean(row.children[0].children[0].checked),
      transaction_time: row.children[1].children[0].value.trim(),
      counterparty: row.children[2].children[0].value.trim(),
      amount: row.children[3].children[0].value.trim(),
      direction: row.children[4].children[0].value.trim(),
      category: row.children[5].children[0].value.trim(),
      member: row.children[6].children[0].value.trim(),
      source: row.children[7].children[0].value.trim(),
      entry_type: row.children[8].children[0].value.trim(),
      note: row.children[9].children[0].value.trim(),
    }));
  }
  return Array.from(elements.reviewBody.children).map((row) => ({
    selected: Boolean(row.children[0].children[0].checked),
    date: row.children[1].children[0].value.trim(),
    merchant_item: row.children[2].children[0].value.trim(),
    amount: row.children[3].children[0].value.trim(),
  }));
}

function hasMissingStatementAssignments(rows) {
  return rows.some((row) => row.selected && (!row.category || !row.member));
}

async function saveRows() {
  if (!elements.saveButton || elements.saveButton.disabled) {
    setStatus(activeMode === "statement" ? "Import a statement before saving." : "Extract the current screenshot before saving.", true);
    return;
  }
  if (activeMode === "image" && extractedSelectionToken !== activeSelectionToken) {
    setStatus("Extract the current screenshot before saving.", true);
    return;
  }
  const rows = collectReviewRows();
  if (activeMode === "statement" && hasMissingStatementAssignments(rows)) {
    setStatus("Category and member are required.", true);
    return;
  }
  const selectionToken = activeSelectionToken;
  setDisabled(elements.saveButton, true);
  let saveSucceeded = false;
  try {
    const response = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: activeMode, rows }),
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
    void loadDashboard();
  } catch (_error) {
    if (selectionToken !== activeSelectionToken) {
      return;
    }
    setStatus("Save failed.", true);
  } finally {
    if (selectionToken === activeSelectionToken && !saveSucceeded) {
      setDisabled(elements.saveButton, false);
    }
  }
}

function isEditablePasteTarget(target) {
  if (!target) {
    return false;
  }
  const tagName = String(target.tagName ?? "").toUpperCase();
  return tagName === "INPUT" || tagName === "TEXTAREA" || target.isContentEditable === true;
}

function handleFileSelection(file) {
  if (file) {
    setSelectedFile(file);
  }
}

function handleStatementFileSelection(file) {
  if (file) {
    setSelectedStatementFile(file);
  }
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
  if (typeof event.preventDefault === "function") {
    event.preventDefault();
  }
  handleFileSelection(new File([file], file.name || "clipboard-snip.png", { type: file.type }));
}

function payloadFromFields(fields) {
  const payload = {};
  for (const [key, element] of Object.entries(fields)) {
    payload[key] = String(element?.value ?? "").trim();
  }
  return payload;
}

async function postJson(url, payload, successMessage) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  setStatus(successMessage);
  return data;
}

function resetValues(fields) {
  for (const element of fields) {
    if (element) {
      element.value = "";
    }
  }
}

async function saveManualEntry() {
  const payload = payloadFromFields({
    date: elements.manualEntryDate,
    description: elements.manualEntryDescription,
    direction: elements.manualEntryDirection,
    amount: elements.manualEntryAmount,
    category: elements.manualEntryCategory,
    member: elements.manualEntryMember,
    entry_type: elements.manualEntryEntryType,
    note: elements.manualEntryNote,
  });
  try {
    await postJson("/api/manual-entry", payload, "Manual entry saved.");
    resetValues([
      elements.manualEntryDate,
      elements.manualEntryDescription,
      elements.manualEntryDirection,
      elements.manualEntryAmount,
      elements.manualEntryEntryType,
      elements.manualEntryNote,
    ]);
    if (elements.manualEntryCategory) {
      elements.manualEntryCategory.value = "";
    }
    if (elements.manualEntryMember) {
      elements.manualEntryMember.value = "";
    }
    void Promise.all([loadRows(), loadDashboard()]);
  } catch (error) {
    setStatus(error.message || "Manual entry failed.", true);
  }
}

async function addCategory() {
  try {
    const data = await postJson("/api/categories", { name: String(elements.categoryName?.value ?? "").trim() }, "Category added.");
    referenceData.categories = normalizeArray(data.categories, "category");
    replaceSelectOptions(elements.manualEntryCategory, referenceData.categories, "Category");
    renderReferenceLists(referenceData.categories, elements.categoryOptions);
    refreshReviewSelects();
    if (elements.categoryName) {
      elements.categoryName.value = "";
    }
  } catch (error) {
    setStatus(error.message || "Category update failed.", true);
  }
}

async function addMember() {
  try {
    const data = await postJson("/api/members", { name: String(elements.memberName?.value ?? "").trim() }, "Member added.");
    referenceData.members = normalizeArray(data.members, "member");
    replaceSelectOptions(elements.manualEntryMember, referenceData.members, "Member");
    renderReferenceLists(referenceData.members, elements.memberOptions);
    refreshReviewSelects();
    if (elements.memberName) {
      elements.memberName.value = "";
    }
  } catch (error) {
    setStatus(error.message || "Member update failed.", true);
  }
}

async function saveAssetSnapshot() {
  const payload = payloadFromFields({
    date: elements.assetSnapshotDate,
    cash_or_balance_total: elements.assetSnapshotCash,
    stock_total_value: elements.assetSnapshotStock,
    note: elements.assetSnapshotNote,
  });
  try {
    await postJson("/api/asset-snapshots", payload, "Asset snapshot saved.");
    resetValues([elements.assetSnapshotDate, elements.assetSnapshotCash, elements.assetSnapshotStock, elements.assetSnapshotNote]);
    void loadDashboard();
  } catch (error) {
    setStatus(error.message || "Asset snapshot failed.", true);
  }
}

async function saveStockRecord() {
  const payload = payloadFromFields({
    date: elements.stockRecordDate,
    stock_name: elements.stockRecordName,
    stock_quantity: elements.stockRecordQuantity,
    stock_price: elements.stockRecordPrice,
    stock_total_value: elements.stockRecordTotalValue,
    note: elements.stockRecordNote,
  });
  try {
    await postJson("/api/stock-records", payload, "Stock record saved.");
    resetValues([
      elements.stockRecordDate,
      elements.stockRecordName,
      elements.stockRecordQuantity,
      elements.stockRecordPrice,
      elements.stockRecordTotalValue,
      elements.stockRecordNote,
    ]);
    void loadDashboard();
  } catch (error) {
    setStatus(error.message || "Stock record failed.", true);
  }
}

async function clearHistory() {
  if (typeof confirm === "function" && !confirm("Are you sure you want to clear all saved records?")) {
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
    void loadDashboard();
  } catch (_error) {
    setStatus("Clear failed.", true);
  }
}

function copyAllRows() {
  if (!elements.recordsBody) {
    return;
  }
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
  const lines = rows.map((tr) => Array.from(tr.children).map((td) => td.textContent).join("\t"));
  const text = [header, ...lines].join("\n");
  navigator.clipboard.writeText(text).then(
    () => setStatus("Copied all records to clipboard."),
    () => setStatus("Copy failed.", true)
  );
}

if (elements.fileInput) {
  elements.fileInput.addEventListener("change", (event) => handleFileSelection(event.target.files?.[0]));
}
if (elements.statementFileInput) {
  elements.statementFileInput.addEventListener("change", (event) => handleStatementFileSelection(event.target.files?.[0]));
}
if (typeof document.addEventListener === "function") {
  document.addEventListener("paste", handlePaste);
}
if (elements.extractButton) {
  elements.extractButton.addEventListener("click", () => {
    void extractRows();
  });
}
if (elements.importStatementButton) {
  elements.importStatementButton.addEventListener("click", () => {
    void importStatementRows();
  });
}
if (elements.saveButton) {
  elements.saveButton.addEventListener("click", () => {
    void saveRows();
  });
}
if (elements.copyAllButton) {
  elements.copyAllButton.addEventListener("click", () => {
    copyAllRows();
  });
}
if (elements.clearHistoryButton) {
  elements.clearHistoryButton.addEventListener("click", () => {
    void clearHistory();
  });
}
if (elements.manualEntryButton) {
  elements.manualEntryButton.addEventListener("click", () => {
    void saveManualEntry();
  });
}
if (elements.addCategoryButton) {
  elements.addCategoryButton.addEventListener("click", () => {
    void addCategory();
  });
}
if (elements.addMemberButton) {
  elements.addMemberButton.addEventListener("click", () => {
    void addMember();
  });
}
if (elements.assetSnapshotButton) {
  elements.assetSnapshotButton.addEventListener("click", () => {
    void saveAssetSnapshot();
  });
}
if (elements.stockRecordButton) {
  elements.stockRecordButton.addEventListener("click", () => {
    void saveStockRecord();
  });
}

setDisabled(elements.extractButton, true);
setDisabled(elements.importStatementButton, true);
setDisabled(elements.saveButton, true);

void loadRows().catch(() => {
  setStatus("Could not load saved rows.", true);
  renderRows([]);
});
void loadReferenceData();
void loadDashboard();
