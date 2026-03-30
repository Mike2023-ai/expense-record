from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from expense_record.config import DEFAULT_EXCEL_PATH
from expense_record.models import ExpenseRow
from expense_record.ocr import run_ocr_lines
from expense_record.parser import parse_expense_row


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

    lines = run_ocr_lines(image.read())
    row = parse_expense_row(lines)
    return jsonify({"row": row.to_dict(), "lines": lines})


@api.post("/save")
def save_row():
    payload = request.get_json(silent=True) or {}
    row = ExpenseRow(
        date=str(payload.get("date", "")).strip(),
        merchant_item=str(payload.get("merchant_item", "")).strip(),
        amount=str(payload.get("amount", "")).strip(),
    )
    storage = _storage()
    storage.append_row(row)
    rows = [item.to_dict() for item in storage.list_rows()]
    return jsonify({"rows": rows})
