from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from expense_record.config import DEFAULT_EXCEL_PATH, resolve_excel_path
from expense_record.models import ExpenseRow
from expense_record.ocr import run_ocr_lines
from expense_record.parser import parse_expense_row


api = Blueprint("api", __name__, url_prefix="/api")


def _storage() -> ExcelExpenseStorage:
    from expense_record.storage import ExcelExpenseStorage

    configured_path = current_app.config.get("EXCEL_PATH")
    env_path = resolve_excel_path()
    if configured_path is None:
        excel_path = env_path
    else:
        excel_path = Path(configured_path)
        if excel_path == DEFAULT_EXCEL_PATH and env_path != DEFAULT_EXCEL_PATH:
            excel_path = env_path
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
        row = parse_expense_row(lines)
    except Exception:
        current_app.logger.exception("OCR extraction failed")
        return jsonify({"error": "OCR extraction failed."}), 500

    row_data = row.to_dict()
    warning = ""
    if not any(row_data.values()):
        warning = "OCR returned no usable fields."
    elif not all(row_data.values()):
        warning = "OCR returned incomplete fields."

    payload = {"row": row_data, "lines": lines}
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
    date = _coerce_save_field(payload, "date")
    merchant_item = _coerce_save_field(payload, "merchant_item")
    amount = _coerce_save_field(payload, "amount")

    if date is None or merchant_item is None or amount is None:
        return jsonify({"error": "Invalid save payload."}), 400

    row = ExpenseRow(date=date, merchant_item=merchant_item, amount=amount)
    storage = _storage()
    storage.append_row(row)
    rows = [item.to_dict() for item in storage.list_rows()]
    return jsonify({"rows": rows})
