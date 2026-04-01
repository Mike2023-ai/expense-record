from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from expense_record.config import DEFAULT_EXCEL_PATH
from expense_record.models import ExpenseRow
from expense_record.ocr import run_ocr_lines
from expense_record.parser import extract_expense_rows


api = Blueprint("api", __name__, url_prefix="/api")


def _storage() -> ExcelExpenseStorage:
    from expense_record.storage import ExcelExpenseStorage

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

    try:
        lines = run_ocr_lines(image.read())
        rows = _normalize_expense_rows(extract_expense_rows(lines))
    except Exception:
        current_app.logger.exception("OCR extraction failed")
        return jsonify({"error": "OCR extraction failed."}), 500

    row_dicts = [row.to_dict() for row in rows]
    warning = ""
    if not any(any(value for value in row.values()) for row in row_dicts):
        warning = "OCR returned no usable fields."
    elif any(not all(value for value in row.values()) for row in row_dicts):
        warning = "OCR returned incomplete fields."

    payload = {"rows": row_dicts, "lines": lines}
    if warning:
        payload["warning"] = warning
    return jsonify(payload)


def _coerce_save_field(payload: object, field: str) -> str | None:
    if not isinstance(payload, dict):
        return None

    value = payload.get(field)
    if value is None or not isinstance(value, str):
        return None

    if value == "":
        return ""

    value = value.strip()
    if not value:
        return None
    return value


@api.post("/save")
def save_row():
    payload = request.get_json(silent=True)
    rows_payload = _extract_save_rows_payload(payload)
    if rows_payload is None or not rows_payload:
        return jsonify({"error": "Invalid save payload."}), 400

    storage = _storage()
    rows_to_save: list[ExpenseRow] = []
    for row_payload in rows_payload:
        if not isinstance(row_payload, dict):
            return jsonify({"error": "Invalid save payload."}), 400
        if not row_payload.get("selected", True):
            continue

        date = _coerce_save_field(row_payload, "date")
        merchant_item = _coerce_save_field(row_payload, "merchant_item")
        amount = _coerce_save_field(row_payload, "amount")

        if date is None or merchant_item is None or amount is None:
            return jsonify({"error": "Invalid save payload."}), 400
        if not any((date, merchant_item, amount)):
            return jsonify({"error": "At least one selected row is required."}), 400

        rows_to_save.append(ExpenseRow(date=date, merchant_item=merchant_item, amount=amount))

    if rows_to_save:
        storage.append_rows(rows_to_save)

    rows = [item.to_dict() for item in storage.list_rows()]
    return jsonify({"rows": rows})


def _normalize_expense_rows(rows: object) -> list[ExpenseRow]:
    if rows is None:
        return []
    if isinstance(rows, ExpenseRow):
        return [rows]
    if not isinstance(rows, list):
        raise TypeError("Unexpected expense row collection.")

    normalized_rows: list[ExpenseRow] = []
    for row in rows:
        if isinstance(row, ExpenseRow):
            normalized_rows.append(row)
            continue
        if isinstance(row, dict):
            normalized_rows.append(
                ExpenseRow(
                    date="" if row.get("date") is None else str(row.get("date")),
                    merchant_item="" if row.get("merchant_item") is None else str(row.get("merchant_item")),
                    amount="" if row.get("amount") is None else str(row.get("amount")),
                )
            )
            continue
        raise TypeError("Unexpected expense row value.")
    return normalized_rows


def _extract_save_rows_payload(payload: object) -> list[object] | None:
    if not isinstance(payload, dict):
        return None

    rows = payload.get("rows")
    if not isinstance(rows, list):
        return None
    return rows
