from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook

from expense_record.models import ExpenseRow


class ExcelExpenseStorage:
    headers = ("date", "merchant/item", "amount")
    sheet_name = "expenses"

    def __init__(self, workbook_path: str | Path):
        self.workbook_path = Path(workbook_path)

    def append_row(self, row: ExpenseRow) -> None:
        workbook = self._load_or_create_workbook()
        worksheet = self._get_expenses_sheet(workbook)
        worksheet.append([row.date, row.merchant_item, row.amount])
        workbook.save(self.workbook_path)

    def list_rows(self) -> list[ExpenseRow]:
        workbook = self._load_or_create_workbook()
        worksheet = self._get_expenses_sheet(workbook)
        rows: list[ExpenseRow] = []
        for values in worksheet.iter_rows(min_row=2, values_only=True):
            if not any(values):
                continue
            date, merchant_item, amount = values[:3]
            rows.append(
                ExpenseRow(
                    date="" if date is None else str(date),
                    merchant_item="" if merchant_item is None else str(merchant_item),
                    amount="" if amount is None else str(amount),
                )
            )
        return rows

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
            return workbook[self.sheet_name]

        worksheet = workbook.create_sheet(self.sheet_name)
        worksheet.append(list(self.headers))
        workbook.save(self.workbook_path)
        return worksheet
