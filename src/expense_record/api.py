from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from expense_record.config import DEFAULT_EXCEL_PATH
from expense_record.models import ExpenseRow, LedgerEntry, StatementImportRow
from expense_record.ocr import run_ocr_lines
from expense_record.parser import extract_expense_rows
from expense_record.statement_import import normalize_statement_ledger_fields


api = Blueprint("api", __name__, url_prefix="/api")
_DROP_STATEMENT_ROW = object()


def _storage() -> ExcelExpenseStorage:
    from expense_record.storage import ExcelExpenseStorage

    excel_path = Path(current_app.config.get("EXCEL_PATH", DEFAULT_EXCEL_PATH))
    return ExcelExpenseStorage(excel_path)


@api.get("/rows")
def list_rows():
    rows = [row.to_dict() for row in _storage().list_rows()]
    return jsonify({"rows": rows})


@api.delete("/rows")
def clear_rows():
    _storage().clear_all()
    return jsonify({"rows": []})


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
    core_keys = ("date", "merchant_item", "amount")
    warning = ""
    if not any(any(row.get(k) for k in core_keys) for row in row_dicts):
        warning = "OCR returned no usable fields."
    elif any(not all(row.get(k) for k in core_keys) for row in row_dicts):
        warning = "OCR returned incomplete fields."

    payload = {"rows": row_dicts, "lines": lines}
    if warning:
        payload["warning"] = warning
    return jsonify(payload)


@api.post("/import-statement")
def import_statement():
    statement_file = request.files.get("statement_file")
    if statement_file is None or statement_file.filename == "":
        return jsonify({"error": "No statement file provided."}), 400

    from expense_record.statement_import import (
        UnsupportedStatementFileError,
        detect_statement_source,
        import_statement_rows,
        statement_rows_to_review_rows,
    )

    try:
        raw_bytes = statement_file.read()
        source = detect_statement_source(statement_file.filename, raw_bytes)
        rows = statement_rows_to_review_rows(
            _normalize_statement_rows(import_statement_rows(statement_file.filename, raw_bytes)),
            source=source,
        )
    except (UnsupportedStatementFileError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Statement import failed")
        return jsonify({"error": "Statement import failed."}), 500

    return jsonify({"rows": [row.to_dict() for row in rows]})


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
    ledger_rows_to_save: list[LedgerEntry] = []
    selected_count = 0
    dropped_statement_count = 0
    if isinstance(payload, dict) and payload.get("mode") == "statement":
        for row_payload in rows_payload:
            selected_row = _normalize_selected_statement_save_row(row_payload)
            if selected_row is None:
                return jsonify({"error": "Invalid save payload."}), 400
            if selected_row is False:
                continue
            if selected_row is _DROP_STATEMENT_ROW:
                dropped_statement_count += 1
                continue
            selected_count += 1
            statement_row = selected_row
            if _statement_row_is_effectively_blank(statement_row):
                return jsonify({"error": "At least one selected row is required."}), 400
            ledger_rows_to_save.append(statement_row)
    else:
        for row_payload in rows_payload:
            if not isinstance(row_payload, dict):
                return jsonify({"error": "Invalid save payload."}), 400
            selected = row_payload.get("selected", True)
            if not isinstance(selected, bool):
                return jsonify({"error": "Invalid save payload."}), 400
            if not selected:
                continue
            selected_count += 1

            date = _coerce_save_field(row_payload, "date")
            merchant_item = _coerce_save_field(row_payload, "merchant_item")
            amount = _coerce_save_field(row_payload, "amount")

            if date is None or merchant_item is None or amount is None:
                return jsonify({"error": "Invalid save payload."}), 400
            if not any((date, merchant_item, amount)):
                return jsonify({"error": "At least one selected row is required."}), 400

            rows_to_save.append(ExpenseRow(date=date, merchant_item=merchant_item, amount=amount))

    if selected_count == 0:
        if dropped_statement_count > 0:
            rows = [item.to_dict() for item in storage.list_ledger_entries()]
            return jsonify({"rows": rows})
        return jsonify({"error": "At least one selected row is required."}), 400

    if ledger_rows_to_save:
        storage.append_ledger_entries(ledger_rows_to_save)
        rows = [item.to_dict() for item in storage.list_ledger_entries()]
        return jsonify({"rows": rows})

    storage.append_rows(rows_to_save)
    rows = [item.to_dict() for item in storage.list_rows()]
    return jsonify({"rows": rows})


@api.post("/manual-entry")
def save_manual_entry():
    payload = request.get_json(silent=True)
    row = _normalize_manual_entry_payload(payload)
    if row is None:
        return jsonify({"error": "Invalid manual entry payload."}), 400

    _storage().append_ledger_entries([row])
    return jsonify({"row": row.to_dict()})


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


def _normalize_statement_rows(rows: object) -> list[StatementImportRow]:
    if not isinstance(rows, list):
        raise TypeError("Unexpected statement row collection.")
    normalized: list[StatementImportRow] = []
    for row in rows:
        if isinstance(row, StatementImportRow):
            normalized.append(row)
            continue
        raise TypeError("Unexpected statement row value.")
    return normalized


def _coerce_statement_save_field(payload: object, field: str, *, allow_blank: bool = False) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(field)
    if value is None or not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized or allow_blank:
        return normalized
    return None


def _normalize_selected_statement_save_row(payload: object) -> LedgerEntry | bool | object | None:
    if not isinstance(payload, dict):
        return None

    selected = payload.get("selected", True)
    if not isinstance(selected, bool):
        return None
    if not selected:
        return False

    transaction_time = _coerce_statement_save_field(payload, "transaction_time")
    counterparty = _coerce_statement_save_field(payload, "counterparty")
    direction = _coerce_statement_save_field(payload, "direction")
    amount = _coerce_statement_save_field(payload, "amount")
    category = _coerce_statement_save_field(payload, "category")
    member = _coerce_statement_save_field(payload, "member")
    source = _coerce_statement_save_field(payload, "source", allow_blank=True)
    entry_type = _coerce_statement_save_field(payload, "entry_type", allow_blank=True)
    note = _coerce_statement_save_field(payload, "note", allow_blank=True)

    if (
        transaction_time is None
        or counterparty is None
        or direction is None
        or amount is None
        or category is None
        or member is None
    ):
        return None

    try:
        normalized_direction, signed_amount, default_entry_type = normalize_statement_ledger_fields(
            direction,
            amount,
            minimum_amount=Decimal("1"),
        )
    except ValueError as exc:
        if str(exc) == "Amount too small.":
            return _DROP_STATEMENT_ROW
        return None
    except InvalidOperation:
        return None
    return LedgerEntry(
        date=transaction_time,
        description=counterparty,
        direction=normalized_direction,
        amount=signed_amount,
        category=category,
        member=member,
        source="" if source is None else source,
        entry_type=default_entry_type if entry_type in (None, "") else entry_type,
        note="" if note is None else note,
    )


def _statement_row_is_effectively_blank(row: LedgerEntry) -> bool:
    return not any((row.date, row.description, row.direction, row.amount, row.category, row.member))


def _normalize_manual_entry_payload(payload: object) -> LedgerEntry | None:
    date = _coerce_statement_save_field(payload, "date")
    description = _coerce_statement_save_field(payload, "description")
    direction = _coerce_statement_save_field(payload, "direction")
    amount = _coerce_statement_save_field(payload, "amount")
    category = _coerce_statement_save_field(payload, "category")
    member = _coerce_statement_save_field(payload, "member")
    entry_type = _coerce_statement_save_field(payload, "entry_type", allow_blank=True)
    note = _coerce_statement_save_field(payload, "note", allow_blank=True)

    if (
        date is None
        or description is None
        or direction is None
        or amount is None
        or category is None
        or member is None
    ):
        return None

    try:
        normalized_direction, signed_amount, default_entry_type = normalize_statement_ledger_fields(
            direction,
            amount,
            minimum_amount=Decimal("1"),
        )
    except (InvalidOperation, ValueError):
        return None

    return LedgerEntry(
        date=date,
        description=description,
        amount=signed_amount,
        direction=normalized_direction,
        category=category,
        member=member,
        source="manual",
        entry_type=default_entry_type if entry_type in (None, "") else entry_type,
        note="" if note is None else note,
    )


def _extract_save_rows_payload(payload: object) -> list[object] | None:
    if not isinstance(payload, dict):
        return None

    rows = payload.get("rows")
    if not isinstance(rows, list):
        return None
    return rows
