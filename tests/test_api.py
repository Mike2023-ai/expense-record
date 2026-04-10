import io
import shutil
from importlib import metadata
from pathlib import Path
import os
import subprocess
import sys
import textwrap
import zipfile
import sysconfig

import pytest
from openpyxl import Workbook

from expense_record.app import create_app
from expense_record.config import DEFAULT_CATEGORIES, DEFAULT_EXCEL_PATH, resolve_app_version
from expense_record.models import AssetSnapshot, LedgerEntry
from expense_record.storage import ExcelExpenseStorage
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    return app.test_client()


def test_index_page_contains_review_table_container():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'id="review-table"' in response.data
    assert b'id="review-body"' in response.data


def test_index_page_contains_statement_import_controls():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'id="statement-file-input"' in response.data
    assert b'id="import-statement-button"' in response.data


def test_index_page_uses_review_table_columns():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Use" in response.data
    assert b"Merchant / Item" in response.data


def test_index_page_contains_ocr_lines_debug_panel():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'id="ocr-lines-panel"' in response.data
    assert b'id="ocr-lines-list"' in response.data


def test_index_page_explains_paste_works_anywhere():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'id="paste-zone"' in response.data
    assert b"anywhere on the page" in response.data.lower()


def test_index_page_shows_app_version():
    app = create_app({"TESTING": True})
    client = app.test_client()
    expected_version = resolve_app_version()

    response = client.get("/")

    assert response.status_code == 200
    assert f"Version {expected_version}".encode() in response.data


def test_index_page_contains_family_finance_sections():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'id="manual-entry-section"' in response.data
    assert b'id="asset-snapshot-section"' in response.data
    assert b'id="stock-record-section"' in response.data
    assert b'id="dashboard-section"' in response.data


def test_frontend_statement_mode_selection_import_save_and_stale_responses():
    script = textwrap.dedent(
        """
        const fs = require("fs");
        const vm = require("vm");
        const path = require("path");
        const assert = require("assert");

        const source = fs.readFileSync(path.join(process.cwd(), "src/expense_record/static/app.js"), "utf8");

        function makeElement(id) {
          return {
            id,
            disabled: false,
            hidden: false,
            value: "",
            checked: false,
            textContent: "",
            innerHTML: "",
            className: "",
            type: "",
            src: "",
            style: {},
            files: [],
            listeners: {},
            children: [],
            addEventListener(type, handler) {
              this.listeners[type] = handler;
            },
            appendChild(child) {
              this.children.push(child);
            },
            removeChild(child) {
              const index = this.children.indexOf(child);
              if (index >= 0) {
                this.children.splice(index, 1);
              }
              return child;
            },
            replaceChildren(...children) {
              this.children = [...children];
            },
            removeAttribute(name) {
              if (name === "src") {
                this.src = "";
              }
            },
          };
        }

        const elements = {
          "file-input": makeElement("file-input"),
          "paste-zone": makeElement("paste-zone"),
          "preview-image": makeElement("preview-image"),
          "preview-caption": makeElement("preview-caption"),
          "statement-file-input": makeElement("statement-file-input"),
          "import-statement-button": makeElement("import-statement-button"),
          "extract-button": makeElement("extract-button"),
          "save-button": makeElement("save-button"),
          "status-message": makeElement("status-message"),
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
          "review-table": makeElement("review-table"),
          "review-header": makeElement("review-header"),
          "review-body": makeElement("review-body"),
          "records-body": makeElement("records-body"),
          "copy-all-button": makeElement("copy-all-button"),
          "clear-history-button": makeElement("clear-history-button"),
        };
        elements["preview-image"].hidden = true;
        const documentListeners = {};

        const fileReaderInstances = [];
        class FakeFileReader {
          constructor() {
            this.result = "";
            this.onload = null;
            this.onerror = null;
            fileReaderInstances.push(this);
          }
          readAsDataURL(file) {
            this.file = file;
          }
        }

        class FakeFile {
          constructor(parts, name, options) {
            this.parts = parts;
            this.name = name;
            this.type = options?.type ?? "";
          }
        }

        class FakeFormData {
          append() {}
        }

        const pendingExtractResponses = [];
        const pendingImportResponses = [];
        const pendingSaveResponses = [];
        const fetchCalls = [];

        function makeResponse(rows, lines = [], warning = "") {
          const payload = { rows, lines };
          if (warning) {
            payload.warning = warning;
          }
          return {
            ok: true,
            json: async () => payload,
          };
        }

        const sandbox = {
          console,
          process,
          FileReader: FakeFileReader,
          File: FakeFile,
          FormData: FakeFormData,
          setTimeout,
          clearTimeout,
          fetch: async (url, options = {}) => {
            fetchCalls.push({ url, options });
            if (url === "/api/rows") {
              return { ok: true, json: async () => ({ rows: [] }) };
            }
            if (url === "/api/extract") {
              return await new Promise((resolve) => {
                pendingExtractResponses.push(resolve);
              });
            }
            if (url === "/api/import-statement") {
              return await new Promise((resolve) => {
                pendingImportResponses.push(resolve);
              });
            }
            if (url === "/api/save") {
              return await new Promise((resolve) => {
                pendingSaveResponses.push(resolve);
              });
            }
            throw new Error(`Unexpected fetch: ${url}`);
          },
          document: {
            addEventListener(type, handler) {
              documentListeners[type] = handler;
            },
            getElementById(id) {
              return elements[id];
            },
            createElement(tag) {
              const element = makeElement(`created-${String(tag).toLowerCase()}`);
              element.tagName = String(tag).toUpperCase();
              element.colSpan = 0;
              return element;
            },
          },
        };
        sandbox.window = sandbox;
        sandbox.globalThis = sandbox;

        vm.runInNewContext(source, sandbox, { filename: "app.js" });

        const fileInputHandler = elements["file-input"].listeners.change;
        const extractHandler = elements["extract-button"].listeners.click;
        const pasteHandler = documentListeners.paste;

        function selectScreenshot(name) {
          fileInputHandler({
            target: {
              files: [
                {
                  name,
                  type: "image/png",
                },
              ],
            },
          });
        }

        function pasteImage(name) {
          const event = {
            defaultPrevented: false,
            preventDefault() {
              this.defaultPrevented = true;
            },
            clipboardData: {
              items: [
                {
                  type: "image/png",
                  getAsFile() {
                    return { name, type: "image/png" };
                  },
                },
              ],
            },
            target: elements["paste-zone"],
          };
          pasteHandler(event);
          return event;
        }

        function pasteTextIntoInput(target) {
          const event = {
            defaultPrevented: false,
            preventDefault() {
              this.defaultPrevented = true;
            },
            clipboardData: {
              items: [
                {
                  type: "text/plain",
                  getAsFile() {
                    return null;
                  },
                },
              ],
            },
            target,
          };
          pasteHandler(event);
          return event;
        }

        function selectStatement(name) {
          elements["statement-file-input"].listeners.change({
            target: {
              files: [
                {
                  name,
                  type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                },
              ],
            },
          });
        }

        function clickImportStatement() {
          elements["import-statement-button"].listeners.click();
        }

        function flush() {
          return new Promise((resolve) => setImmediate(resolve));
        }

        async function main() {
          selectScreenshot("first.png");
          assert.strictEqual(elements["preview-caption"].textContent, "first.png");
          assert.deepStrictEqual(elements["review-body"].children, []);
          assert.strictEqual(elements["save-button"].disabled, true);
          assert.strictEqual(fileReaderInstances.length, 1);

          selectStatement("wechat.xlsx");
          assert.strictEqual(elements["preview-caption"].textContent, "No screenshot selected yet.");
          assert.strictEqual(elements["preview-image"].hidden, true);
          assert.strictEqual(elements["extract-button"].disabled, true);
          assert.strictEqual(elements["import-statement-button"].disabled, false);
          assert.deepStrictEqual(elements["review-body"].children, []);
          assert.strictEqual(elements["save-button"].disabled, true);
          assert.strictEqual(elements["ocr-lines-panel"].hidden, true);
          assert.deepStrictEqual(elements["ocr-lines-list"].children, []);

          clickImportStatement();
          assert.strictEqual(elements["import-statement-button"].disabled, true);
          assert.strictEqual(fetchCalls.at(-1).url, "/api/import-statement");

          pendingImportResponses.shift()({
            ok: true,
            json: async () => ({
              rows: [
                {
                  date: "2026-03-29 18:44:00",
                  description: "叫了个炸鸡",
                  amount: "-26.50",
                  direction: "expense",
                  category: "",
                  member: "",
                  source: "wechat",
                  entry_type: "expense",
                  note: "",
                },
                {
                  date: "2026-03-29 18:41:00",
                  description: "商户_沈菊",
                  amount: "-10.00",
                  direction: "expense",
                  category: "",
                  member: "",
                  source: "wechat",
                  entry_type: "expense",
                  note: "",
                },
              ],
            }),
          });
          await flush();

          assert.deepStrictEqual(
            elements["review-header"].children.map((child) => child.textContent),
            ["Use", "Date", "Description", "Amount", "Direction", "Category", "Member", "Source", "Entry Type", "Note"]
          );
          assert.strictEqual(elements["review-body"].children.length, 2);
          assert.strictEqual(elements["review-body"].children[0].children[1].children[0].value, "2026-03-29 18:44:00");
          assert.strictEqual(elements["review-body"].children[0].children[2].children[0].value, "叫了个炸鸡");
          assert.strictEqual(elements["review-body"].children[0].children[3].children[0].value, "-26.50");
          assert.strictEqual(elements["review-body"].children[0].children[4].children[0].value, "expense");
          assert.strictEqual(elements["review-body"].children[0].children[5].children[0].value, "");
          assert.strictEqual(elements["review-body"].children[0].children[6].children[0].value, "");
          assert.strictEqual(elements["save-button"].disabled, false);
          assert.strictEqual(elements["import-statement-button"].disabled, false);
          assert.strictEqual(elements["status-message"].textContent, "Statement imported. Review the rows before saving.");

          elements["review-body"].children[0].children[5].children[0].value = "food";
          elements["review-body"].children[0].children[6].children[0].value = "Mike";
          elements["review-body"].children[0].children[7].children[0].value = "wechat-edited";
          elements["review-body"].children[0].children[8].children[0].value = "shared-expense";
          elements["review-body"].children[0].children[9].children[0].value = "team lunch";
          elements["review-body"].children[1].children[5].children[0].value = "food";
          elements["review-body"].children[1].children[6].children[0].value = "Mike";
          elements["review-body"].children[1].children[7].children[0].value = "wechat-edited";
          elements["review-body"].children[1].children[8].children[0].value = "shared-expense";
          elements["review-body"].children[1].children[9].children[0].value = "breakfast";

          elements["save-button"].listeners.click();
          const saveCall = fetchCalls.filter((call) => call.url === "/api/save").at(-1);
          assert.deepStrictEqual(JSON.parse(saveCall.options.body), {
            mode: "statement",
            rows: [
              {
                selected: true,
                transaction_time: "2026-03-29 18:44:00",
                counterparty: "叫了个炸鸡",
                direction: "expense",
                amount: "-26.50",
                category: "food",
                member: "Mike",
                source: "wechat-edited",
                entry_type: "shared-expense",
                note: "team lunch",
              },
              {
                selected: true,
                transaction_time: "2026-03-29 18:41:00",
                counterparty: "商户_沈菊",
                direction: "expense",
                amount: "-10.00",
                category: "food",
                member: "Mike",
                source: "wechat-edited",
                entry_type: "shared-expense",
                note: "breakfast",
              },
            ],
          });
          pendingSaveResponses.shift()({
            ok: true,
            json: async () => ({
              rows: [
                {
                  date: "2026-03-29 18:44:00",
                  description: "叫了个炸鸡",
                  amount: "-26.50",
                  direction: "expense",
                  category: "food",
                  member: "Mike",
                  source: "wechat",
                  entry_type: "expense",
                  note: "",
                },
                {
                  date: "2026-03-29 18:41:00",
                  description: "商户_沈菊",
                  amount: "-10.00",
                  direction: "expense",
                  category: "food",
                  member: "Mike",
                  source: "wechat",
                  entry_type: "expense",
                  note: "",
                },
              ],
            }),
          });
          await flush();
          assert.strictEqual(elements["status-message"].textContent, "Rows saved to Excel.");
          assert.strictEqual(elements["review-body"].children.length, 0);
          assert.strictEqual(elements["save-button"].disabled, true);
          assert.strictEqual(elements["records-body"].children.length, 2);
          assert.strictEqual(elements["records-body"].children[0].children[1].textContent, "叫了个炸鸡");
          assert.strictEqual(elements["records-body"].children[0].children[2].textContent, "-26.50");

          selectStatement("alipay.csv");
          clickImportStatement();
          pendingImportResponses.shift()({
            ok: false,
            json: async () => ({ error: "Statement import failed from API." }),
          });
          await flush();
          assert.strictEqual(elements["status-message"].textContent, "Statement import failed from API.");
          assert.strictEqual(elements["status-message"].style.color, "#9d2d22");
          assert.strictEqual(elements["save-button"].disabled, true);
          assert.deepStrictEqual(elements["review-body"].children, []);

          selectStatement("wechat-stale.xlsx");
          clickImportStatement();
          selectStatement("wechat-fresh.xlsx");
          clickImportStatement();

          const staleImport = pendingImportResponses.shift();
          const freshImport = pendingImportResponses.shift();
          staleImport({
            ok: true,
            json: async () => ({
              rows: [
                {
                  date: "2026-04-01 10:00:00",
                  description: "过期",
                  amount: "-1.00",
                  direction: "expense",
                  category: "",
                  member: "",
                  source: "wechat",
                  entry_type: "expense",
                  note: "",
                },
              ],
            }),
          });
          await flush();
          assert.strictEqual(elements["review-body"].children.length, 0);
          freshImport({
            ok: true,
            json: async () => ({
              rows: [
                {
                  date: "2026-04-03 18:40:31",
                  description: "淘宝闪购",
                  amount: "-25.40",
                  direction: "expense",
                  category: "",
                  member: "",
                  source: "wechat",
                  entry_type: "expense",
                  note: "",
                },
              ],
            }),
          });
          await flush();
          assert.strictEqual(elements["review-body"].children.length, 1);
          assert.strictEqual(elements["review-body"].children[0].children[2].children[0].value, "淘宝闪购");
          assert.strictEqual(elements["save-button"].disabled, false);
        }

        main().catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """
    )

    subprocess.run(["node", "-e", script], check=True, cwd=PROJECT_ROOT)


def test_frontend_shows_api_error_messages_for_extract_and_save():
    script = textwrap.dedent(
        """
        const fs = require("fs");
        const vm = require("vm");
        const path = require("path");
        const assert = require("assert");

        const source = fs.readFileSync(path.join(process.cwd(), "src/expense_record/static/app.js"), "utf8");

        function makeElement(id) {
          return {
            id,
            disabled: false,
            hidden: false,
            value: "",
            checked: false,
            textContent: "",
            innerHTML: "",
            className: "",
            type: "",
            src: "",
            style: {},
            listeners: {},
            children: [],
            addEventListener(type, handler) {
              this.listeners[type] = handler;
            },
            appendChild(child) {
              this.children.push(child);
            },
            removeChild(child) {
              const index = this.children.indexOf(child);
              if (index >= 0) {
                this.children.splice(index, 1);
              }
              return child;
            },
            replaceChildren(...children) {
              this.children = [...children];
            },
            removeAttribute(name) {
              if (name === "src") {
                this.src = "";
              }
            },
          };
        }

        const elements = {
          "file-input": makeElement("file-input"),
          "paste-zone": makeElement("paste-zone"),
          "preview-image": makeElement("preview-image"),
          "preview-caption": makeElement("preview-caption"),
          "statement-file-input": makeElement("statement-file-input"),
          "import-statement-button": makeElement("import-statement-button"),
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
          "extract-button": makeElement("extract-button"),
          "save-button": makeElement("save-button"),
          "status-message": makeElement("status-message"),
          "review-table": makeElement("review-table"),
          "review-header": makeElement("review-header"),
          "review-body": makeElement("review-body"),
          "records-body": makeElement("records-body"),
          "copy-all-button": makeElement("copy-all-button"),
          "clear-history-button": makeElement("clear-history-button"),
        };
        elements["preview-image"].hidden = true;

        const pendingExtractResponses = [];
        const pendingSaveResponses = [];
        let rejectNextExtract = false;

        const sandbox = {
          console,
          process,
          FileReader: class {
            readAsDataURL() {}
          },
          File: class {},
          FormData: class {
            append() {}
          },
          setTimeout,
          clearTimeout,
          fetch: async (url) => {
            if (url === "/api/rows") {
              return { ok: true, json: async () => ({ rows: [] }) };
            }
            if (url === "/api/extract") {
              if (rejectNextExtract) {
                rejectNextExtract = false;
                throw new Error("network down");
              }
              return await new Promise((resolve) => pendingExtractResponses.push(resolve));
            }
            if (url === "/api/save") {
              return await new Promise((resolve) => pendingSaveResponses.push(resolve));
            }
            throw new Error(`Unexpected fetch: ${url}`);
          },
          document: {
            addEventListener() {},
            getElementById(id) {
              return elements[id];
            },
            createElement(tag) {
              const element = makeElement(`created-${String(tag).toLowerCase()}`);
              element.tagName = String(tag).toUpperCase();
              element.colSpan = 0;
              return element;
            },
          },
        };
        sandbox.window = sandbox;
        sandbox.globalThis = sandbox;

        vm.runInNewContext(source, sandbox, { filename: "app.js" });

        function flush() {
          return new Promise((resolve) => setImmediate(resolve));
        }

            async function main() {
              elements["file-input"].listeners.change({
                target: { files: [{ name: "receipt.png", type: "image/png" }] },
              });

              elements["extract-button"].listeners.click();
              pendingExtractResponses.shift()({
                ok: false,
                json: async () => ({ error: "Extraction failed from API." }),
              });
              await flush();
              assert.strictEqual(elements["status-message"].textContent, "Extraction failed from API.");
              assert.strictEqual(elements["status-message"].style.color, "#9d2d22");
              assert.strictEqual(elements["extract-button"].disabled, false);
              assert.strictEqual(elements["ocr-lines-panel"].hidden, true);
              assert.deepStrictEqual(elements["ocr-lines-list"].children, []);

              elements["extract-button"].listeners.click();
              pendingExtractResponses.shift()({
                ok: true,
                json: async () => ({
                  rows: [{ date: "2026-03-30", merchant_item: "Shop", amount: "12.00" }],
                  lines: ["2026-03-30", "Shop", "12.00"],
                }),
              });
              await flush();

              const reviewRow = elements["review-body"].children[0];
              reviewRow.children[1].children[0].value = "2026-03-30";
              reviewRow.children[2].children[0].value = "Shop";
              reviewRow.children[3].children[0].value = "12.00";

              elements["save-button"].listeners.click();
              pendingSaveResponses.shift()({
                ok: false,
                json: async () => ({ error: "Save failed from API." }),
              });
              await flush();
              assert.strictEqual(elements["status-message"].textContent, "Save failed from API.");
              assert.strictEqual(elements["status-message"].style.color, "#9d2d22");
              assert.strictEqual(elements["save-button"].disabled, false);

              rejectNextExtract = true;
              elements["extract-button"].listeners.click();
              await flush();
              assert.strictEqual(elements["status-message"].textContent, "Extraction failed.");
              assert.strictEqual(elements["status-message"].style.color, "#9d2d22");
              assert.strictEqual(elements["ocr-lines-panel"].hidden, true);
              assert.deepStrictEqual(elements["ocr-lines-list"].children, []);
        }

        main().catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """
    )

    subprocess.run(["node", "-e", script], check=True, cwd=PROJECT_ROOT)


def test_frontend_copy_all_ignores_empty_saved_records_state():
    script = textwrap.dedent(
        """
        const fs = require("fs");
        const vm = require("vm");
        const path = require("path");
        const assert = require("assert");

        const source = fs.readFileSync(path.join(process.cwd(), "src/expense_record/static/app.js"), "utf8");

        function makeElement(id) {
          return {
            id,
            disabled: false,
            hidden: false,
            value: "",
            checked: false,
            textContent: "",
            innerHTML: "",
            className: "",
            type: "",
            src: "",
            style: {},
            listeners: {},
            children: [],
            addEventListener(type, handler) {
              this.listeners[type] = handler;
            },
            appendChild(child) {
              this.children.push(child);
            },
            removeChild(child) {
              const index = this.children.indexOf(child);
              if (index >= 0) {
                this.children.splice(index, 1);
              }
              return child;
            },
            replaceChildren(...children) {
              this.children = [...children];
            },
            removeAttribute(name) {
              if (name === "src") {
                this.src = "";
              }
            },
          };
        }

        const elements = {
          "file-input": makeElement("file-input"),
          "paste-zone": makeElement("paste-zone"),
          "preview-image": makeElement("preview-image"),
          "preview-caption": makeElement("preview-caption"),
          "statement-file-input": makeElement("statement-file-input"),
          "import-statement-button": makeElement("import-statement-button"),
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
          "extract-button": makeElement("extract-button"),
          "save-button": makeElement("save-button"),
          "status-message": makeElement("status-message"),
          "review-table": makeElement("review-table"),
          "review-header": makeElement("review-header"),
          "review-body": makeElement("review-body"),
          "records-body": makeElement("records-body"),
          "copy-all-button": makeElement("copy-all-button"),
          "clear-history-button": makeElement("clear-history-button"),
        };
        elements["preview-image"].hidden = true;

        const clipboardWrites = [];

        const sandbox = {
          console,
          process,
          FileReader: class {
            readAsDataURL() {}
          },
          File: class {},
          FormData: class {
            append() {}
          },
          setTimeout,
          clearTimeout,
          fetch: async (url) => {
            if (url === "/api/rows") {
              return { ok: true, json: async () => ({ rows: [] }) };
            }
            throw new Error(`Unexpected fetch: ${url}`);
          },
          navigator: {
            clipboard: {
              writeText: async (text) => {
                clipboardWrites.push(text);
              },
            },
          },
          document: {
            addEventListener() {},
            getElementById(id) {
              return elements[id];
            },
            createElement(tag) {
              const element = makeElement(`created-${String(tag).toLowerCase()}`);
              element.tagName = String(tag).toUpperCase();
              element.colSpan = 0;
              return element;
            },
          },
        };
        sandbox.window = sandbox;
        sandbox.globalThis = sandbox;

        vm.runInNewContext(source, sandbox, { filename: "app.js" });

        function flush() {
          return new Promise((resolve) => setImmediate(resolve));
        }

        async function main() {
          await flush();

          assert.strictEqual(elements["records-body"].children.length, 1);
          elements["copy-all-button"].listeners.click();
          await flush();

          assert.deepStrictEqual(clipboardWrites, []);
          assert.strictEqual(elements["status-message"].textContent, "No records to copy.");
          assert.strictEqual(elements["status-message"].style.color, "#9d2d22");
        }

        main().catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """
    )

    subprocess.run(["node", "-e", script], check=True, cwd=PROJECT_ROOT)


def test_frontend_prevents_saving_imported_row_without_category_or_member():
    script = textwrap.dedent(
        """
        const fs = require("fs");
        const vm = require("vm");
        const path = require("path");
        const assert = require("assert");

        const source = fs.readFileSync(path.join(process.cwd(), "src/expense_record/static/app.js"), "utf8");

        function makeElement(id) {
          return {
            id,
            disabled: false,
            hidden: false,
            value: "",
            checked: false,
            textContent: "",
            innerHTML: "",
            className: "",
            type: "",
            src: "",
            style: {},
            files: [],
            listeners: {},
            children: [],
            addEventListener(type, handler) {
              this.listeners[type] = handler;
            },
            appendChild(child) {
              this.children.push(child);
            },
            removeChild(child) {
              const index = this.children.indexOf(child);
              if (index >= 0) {
                this.children.splice(index, 1);
              }
              return child;
            },
            replaceChildren(...children) {
              this.children = [...children];
            },
            removeAttribute(name) {
              if (name === "src") {
                this.src = "";
              }
            },
          };
        }

        const elements = {
          "file-input": makeElement("file-input"),
          "paste-zone": makeElement("paste-zone"),
          "preview-image": makeElement("preview-image"),
          "preview-caption": makeElement("preview-caption"),
          "statement-file-input": makeElement("statement-file-input"),
          "import-statement-button": makeElement("import-statement-button"),
          "extract-button": makeElement("extract-button"),
          "save-button": makeElement("save-button"),
          "status-message": makeElement("status-message"),
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
          "review-table": makeElement("review-table"),
          "review-header": makeElement("review-header"),
          "review-body": makeElement("review-body"),
          "records-body": makeElement("records-body"),
          "copy-all-button": makeElement("copy-all-button"),
          "clear-history-button": makeElement("clear-history-button"),
        };
        elements["preview-image"].hidden = true;
        const documentListeners = {};
        const pendingImportResponses = [];
        const fetchCalls = [];

        const sandbox = {
          console,
          process,
          FileReader: class {},
          File: class {},
          FormData: class {
            append() {}
          },
          setTimeout,
          clearTimeout,
          fetch: async (url, options = {}) => {
            fetchCalls.push({ url, options });
            if (url === "/api/rows") {
              return { ok: true, json: async () => ({ rows: [] }) };
            }
            if (url === "/api/import-statement") {
              return await new Promise((resolve) => pendingImportResponses.push(resolve));
            }
            if (url === "/api/save") {
              throw new Error("save should not be called");
            }
            throw new Error(`Unexpected fetch: ${url}`);
          },
          document: {
            addEventListener(type, handler) {
              documentListeners[type] = handler;
            },
            getElementById(id) {
              return elements[id];
            },
            createElement(tag) {
              const element = makeElement(`created-${String(tag).toLowerCase()}`);
              element.tagName = String(tag).toUpperCase();
              element.colSpan = 0;
              return element;
            },
          },
        };
        sandbox.window = sandbox;
        sandbox.globalThis = sandbox;

        vm.runInNewContext(source, sandbox, { filename: "app.js" });

        function flush() {
          return new Promise((resolve) => setImmediate(resolve));
        }

        async function main() {
          elements["statement-file-input"].listeners.change({
            target: {
              files: [{ name: "wechat.xlsx", type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }],
            },
          });

          elements["import-statement-button"].listeners.click();
          pendingImportResponses.shift()({
            ok: true,
            json: async () => ({
              rows: [
                {
                  date: "2026-04-10 10:00:00",
                  description: "Lunch",
                  amount: "-26.50",
                  direction: "expense",
                  category: "",
                  member: "",
                  source: "wechat",
                  entry_type: "expense",
                  note: "",
                },
              ],
            }),
          });
          await flush();

          elements["save-button"].listeners.click();
          await flush();

          assert.strictEqual(elements["status-message"].textContent, "Category and member are required.");
          assert.strictEqual(fetchCalls.filter((call) => call.url === "/api/save").length, 0);
        }

        main().catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """
    )

    subprocess.run(["node", "-e", script], check=True, cwd=PROJECT_ROOT)


def test_frontend_manual_entry_posts_valid_payload():
    script = textwrap.dedent(
        """
        const fs = require("fs");
        const vm = require("vm");
        const path = require("path");
        const assert = require("assert");

        const source = fs.readFileSync(path.join(process.cwd(), "src/expense_record/static/app.js"), "utf8");

        function makeElement(id) {
          return {
            id,
            disabled: false,
            hidden: false,
            value: "",
            checked: false,
            textContent: "",
            innerHTML: "",
            className: "",
            type: "",
            src: "",
            style: {},
            files: [],
            listeners: {},
            children: [],
            dataset: {},
            addEventListener(type, handler) {
              this.listeners[type] = handler;
            },
            appendChild(child) {
              this.children.push(child);
            },
            removeChild(child) {
              const index = this.children.indexOf(child);
              if (index >= 0) {
                this.children.splice(index, 1);
              }
              return child;
            },
            replaceChildren(...children) {
              this.children = [...children];
            },
            removeAttribute(name) {
              if (name === "src") {
                this.src = "";
              }
            },
          };
        }

        const elements = {
          "file-input": makeElement("file-input"),
          "paste-zone": makeElement("paste-zone"),
          "preview-image": makeElement("preview-image"),
          "preview-caption": makeElement("preview-caption"),
          "statement-file-input": makeElement("statement-file-input"),
          "import-statement-button": makeElement("import-statement-button"),
          "extract-button": makeElement("extract-button"),
          "save-button": makeElement("save-button"),
          "status-message": makeElement("status-message"),
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
          "review-table": makeElement("review-table"),
          "review-header": makeElement("review-header"),
          "review-body": makeElement("review-body"),
          "records-body": makeElement("records-body"),
          "copy-all-button": makeElement("copy-all-button"),
          "clear-history-button": makeElement("clear-history-button"),
          "manual-entry-date": makeElement("manual-entry-date"),
          "manual-entry-description": makeElement("manual-entry-description"),
          "manual-entry-direction": makeElement("manual-entry-direction"),
          "manual-entry-amount": makeElement("manual-entry-amount"),
          "manual-entry-category": makeElement("manual-entry-category"),
          "manual-entry-member": makeElement("manual-entry-member"),
          "manual-entry-entry-type": makeElement("manual-entry-entry-type"),
          "manual-entry-note": makeElement("manual-entry-note"),
          "manual-entry-button": makeElement("manual-entry-button"),
          "category-options": makeElement("category-options"),
          "member-options": makeElement("member-options"),
          "dashboard-expense-category": makeElement("dashboard-expense-category"),
          "dashboard-member-category": makeElement("dashboard-member-category"),
          "dashboard-cash-flow": makeElement("dashboard-cash-flow"),
          "dashboard-assets": makeElement("dashboard-assets"),
        };
        elements["preview-image"].hidden = true;
        const fetchCalls = [];

        const sandbox = {
          console,
          process,
          FileReader: class {},
          File: class {},
          FormData: class {
            append() {}
          },
          setTimeout,
          clearTimeout,
          fetch: async (url, options = {}) => {
            fetchCalls.push({ url, options });
            if (url === "/api/rows") {
              return { ok: true, json: async () => ({ rows: [] }) };
            }
            if (url === "/api/categories") {
              return { ok: true, json: async () => ({ categories: ["food", "rent"] }) };
            }
            if (url === "/api/members") {
              return { ok: true, json: async () => ({ members: ["Mike", "Family"] }) };
            }
            if (url === "/api/dashboard") {
              return {
                ok: true,
                json: async () => ({
                  expense_by_category: [],
                  expense_by_member_category: [],
                  cash_flow: [],
                  asset_trend: [],
                }),
              };
            }
            if (url === "/api/manual-entry") {
              return {
                ok: true,
                json: async () => ({
                  row: {
                    date: "2026-04-11",
                    description: "Lunch",
                    direction: "expense",
                    amount: "-26.50",
                    category: "food",
                    member: "Mike",
                    source: "manual",
                    entry_type: "expense",
                    note: "weekday lunch",
                  },
                }),
              };
            }
            throw new Error(`Unexpected fetch: ${url}`);
          },
          document: {
            addEventListener() {},
            getElementById(id) {
              return elements[id];
            },
            createElement(tag) {
              const element = makeElement(`created-${String(tag).toLowerCase()}`);
              element.tagName = String(tag).toUpperCase();
              element.colSpan = 0;
              return element;
            },
          },
        };
        sandbox.window = sandbox;
        sandbox.globalThis = sandbox;

        vm.runInNewContext(source, sandbox, { filename: "app.js" });

        function flush() {
          return new Promise((resolve) => setImmediate(resolve));
        }

        async function main() {
          await flush();

          elements["manual-entry-date"].value = "2026-04-11";
          elements["manual-entry-description"].value = "Lunch";
          elements["manual-entry-direction"].value = "expense";
          elements["manual-entry-amount"].value = "26.50";
          elements["manual-entry-category"].value = "food";
          elements["manual-entry-member"].value = "Mike";
          elements["manual-entry-entry-type"].value = "expense";
          elements["manual-entry-note"].value = "weekday lunch";

          elements["manual-entry-button"].listeners.click();
          await flush();

          const call = fetchCalls.find((entry) => entry.url === "/api/manual-entry");
          assert.ok(call);
          assert.deepStrictEqual(JSON.parse(call.options.body), {
            date: "2026-04-11",
            description: "Lunch",
            direction: "expense",
            amount: "26.50",
            category: "food",
            member: "Mike",
            entry_type: "expense",
            note: "weekday lunch",
          });
          assert.strictEqual(elements["status-message"].textContent, "Manual entry saved.");
        }

        main().catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """
    )

    subprocess.run(["node", "-e", script], check=True, cwd=PROJECT_ROOT)


def test_frontend_asset_snapshot_posts_valid_payload():
    script = textwrap.dedent(
        """
        const fs = require("fs");
        const vm = require("vm");
        const path = require("path");
        const assert = require("assert");

        const source = fs.readFileSync(path.join(process.cwd(), "src/expense_record/static/app.js"), "utf8");

        function makeElement(id) {
          return {
            id,
            disabled: false,
            hidden: false,
            value: "",
            checked: false,
            textContent: "",
            innerHTML: "",
            className: "",
            type: "",
            src: "",
            style: {},
            files: [],
            listeners: {},
            children: [],
            dataset: {},
            addEventListener(type, handler) {
              this.listeners[type] = handler;
            },
            appendChild(child) {
              this.children.push(child);
            },
            removeChild(child) {
              const index = this.children.indexOf(child);
              if (index >= 0) {
                this.children.splice(index, 1);
              }
              return child;
            },
            replaceChildren(...children) {
              this.children = [...children];
            },
            removeAttribute(name) {
              if (name === "src") {
                this.src = "";
              }
            },
          };
        }

        const elements = {
          "file-input": makeElement("file-input"),
          "paste-zone": makeElement("paste-zone"),
          "preview-image": makeElement("preview-image"),
          "preview-caption": makeElement("preview-caption"),
          "statement-file-input": makeElement("statement-file-input"),
          "import-statement-button": makeElement("import-statement-button"),
          "extract-button": makeElement("extract-button"),
          "save-button": makeElement("save-button"),
          "status-message": makeElement("status-message"),
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
          "review-table": makeElement("review-table"),
          "review-header": makeElement("review-header"),
          "review-body": makeElement("review-body"),
          "records-body": makeElement("records-body"),
          "copy-all-button": makeElement("copy-all-button"),
          "clear-history-button": makeElement("clear-history-button"),
          "asset-snapshot-date": makeElement("asset-snapshot-date"),
          "asset-snapshot-cash": makeElement("asset-snapshot-cash"),
          "asset-snapshot-stock": makeElement("asset-snapshot-stock"),
          "asset-snapshot-note": makeElement("asset-snapshot-note"),
          "asset-snapshot-button": makeElement("asset-snapshot-button"),
          "category-options": makeElement("category-options"),
          "member-options": makeElement("member-options"),
          "dashboard-expense-category": makeElement("dashboard-expense-category"),
          "dashboard-member-category": makeElement("dashboard-member-category"),
          "dashboard-cash-flow": makeElement("dashboard-cash-flow"),
          "dashboard-assets": makeElement("dashboard-assets"),
        };
        elements["preview-image"].hidden = true;
        const fetchCalls = [];

        const sandbox = {
          console,
          process,
          FileReader: class {},
          File: class {},
          FormData: class {
            append() {}
          },
          setTimeout,
          clearTimeout,
          fetch: async (url, options = {}) => {
            fetchCalls.push({ url, options });
            if (url === "/api/rows") {
              return { ok: true, json: async () => ({ rows: [] }) };
            }
            if (url === "/api/categories") {
              return { ok: true, json: async () => ({ categories: [] }) };
            }
            if (url === "/api/members") {
              return { ok: true, json: async () => ({ members: [] }) };
            }
            if (url === "/api/dashboard") {
              return {
                ok: true,
                json: async () => ({
                  expense_by_category: [],
                  expense_by_member_category: [],
                  cash_flow: [],
                  asset_trend: [],
                }),
              };
            }
            if (url === "/api/asset-snapshots") {
              return {
                ok: true,
                json: async () => ({
                  snapshot: {
                    date: "2026-04-11",
                    cash_or_balance_total: "8000.00",
                    stock_total_value: "12000.00",
                    note: "month end",
                  },
                }),
              };
            }
            throw new Error(`Unexpected fetch: ${url}`);
          },
          document: {
            addEventListener() {},
            getElementById(id) {
              return elements[id];
            },
            createElement(tag) {
              const element = makeElement(`created-${String(tag).toLowerCase()}`);
              element.tagName = String(tag).toUpperCase();
              element.colSpan = 0;
              return element;
            },
          },
        };
        sandbox.window = sandbox;
        sandbox.globalThis = sandbox;

        vm.runInNewContext(source, sandbox, { filename: "app.js" });

        function flush() {
          return new Promise((resolve) => setImmediate(resolve));
        }

        async function main() {
          await flush();

          elements["asset-snapshot-date"].value = "2026-04-11";
          elements["asset-snapshot-cash"].value = "8000";
          elements["asset-snapshot-stock"].value = "12000";
          elements["asset-snapshot-note"].value = "month end";

          elements["asset-snapshot-button"].listeners.click();
          await flush();

          const call = fetchCalls.find((entry) => entry.url === "/api/asset-snapshots");
          assert.ok(call);
          assert.deepStrictEqual(JSON.parse(call.options.body), {
            date: "2026-04-11",
            cash_or_balance_total: "8000",
            stock_total_value: "12000",
            note: "month end",
          });
          assert.strictEqual(elements["status-message"].textContent, "Asset snapshot saved.");
        }

        main().catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """
    )

    subprocess.run(["node", "-e", script], check=True, cwd=PROJECT_ROOT)


def test_frontend_dashboard_loads_reference_data_and_renders_summary():
    script = textwrap.dedent(
        """
        const fs = require("fs");
        const vm = require("vm");
        const path = require("path");
        const assert = require("assert");

        const source = fs.readFileSync(path.join(process.cwd(), "src/expense_record/static/app.js"), "utf8");

        function makeElement(id) {
          return {
            id,
            disabled: false,
            hidden: false,
            value: "",
            checked: false,
            textContent: "",
            innerHTML: "",
            className: "",
            type: "",
            src: "",
            style: {},
            files: [],
            listeners: {},
            children: [],
            dataset: {},
            addEventListener(type, handler) {
              this.listeners[type] = handler;
            },
            appendChild(child) {
              this.children.push(child);
            },
            removeChild(child) {
              const index = this.children.indexOf(child);
              if (index >= 0) {
                this.children.splice(index, 1);
              }
              return child;
            },
            replaceChildren(...children) {
              this.children = [...children];
            },
            removeAttribute(name) {
              if (name === "src") {
                this.src = "";
              }
            },
          };
        }

        const elements = {
          "file-input": makeElement("file-input"),
          "paste-zone": makeElement("paste-zone"),
          "preview-image": makeElement("preview-image"),
          "preview-caption": makeElement("preview-caption"),
          "statement-file-input": makeElement("statement-file-input"),
          "import-statement-button": makeElement("import-statement-button"),
          "extract-button": makeElement("extract-button"),
          "save-button": makeElement("save-button"),
          "status-message": makeElement("status-message"),
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
          "review-table": makeElement("review-table"),
          "review-header": makeElement("review-header"),
          "review-body": makeElement("review-body"),
          "records-body": makeElement("records-body"),
          "copy-all-button": makeElement("copy-all-button"),
          "clear-history-button": makeElement("clear-history-button"),
          "manual-entry-category": makeElement("manual-entry-category"),
          "manual-entry-member": makeElement("manual-entry-member"),
          "category-options": makeElement("category-options"),
          "member-options": makeElement("member-options"),
          "dashboard-expense-category": makeElement("dashboard-expense-category"),
          "dashboard-member-category": makeElement("dashboard-member-category"),
          "dashboard-cash-flow": makeElement("dashboard-cash-flow"),
          "dashboard-assets": makeElement("dashboard-assets"),
        };
        elements["preview-image"].hidden = true;

        const sandbox = {
          console,
          process,
          FileReader: class {},
          File: class {},
          FormData: class {
            append() {}
          },
          setTimeout,
          clearTimeout,
          fetch: async (url) => {
            if (url === "/api/rows") {
              return { ok: true, json: async () => ({ rows: [] }) };
            }
            if (url === "/api/categories") {
              return { ok: true, json: async () => ({ categories: ["food", "rent"] }) };
            }
            if (url === "/api/members") {
              return { ok: true, json: async () => ({ members: ["Mike", "Jane"] }) };
            }
            if (url === "/api/dashboard") {
              return {
                ok: true,
                json: async () => ({
                  expense_by_category: [{ category: "food", amount: "120.00" }],
                  expense_by_member_category: [{ member: "Mike", category: "food", amount: "80.00" }],
                  cash_flow: [{ month: "2026-04", income_total: "10000.00", expense_total: "4200.00", net_total: "5800.00" }],
                  asset_trend: [{ month: "2026-04", cash_or_balance_total: "8000.00", stock_total_value: "12000.00", total_assets: "20000.00" }],
                }),
              };
            }
            throw new Error(`Unexpected fetch: ${url}`);
          },
          document: {
            addEventListener() {},
            getElementById(id) {
              return elements[id];
            },
            createElement(tag) {
              const element = makeElement(`created-${String(tag).toLowerCase()}`);
              element.tagName = String(tag).toUpperCase();
              element.colSpan = 0;
              return element;
            },
          },
        };
        sandbox.window = sandbox;
        sandbox.globalThis = sandbox;

        vm.runInNewContext(source, sandbox, { filename: "app.js" });

        function flush() {
          return new Promise((resolve) => setImmediate(resolve));
        }

        async function main() {
          await flush();
          await flush();

          assert.strictEqual(elements["manual-entry-category"].children.length, 3);
          assert.strictEqual(elements["manual-entry-member"].children.length, 3);
          assert.ok(elements["dashboard-expense-category"].children[0].textContent.includes("food"));
          assert.ok(elements["dashboard-member-category"].children[0].textContent.includes("Mike"));
          assert.ok(elements["dashboard-cash-flow"].children[0].textContent.includes("5800.00"));
          assert.ok(elements["dashboard-assets"].children[0].textContent.includes("20000.00"));
        }

        main().catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """
    )

    subprocess.run(["node", "-e", script], check=True, cwd=PROJECT_ROOT)


def test_imported_wechat_rows_can_be_saved(client):
    response = client.post(
        "/api/import-statement",
        data={"statement_file": (io.BytesIO(_wechat_fixture_bytes()), "wechat.xlsx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    rows = response.get_json()["rows"]
    rows = [
        {
            "selected": True,
            "transaction_time": rows[0]["date"],
            "counterparty": rows[0]["description"],
            "direction": rows[0]["direction"],
            "amount": rows[0]["amount"],
            "category": "food",
            "member": "Mike",
        }
    ]

    save_response = client.post("/api/save", json={"mode": "statement", "rows": rows})

    assert save_response.status_code == 200
    assert any("叫了个炸鸡" in row["description"] for row in save_response.get_json()["rows"])


def test_imported_alipay_statement_rows_can_be_saved(client):
    response = client.post(
        "/api/import-statement",
        data={"statement_file": (io.BytesIO(_alipay_fixture_bytes()), "alipay.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    rows = response.get_json()["rows"]
    rows = [
        {
            "selected": True,
            "transaction_time": rows[0]["date"],
            "counterparty": rows[0]["description"],
            "direction": rows[0]["direction"],
            "amount": rows[0]["amount"],
            "category": "food",
            "member": "Mike",
        }
    ]

    save_response = client.post("/api/save", json={"mode": "statement", "rows": rows})

    assert save_response.status_code == 200
    assert any("淘宝闪购" in row["description"] for row in save_response.get_json()["rows"])


def _distribution_index(site_packages: Path) -> dict[str, metadata.Distribution]:
    return {
        canonicalize_name(dist.metadata["Name"]): dist
        for dist in metadata.distributions(path=[str(site_packages)])
        if dist.metadata.get("Name")
    }


def _dependency_closure(root_names: list[str], site_packages: Path) -> list[metadata.Distribution]:
    distributions = _distribution_index(site_packages)
    required: dict[str, metadata.Distribution] = {}
    pending = [canonicalize_name(name) for name in root_names]

    while pending:
        name = pending.pop()
        if name in required:
            continue
        dist = distributions[name]
        required[name] = dist
        for requirement_text in dist.requires or []:
            requirement = Requirement(requirement_text)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            pending.append(canonicalize_name(requirement.name))

    return list(required.values())


def _copy_distribution(dist: metadata.Distribution, destination: Path) -> None:
    for file in dist.files or []:
        source = dist.locate_file(file)
        target = destination / file
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)


def test_index_page_loads_from_installed_package(tmp_path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-build-isolation",
            "--no-deps",
            "-w",
            str(wheelhouse),
            ".",
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )

    wheel_path = next(wheelhouse.glob("*.whl"))

    with zipfile.ZipFile(wheel_path) as wheel_file:
        metadata_name = next(name for name in wheel_file.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = wheel_file.read(metadata_name).decode()
        assert any(name.endswith("static/nested/fixture.txt") for name in wheel_file.namelist())

    assert "Requires-Dist: Flask>=3.0" in metadata
    assert "Requires-Dist: openpyxl>=3.1" in metadata
    assert "Requires-Dist: rapidocr-onnxruntime>=1.4" in metadata

    venv_dir = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, cwd=PROJECT_ROOT)

    venv_python = venv_dir / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python"
    )

    venv_site_packages = Path(
        subprocess.check_output(
            [
                str(venv_python),
                "-c",
                "import sysconfig; print(sysconfig.get_paths()['purelib'])",
            ],
            text=True,
        ).strip()
    )
    current_site_packages = Path(sysconfig.get_paths()["purelib"])

    for distribution in _dependency_closure(["Flask"], current_site_packages):
        _copy_distribution(distribution, venv_site_packages)

    subprocess.run([str(venv_python), "-m", "pip", "install", "--no-deps", str(wheel_path)], check=True, cwd=PROJECT_ROOT)

    script = textwrap.dedent(
        """
        from pathlib import Path
        import sysconfig

        from expense_record import __file__ as package_file
        from expense_record.app import create_app

        package_path = Path(package_file).resolve()
        install_dir = Path(sysconfig.get_paths()["purelib"]).resolve()
        assert package_path.is_relative_to(install_dir)
        assert (install_dir / "expense_record" / "templates" / "index.html").exists()
        assert (install_dir / "expense_record" / "static" / "app.css").exists()
        assert (install_dir / "expense_record" / "static" / "app.js").exists()
        assert (install_dir / "expense_record" / "static" / "nested" / "fixture.txt").exists()

        app = create_app({"TESTING": True})
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        assert b"Family Finance Tool" in response.data
        assert client.get("/static/app.css").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        """
    )

    subprocess.run([str(venv_python), "-c", script], check=True, cwd=PROJECT_ROOT)


def test_extract_endpoint_parses_uploaded_image(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    monkeypatch.setattr(
        "expense_record.api.run_ocr_lines",
        lambda image_bytes: ["微信支付", "2026-03-30 18:21", "瑞幸咖啡", "￥23.50"],
    )

    response = client.post(
        "/api/extract",
        data={"image": (io.BytesIO(b"fake image bytes"), "receipt.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "rows": [{"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50", "direction": ""}],
        "lines": ["微信支付", "2026-03-30 18:21", "瑞幸咖啡", "￥23.50"],
    }


def test_extract_endpoint_returns_multiple_rows(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    monkeypatch.setattr(
        "expense_record.api.run_ocr_lines",
        lambda _image_bytes: [
            "滴滴出行",
            "3月28日11:44",
            "-28.00",
            "扫二维码付款-给早餐",
            "3月29日08:42",
            "-5.00",
        ],
    )

    response = client.post(
        "/api/extract",
        data={"image": (io.BytesIO(b"fake image bytes"), "screen.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "rows": [
            {"date": "03-28", "merchant_item": "滴滴出行", "amount": "28.00", "direction": ""},
            {"date": "03-29", "merchant_item": "扫二维码付款-给早餐", "amount": "5.00", "direction": ""},
        ],
        "lines": [
            "滴滴出行",
            "3月28日11:44",
            "-28.00",
            "扫二维码付款-给早餐",
            "3月29日08:42",
            "-5.00",
        ],
    }


def test_extract_endpoint_keeps_date_only_row_for_manual_completion(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    monkeypatch.setattr(
        "expense_record.api.run_ocr_lines",
        lambda _image_bytes: ["3月29日08:42"],
    )

    response = client.post(
        "/api/extract",
        data={"image": (io.BytesIO(b"fake image bytes"), "screen.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "rows": [{"date": "03-29", "merchant_item": "", "amount": "", "direction": ""}],
        "lines": ["3月29日08:42"],
        "warning": "OCR returned incomplete fields.",
    }


def test_extract_endpoint_rejects_missing_image(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post("/api/extract", data={}, content_type="multipart/form-data")

    assert response.status_code == 400
    assert response.get_json() == {"error": "No image provided."}


def test_extract_endpoint_returns_warning_when_ocr_has_no_usable_fields(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    monkeypatch.setattr(
        "expense_record.api.run_ocr_lines",
        lambda _image_bytes: ["微信支付", "订单已完成"],
    )

    response = client.post(
        "/api/extract",
        data={"image": (io.BytesIO(b"fake image bytes"), "receipt.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "rows": [],
        "lines": ["微信支付", "订单已完成"],
        "warning": "OCR returned no usable fields.",
    }


def test_save_endpoint_rejects_completely_blank_rows_after_empty_ocr_warning(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    monkeypatch.setattr(
        "expense_record.api.run_ocr_lines",
        lambda _image_bytes: ["微信支付", "订单已完成"],
    )

    extract_response = client.post(
        "/api/extract",
        data={"image": (io.BytesIO(b"fake image bytes"), "receipt.png")},
        content_type="multipart/form-data",
    )
    assert extract_response.status_code == 200
    assert extract_response.get_json()["warning"] == "OCR returned no usable fields."

    save_response = client.post(
        "/api/save",
        json={
            "rows": [
                {"date": "", "merchant_item": "", "amount": "", "selected": True},
            ]
        },
    )

    assert save_response.status_code == 400
    assert save_response.get_json() == {"error": "At least one selected row is required."}


def test_extract_endpoint_returns_json_for_ocr_failures(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    def raise_ocr(_image_bytes: bytes) -> list[str]:
        raise RuntimeError("ocr failed")

    monkeypatch.setattr("expense_record.api.run_ocr_lines", raise_ocr)

    response = client.post(
        "/api/extract",
        data={"image": (io.BytesIO(b"fake image bytes"), "receipt.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "OCR extraction failed."}


def test_import_statement_returns_normalized_rows(client):
    response = client.post(
        "/api/import-statement",
        data={"statement_file": (io.BytesIO(_wechat_fixture_bytes()), "wechat.xlsx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {
            "date": "2026-03-29 18:44:00",
            "description": "叫了个炸鸡",
            "amount": "-26.50",
            "direction": "expense",
            "category": "",
            "member": "",
            "source": "wechat",
            "entry_type": "expense",
            "note": "",
        }
    ]


def test_import_statement_rejects_unsupported_files(client):
    response = client.post(
        "/api/import-statement",
        data={"statement_file": (io.BytesIO(b"bad"), "bad.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Unsupported or ambiguous statement file."


def test_save_endpoint_persists_selected_rows(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={
            "rows": [
                {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50", "selected": True},
            ]
        },
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50", "direction": ""}
    ]


def test_save_endpoint_appends_only_checked_rows(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
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
        {"date": "03-28", "merchant_item": "滴滴出行", "amount": "28.00", "direction": ""}
    ]


def test_save_endpoint_rejects_when_no_rows_are_selected(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={
            "rows": [
                {"date": "03-28", "merchant_item": "滴滴出行", "amount": "28.00", "selected": False},
            ]
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "At least one selected row is required."}


def test_save_endpoint_allows_blank_manual_corrections(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={
            "rows": [
                {"date": "", "merchant_item": "手动补录", "amount": "", "selected": True},
            ]
        },
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {"date": "", "merchant_item": "手动补录", "amount": "", "direction": ""}
    ]


def test_statement_save_normalizes_expense_to_negative_and_income_to_positive(client):
    response = client.post(
        "/api/save",
        json={
            "mode": "statement",
            "rows": [
                {
                    "selected": True,
                    "transaction_time": "2026-04-10 10:00:00",
                    "counterparty": "Salary",
                    "direction": "收入",
                    "amount": "5000.00",
                    "category": "salary",
                    "member": "Mike",
                },
                {
                    "selected": True,
                    "transaction_time": "2026-04-10 12:00:00",
                    "counterparty": "Lunch",
                    "direction": "支出",
                    "amount": "26.50",
                    "category": "food",
                    "member": "Mike",
                },
            ],
        },
    )

    assert response.status_code == 200
    rows = response.get_json()["rows"]
    assert rows[0]["amount"].startswith("+")
    assert rows[1]["amount"].startswith("-")


def test_save_endpoint_persists_selected_statement_rows(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")

    response = client.post(
        "/api/save",
        json={
            "mode": "statement",
            "rows": [
                {
                    "transaction_time": "2026-03-29 18:44:00",
                    "counterparty": "叫了个炸鸡",
                    "direction": "支出",
                    "amount": "26.50",
                    "category": "food",
                    "member": "Mike",
                    "selected": True,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {
            "date": "2026-03-29 18:44:00",
            "description": "叫了个炸鸡",
            "amount": "-26.50",
            "direction": "expense",
            "category": "food",
            "member": "Mike",
            "source": "",
            "entry_type": "expense",
            "note": "",
        }
    ]
    assert [row.to_dict() for row in storage.list_ledger_entries()] == response.get_json()["rows"]


@pytest.mark.parametrize(
    ("row_payload", "description"),
    [
        (
            {
                "transaction_time": ["2026-03-29 18:44:00"],
                "counterparty": "叫了个炸鸡",
                "direction": "支出",
                "amount": "26.50",
                "category": "food",
                "member": "Mike",
                "selected": True,
            },
            "non-string transaction_time",
        ),
        (
            {
                "transaction_time": "2026-03-29 18:44:00",
                "counterparty": {"name": "叫了个炸鸡"},
                "direction": "支出",
                "amount": "26.50",
                "category": "food",
                "member": "Mike",
                "selected": True,
            },
            "non-string counterparty",
        ),
        (
            {
                "transaction_time": "2026-03-29 18:44:00",
                "counterparty": "叫了个炸鸡",
                "direction": "支出",
                "category": "food",
                "member": "Mike",
                "selected": True,
            },
            "missing amount",
        ),
    ],
)
def test_save_endpoint_rejects_malformed_statement_rows(tmp_path, row_payload, description):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={"mode": "statement", "rows": [row_payload]},
    )

    assert response.status_code == 400, description
    assert response.get_json() == {"error": "Invalid save payload."}


def test_save_endpoint_rejects_whitespace_only_statement_rows(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={
            "mode": "statement",
            "rows": [
                {
                    "transaction_time": "   ",
                    "counterparty": " \t ",
                    "direction": "\n",
                    "amount": "   ",
                    "category": " \t",
                    "member": "\n",
                    "selected": True,
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid save payload."}


def test_statement_save_require_member(client):
    response = client.post(
        "/api/save",
        json={
            "mode": "statement",
            "rows": [
                {
                    "selected": True,
                    "transaction_time": "2026-04-10 12:00:00",
                    "counterparty": "Lunch",
                    "direction": "支出",
                    "amount": "26.50",
                    "category": "food",
                    "member": "",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid save payload."}


def test_statement_save_require_category(client):
    response = client.post(
        "/api/save",
        json={
            "mode": "statement",
            "rows": [
                {
                    "selected": True,
                    "transaction_time": "2026-04-10 12:00:00",
                    "counterparty": "Lunch",
                    "direction": "支出",
                    "amount": "26.50",
                    "category": "",
                    "member": "Mike",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid save payload."}


def test_statement_save_rejects_invalid_direction(client):
    response = client.post(
        "/api/save",
        json={
            "mode": "statement",
            "rows": [
                {
                    "selected": True,
                    "transaction_time": "2026-04-10 12:00:00",
                    "counterparty": "Lunch",
                    "direction": "refund",
                    "amount": "26.50",
                    "category": "food",
                    "member": "Mike",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid save payload."}


def test_statement_save_drops_rows_below_one(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")

    response = client.post(
        "/api/save",
        json={
            "mode": "statement",
            "rows": [
                {
                    "selected": True,
                    "transaction_time": "2026-04-10 12:00:00",
                    "counterparty": "Interest",
                    "direction": "收入",
                    "amount": "0.99",
                    "category": "interest",
                    "member": "Mike",
                },
                {
                    "selected": True,
                    "transaction_time": "2026-04-10 12:01:00",
                    "counterparty": "Coffee",
                    "direction": "支出",
                    "amount": "12.50",
                    "category": "food",
                    "member": "Mike",
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {
            "date": "2026-04-10 12:01:00",
            "description": "Coffee",
            "amount": "-12.50",
            "direction": "expense",
            "category": "food",
            "member": "Mike",
            "source": "",
            "entry_type": "expense",
            "note": "",
        }
    ]
    assert [row.to_dict() for row in storage.list_ledger_entries()] == response.get_json()["rows"]


def test_statement_save_persists_visible_source_entry_type_and_note(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")

    response = client.post(
        "/api/save",
        json={
            "mode": "statement",
            "rows": [
                {
                    "selected": True,
                    "transaction_time": "2026-04-10 12:01:00",
                    "counterparty": "Coffee",
                    "direction": "expense",
                    "amount": "-12.50",
                    "category": "food",
                    "member": "Mike",
                    "source": "wechat-edited",
                    "entry_type": "shared-expense",
                    "note": "office run",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {
            "date": "2026-04-10 12:01:00",
            "description": "Coffee",
            "amount": "-12.50",
            "direction": "expense",
            "category": "food",
            "member": "Mike",
            "source": "wechat-edited",
            "entry_type": "shared-expense",
            "note": "office run",
        }
    ]
    assert [row.to_dict() for row in storage.list_ledger_entries()] == response.get_json()["rows"]


def test_statement_save_allows_only_sub_one_rows_as_no_op(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")

    response = client.post(
        "/api/save",
        json={
            "mode": "statement",
            "rows": [
                {
                    "selected": True,
                    "transaction_time": "2026-04-10 12:00:00",
                    "counterparty": "Interest",
                    "direction": "收入",
                    "amount": "0.99",
                    "category": "interest",
                    "member": "Mike",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == []
    assert storage.list_ledger_entries() == []


def test_manual_entry_endpoint_saves_income_with_required_fields(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")

    response = client.post(
        "/api/manual-entry",
        json={
            "date": "2026-04-10",
            "description": "Salary",
            "amount": "5000",
            "direction": "income",
            "category": "salary",
            "member": "Mike",
            "entry_type": "income",
            "note": "",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["row"] == {
        "date": "2026-04-10",
        "description": "Salary",
        "amount": "+5000.00",
        "direction": "income",
        "category": "salary",
        "member": "Mike",
        "source": "manual",
        "entry_type": "income",
        "note": "",
    }
    assert [row.to_dict() for row in storage.list_ledger_entries()] == [response.get_json()["row"]]


def test_manual_entry_endpoint_saves_expense_with_required_fields(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")

    response = client.post(
        "/api/manual-entry",
        json={
            "date": "2026-04-10",
            "description": "Groceries",
            "amount": "88.6",
            "direction": "expense",
            "category": "food",
            "member": "Mike",
            "entry_type": "expense",
            "note": "weekly run",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["row"] == {
        "date": "2026-04-10",
        "description": "Groceries",
        "amount": "-88.60",
        "direction": "expense",
        "category": "food",
        "member": "Mike",
        "source": "manual",
        "entry_type": "expense",
        "note": "weekly run",
    }
    assert [row.to_dict() for row in storage.list_ledger_entries()] == [response.get_json()["row"]]


def test_manual_entry_endpoint_requires_category(client):
    response = client.post(
        "/api/manual-entry",
        json={
            "date": "2026-04-10",
            "description": "Salary",
            "amount": "5000",
            "direction": "income",
            "category": "",
            "member": "Mike",
            "entry_type": "income",
            "note": "",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid manual entry payload."}


def test_manual_entry_endpoint_requires_member(client):
    response = client.post(
        "/api/manual-entry",
        json={
            "date": "2026-04-10",
            "description": "Salary",
            "amount": "5000",
            "direction": "income",
            "category": "salary",
            "member": "",
            "entry_type": "income",
            "note": "",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid manual entry payload."}


def test_manual_entry_endpoint_rejects_amounts_below_one(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")

    response = client.post(
        "/api/manual-entry",
        json={
            "date": "2026-04-10",
            "description": "Interest",
            "amount": "0.99",
            "direction": "income",
            "category": "interest",
            "member": "Mike",
            "entry_type": "income",
            "note": "",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid manual entry payload."}
    assert storage.list_ledger_entries() == []


def test_manual_entry_endpoint_rejects_invalid_direction(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")

    response = client.post(
        "/api/manual-entry",
        json={
            "date": "2026-04-10",
            "description": "Interest",
            "amount": "26.50",
            "direction": "refund",
            "category": "interest",
            "member": "Mike",
            "entry_type": "income",
            "note": "",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid manual entry payload."}
    assert storage.list_ledger_entries() == []


def test_categories_endpoint_returns_seeded_defaults(client):
    response = client.get("/api/categories")

    assert response.status_code == 200
    assert response.get_json() == {
        "categories": [
            "cloth",
            "commute",
            "company",
            "festival",
            "food",
            "insurance",
            "operation fee",
            "rent",
        ]
    }


def test_categories_endpoint_adds_trimmed_category_once(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post("/api/categories", json={"name": "  travel  "})

    assert response.status_code == 200
    assert response.get_json()["categories"] == sorted([*DEFAULT_CATEGORIES, "travel"])

    duplicate_response = client.post("/api/categories", json={"name": "travel"})

    assert duplicate_response.status_code == 200
    assert duplicate_response.get_json()["categories"] == sorted([*DEFAULT_CATEGORIES, "travel"])


def test_members_endpoint_returns_saved_members(client):
    response = client.get("/api/members")

    assert response.status_code == 200
    assert response.get_json() == {"members": []}


def test_members_endpoint_returns_persisted_members_in_insertion_order(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    client.post("/api/members", json={"name": "Mike"})
    client.post("/api/members", json={"name": "Family"})

    response = client.get("/api/members")

    assert response.status_code == 200
    assert response.get_json() == {"members": ["Mike", "Family"]}


def test_members_endpoint_adds_trimmed_member_once(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post("/api/members", json={"name": "  Mike  "})

    assert response.status_code == 200
    assert response.get_json() == {"members": ["Mike"]}

    duplicate_response = client.post("/api/members", json={"name": "Mike"})

    assert duplicate_response.status_code == 200
    assert duplicate_response.get_json() == {"members": ["Mike"]}


def test_asset_snapshot_endpoint_saves_snapshot(client):
    response = client.post(
        "/api/asset-snapshots",
        json={
            "date": "2026-04-30",
            "cash_or_balance_total": "20000.00",
            "stock_total_value": "150000.00",
            "note": "month end",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["snapshot"]["stock_total_value"] == "150000.00"


def test_asset_snapshot_endpoint_lists_saved_snapshots(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    save_response = client.post(
        "/api/asset-snapshots",
        json={
            "date": "2026-04-30",
            "cash_or_balance_total": "20000.00",
            "stock_total_value": "150000.00",
            "note": "month end",
        },
    )

    assert save_response.status_code == 200

    response = client.get("/api/asset-snapshots")

    assert response.status_code == 200
    assert response.get_json() == {
        "snapshots": [
            {
                "date": "2026-04-30",
                "cash_or_balance_total": "20000.00",
                "stock_total_value": "150000.00",
                "note": "month end",
            }
        ]
    }


def test_asset_snapshot_endpoint_requires_non_empty_fields(client):
    response = client.post(
        "/api/asset-snapshots",
        json={
            "date": "2026-04-30",
            "cash_or_balance_total": "",
            "stock_total_value": "150000.00",
            "note": "month end",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid asset snapshot payload."}


def test_stock_record_endpoint_saves_record(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")

    response = client.post(
        "/api/stock-records",
        json={
            "date": "2026-04-30",
            "stock_name": "ACME",
            "stock_quantity": "10",
            "stock_price": "100.00",
            "stock_total_value": "1000.00",
            "note": "brokerage",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "record": {
            "date": "2026-04-30",
            "stock_name": "ACME",
            "stock_quantity": "10",
            "stock_price": "100.00",
            "stock_total_value": "1000.00",
            "note": "brokerage",
        }
    }
    assert [row.to_dict() for row in storage.list_stock_records()] == [response.get_json()["record"]]


def test_stock_record_endpoint_lists_saved_records(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    save_response = client.post(
        "/api/stock-records",
        json={
            "date": "2026-04-30",
            "stock_name": "ACME",
            "stock_quantity": "10",
            "stock_price": "100.00",
            "stock_total_value": "1000.00",
            "note": "brokerage",
        },
    )

    assert save_response.status_code == 200

    response = client.get("/api/stock-records")

    assert response.status_code == 200
    assert response.get_json() == {
        "records": [
            {
                "date": "2026-04-30",
                "stock_name": "ACME",
                "stock_quantity": "10",
                "stock_price": "100.00",
                "stock_total_value": "1000.00",
                "note": "brokerage",
            }
        ]
    }


def test_stock_record_endpoint_requires_non_empty_fields(client):
    response = client.post(
        "/api/stock-records",
        json={
            "date": "2026-04-30",
            "stock_name": "ACME",
            "stock_quantity": "10",
            "stock_price": "",
            "stock_total_value": "1000.00",
            "note": "brokerage",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid stock record payload."}


def test_dashboard_endpoint_returns_expected_aggregates(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()
    storage = ExcelExpenseStorage(tmp_path / "expenses.xlsx")
    storage.append_ledger_entries(
        [
            LedgerEntry(
                date="2026-04-01",
                description="Salary",
                amount="+5000.00",
                direction="income",
                category="salary",
                member="Mike",
                source="manual",
                entry_type="income",
                note="",
            ),
            LedgerEntry(
                date="2026-04-02",
                description="Lunch",
                amount="-26.50",
                direction="expense",
                category="food",
                member="Mike",
                source="manual",
                entry_type="expense",
                note="",
            ),
            LedgerEntry(
                date="2026-04-03",
                description="Rent",
                amount="-1500.00",
                direction="expense",
                category="rent",
                member="Lucy",
                source="manual",
                entry_type="expense",
                note="",
            ),
        ]
    )
    storage.append_asset_snapshots(
        [
            AssetSnapshot(
                date="2026-04-30",
                cash_or_balance_total="20000.00",
                stock_total_value="150000.00",
                note="month end",
            )
        ]
    )

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    assert response.get_json() == {
        "expense_by_category": [
            {"category": "food", "amount": "26.50"},
            {"category": "rent", "amount": "1500.00"},
        ],
        "expense_by_member_category": [
            {"member": "Lucy", "category": "rent", "amount": "1500.00"},
            {"member": "Mike", "category": "food", "amount": "26.50"},
        ],
        "cash_flow": [
            {
                "month": "2026-04",
                "income_total": "5000.00",
                "expense_total": "1526.50",
                "net_total": "3473.50",
            }
        ],
        "asset_trend": [
            {
                "month": "2026-04",
                "cash_or_balance_total": "20000.00",
                "stock_total_value": "150000.00",
                "total_assets": "170000.00",
            }
        ],
    }


def test_save_endpoint_rejects_malformed_payload(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post(
        "/api/save",
        json={
            "rows": [
                {"date": ["2026-03-30"], "merchant_item": {"name": "瑞幸咖啡"}, "amount": "23.50", "selected": True},
            ]
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid save payload."}


@pytest.mark.parametrize(
    ("payload", "description"),
    [
        ({}, "empty payload"),
        ({"rows": None}, "null rows"),
        ({"rows": {}}, "non-list rows"),
        ({"rows": [{"date": "2026-03-30"}]}, "omitted fields"),
        ({"rows": [{"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50", "selected": "false"}]}, "non-boolean selected"),
        ({"rows": [{"date": None, "merchant_item": None, "amount": None, "selected": True}]}, "null fields"),
        ({"rows": [{"date": " ", "merchant_item": "\t", "amount": "\n", "selected": True}]}, "whitespace-only fields"),
    ],
)
def test_save_endpoint_rejects_missing_required_fields(tmp_path, payload, description):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    response = client.post("/api/save", json=payload)

    assert response.status_code == 400, description
    assert response.get_json() == {"error": "Invalid save payload."}


def test_rows_endpoint_lists_saved_rows(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

    client.post(
        "/api/save",
        json={
            "rows": [
                {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50", "selected": True},
            ]
        },
    )

    response = client.get("/api/rows")

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50", "direction": ""}
    ]


def _wechat_fixture_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "微信账单"
    worksheet.append(["微信支付账单明细", "2026-04-06"])
    worksheet.append(["账单说明", "微信支付账单明细"])
    worksheet.append([])
    worksheet.append(["交易时间", "交易类型", "交易对方", "商品说明", "收/支", "金额(元)"])
    worksheet.append([46110.78055555555, "支付", "叫了个炸鸡", "晚餐", "支出", 26.5])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _alipay_fixture_bytes() -> bytes:
    return (
        "支付宝支付科技有限公司\n"
        "账单说明,支付宝账户\n"
        "交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易订单号,商家订单号,备注\n"
        "2026-04-03 18:40:31,消费,淘宝闪购,支付宝账户,外卖,支出,25.4,余额宝,成功,202604030001,202604030001A,外卖\n"
    ).encode("gb18030")


def test_create_app_uses_default_excel_path_without_override():
    app = create_app({"TESTING": True})

    assert app.config["EXCEL_PATH"] == DEFAULT_EXCEL_PATH
    assert app.config["EXCEL_PATH"] == Path.home() / ".expense-screenshot-tool" / "expenses.xlsx"


def test_create_app_honors_excel_path_environment_override(monkeypatch, tmp_path):
    override_path = tmp_path / "overridden.xlsx"
    monkeypatch.setenv("EXPENSE_RECORD_EXCEL_PATH", str(override_path))

    script = textwrap.dedent(
        """
        import os
        from expense_record.app import create_app

        app = create_app({"TESTING": True})
        assert str(app.config["EXCEL_PATH"]) == os.environ["EXPECTED_EXCEL_PATH"]
        """
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    env["EXPECTED_EXCEL_PATH"] = str(override_path)

    subprocess.run([sys.executable, "-c", script], check=True, cwd=PROJECT_ROOT, env=env)
