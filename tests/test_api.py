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
from expense_record.config import DEFAULT_EXCEL_PATH, resolve_app_version
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


def test_frontend_ignores_stale_selection_work_and_resets_save_state():
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
          "extract-button": makeElement("extract-button"),
          "save-button": makeElement("save-button"),
          "status-message": makeElement("status-message"),
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
          "review-table": makeElement("review-table"),
          "review-body": makeElement("review-body"),
          "records-body": makeElement("records-body"),
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

        function flush() {
          return new Promise((resolve) => setImmediate(resolve));
        }

        async function main() {
          selectScreenshot("first.png");
          assert.strictEqual(elements["preview-caption"].textContent, "first.png");
          assert.deepStrictEqual(elements["review-body"].children, []);
          assert.strictEqual(elements["save-button"].disabled, true);
          assert.strictEqual(fileReaderInstances.length, 1);

          extractHandler();
          selectScreenshot("second.png");

          fileReaderInstances[0].result = "data:first";
          fileReaderInstances[0].onload();
          await flush();
          assert.strictEqual(elements["preview-image"].src, "");
          assert.strictEqual(elements["preview-caption"].textContent, "second.png");
          assert.deepStrictEqual(elements["review-body"].children, []);
          assert.strictEqual(elements["save-button"].disabled, true);

          assert.strictEqual(fileReaderInstances.length, 2);

          const firstPendingExtract = pendingExtractResponses.shift();
          firstPendingExtract(makeResponse([{ date: "2026-03-30", merchant_item: "old", amount: "1.00" }]));
          await flush();
          assert.deepStrictEqual(elements["review-body"].children, []);
          assert.strictEqual(elements["save-button"].disabled, true);

          extractHandler();
          const secondPendingExtract = pendingExtractResponses.shift();
          secondPendingExtract(
            makeResponse(
              [
                { date: "2026-03-31", merchant_item: "new", amount: "2.00" },
                { date: "2026-04-01", merchant_item: "skip", amount: "3.00" },
              ],
              ["2026-03-31", "new", "2.00"]
            )
          );
          await flush();

          fileReaderInstances[1].result = "data:second";
          fileReaderInstances[1].onload();
          await flush();

          assert.strictEqual(elements["preview-image"].src, "data:second");
          assert.strictEqual(elements["review-body"].children.length, 2);
          const firstRow = elements["review-body"].children[0];
          const secondRow = elements["review-body"].children[1];
          assert.strictEqual(firstRow.children[0].children[0].checked, true);
          assert.strictEqual(firstRow.children[1].children[0].value, "2026-03-31");
          assert.strictEqual(firstRow.children[2].children[0].value, "new");
          assert.strictEqual(firstRow.children[3].children[0].value, "2.00");
          assert.strictEqual(secondRow.children[2].children[0].value, "skip");
          assert.strictEqual(elements["save-button"].disabled, false);
          assert.strictEqual(elements["extract-button"].disabled, false);
          assert.strictEqual(elements["ocr-lines-panel"].hidden, false);
          assert.deepStrictEqual(
            elements["ocr-lines-list"].children.map((child) => child.textContent),
            ["2026-03-31", "new", "2.00"]
          );
          assert.ok(fetchCalls.some((call) => call.url === "/api/rows"));

          const imagePasteEvent = pasteImage("clipboard.png");
          assert.strictEqual(imagePasteEvent.defaultPrevented, true);
          assert.strictEqual(elements["preview-caption"].textContent, "clipboard.png");
          assert.strictEqual(fileReaderInstances.length, 3);

          fileReaderInstances[2].result = "data:clipboard";
          fileReaderInstances[2].onload();
          await flush();
          assert.strictEqual(elements["preview-image"].src, "data:clipboard");

          const inputPasteEvent = pasteTextIntoInput(firstRow.children[1].children[0]);
          assert.strictEqual(inputPasteEvent.defaultPrevented, false);
          assert.strictEqual(elements["preview-caption"].textContent, "clipboard.png");
          assert.strictEqual(elements["preview-image"].src, "data:clipboard");
          assert.strictEqual(fileReaderInstances.length, 3);

          selectScreenshot("third.png");
          assert.strictEqual(elements["ocr-lines-panel"].hidden, true);
          assert.deepStrictEqual(elements["ocr-lines-list"].children, []);
          extractHandler();
          const thirdPendingExtract = pendingExtractResponses.shift();
          thirdPendingExtract(makeResponse([], ["OCR returned no usable fields."], "OCR returned no usable fields."));
          await flush();

          assert.strictEqual(elements["status-message"].textContent, "OCR returned no usable fields.");
          assert.strictEqual(elements["status-message"].style.color, "#9d2d22");
          assert.strictEqual(elements["save-button"].disabled, true);

          extractHandler();
          const fourthPendingExtract = pendingExtractResponses.shift();
          fourthPendingExtract(makeResponse([{ date: "04-02", merchant_item: "save-me", amount: "6.00" }], ["04-02", "save-me", "6.00"]));
          await flush();

          const savedRow = elements["review-body"].children[0];
          savedRow.children[1].children[0].value = "04-03";
          savedRow.children[0].children[0].checked = true;
          elements["save-button"].listeners.click();
          const saveCall = fetchCalls.filter((call) => call.url === "/api/save").at(-1);
          assert.deepStrictEqual(JSON.parse(saveCall.options.body), {
            rows: [{ date: "04-03", merchant_item: "save-me", amount: "6.00", selected: true }],
          });
          pendingSaveResponses.shift()({
            ok: true,
            json: async () => ({ rows: [{ date: "04-03", merchant_item: "save-me", amount: "6.00" }] }),
          });
          await flush();
          assert.strictEqual(elements["status-message"].textContent, "Rows saved to Excel.");
          assert.strictEqual(elements["review-body"].children.length, 0);
          assert.strictEqual(elements["save-button"].disabled, true);
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
          "ocr-lines-panel": makeElement("ocr-lines-panel"),
          "ocr-lines-list": makeElement("ocr-lines-list"),
          "extract-button": makeElement("extract-button"),
          "save-button": makeElement("save-button"),
          "status-message": makeElement("status-message"),
          "review-table": makeElement("review-table"),
          "review-body": makeElement("review-body"),
          "records-body": makeElement("records-body"),
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
        assert b"Expense Screenshot Tool" in response.data
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
        "rows": [{"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"}],
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
            {"date": "03-28", "merchant_item": "滴滴出行", "amount": "28.00"},
            {"date": "03-29", "merchant_item": "扫二维码付款-给早餐", "amount": "5.00"},
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
        "rows": [{"date": "03-29", "merchant_item": "", "amount": ""}],
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
            "transaction_time": "2026-03-29 18:44:00",
            "counterparty": "叫了个炸鸡",
            "direction": "支出",
            "amount": "26.50",
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
        {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"}
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
        {"date": "03-28", "merchant_item": "滴滴出行", "amount": "28.00"}
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
        {"date": "", "merchant_item": "手动补录", "amount": ""}
    ]


def test_save_endpoint_persists_selected_statement_rows(tmp_path):
    app = create_app({"TESTING": True, "EXCEL_PATH": tmp_path / "expenses.xlsx"})
    client = app.test_client()

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
                    "selected": True,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.get_json()["rows"] == [
        {"date": "2026-03-29 18:44:00", "merchant_item": "叫了个炸鸡 | 支出", "amount": "26.50"}
    ]


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
        {"date": "2026-03-30", "merchant_item": "瑞幸咖啡", "amount": "23.50"}
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
