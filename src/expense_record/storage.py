from __future__ import annotations

from collections.abc import Iterable
from datetime import date as date_type, datetime as datetime_type
from collections.abc import Iterable
from pathlib import Path

from openpyxl import Workbook, load_workbook

from expense_record.models import ExpenseRow


class ExcelExpenseStorage:
    headers = ("date", "merchant/item", "amount", "direction")
    sheet_name = "expenses"

    def __init__(self, workbook_path: str | Path):
        self.workbook_path = Path(workbook_path)

    def append_row(self, row: ExpenseRow) -> None:
        self.append_rows((row,))

    def append_rows(self, rows: Iterable[ExpenseRow]) -> None:
        rows = list(rows)
        if not rows:
            return

        workbook = self._load_or_create_workbook()
        worksheet = self._get_expenses_sheet(workbook)
        for row in rows:
            worksheet.append([row.date, row.merchant_item, row.amount, row.direction])
        workbook.save(self.workbook_path)

    def list_rows(self) -> list[ExpenseRow]:
        workbook = self._load_or_create_workbook()
        worksheet = self._get_expenses_sheet(workbook)
        rows: list[ExpenseRow] = []
        for values in worksheet.iter_rows(min_row=2, values_only=True):
            if not any(values):
                continue
            padded = list(values) + [""] * (4 - len(values))
            date, merchant_item, amount, direction = padded[:4]
            rows.append(
                ExpenseRow(
                    date=self._normalize_date_value(date),
                    merchant_item="" if merchant_item is None else str(merchant_item),
                    amount="" if amount is None else str(amount),
                    direction="" if direction is None else str(direction),
                )
            )
        return rows

    def clear_all(self) -> None:
        workbook = self._load_or_create_workbook()
        worksheet = self._get_expenses_sheet(workbook)
        worksheet.delete_rows(2, worksheet.max_row)
        workbook.save(self.workbook_path)

    def _load_or_create_workbook(self):
        if self.workbook_path.exists():
            return load_workbook(self.workbook_path)

        self.workbook_path.parent.mkdir(parents=True, exist_ok=True)
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = self.sheet_name
        worksheet.append(list(self.headers))
        workbook.save(self.workbook_path)
        return workbook

    def _get_expenses_sheet(self, workbook):
        if self.sheet_name in workbook.sheetnames:
            worksheet = workbook[self.sheet_name]
            if self._sheet_needs_headers(worksheet):
                self._write_headers(worksheet)
                workbook.save(self.workbook_path)
            return worksheet

        worksheet = workbook.create_sheet(self.sheet_name)
        self._write_headers(worksheet)
        workbook.save(self.workbook_path)
        return worksheet

    def _sheet_needs_headers(self, worksheet) -> bool:
        return worksheet.max_row == 1 and worksheet.max_column == 1 and worksheet["A1"].value is None

    def _write_headers(self, worksheet) -> None:
        for column, header in enumerate(self.headers, start=1):
            worksheet.cell(row=1, column=column, value=header)

    def _normalize_date_value(self, value) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime_type):
            return value.date().isoformat()
        if isinstance(value, date_type):
            return value.isoformat()
        return str(value)
