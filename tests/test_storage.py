from expense_record.models import ExpenseRow
from expense_record.storage import ExcelExpenseStorage


def test_excel_storage_creates_workbook_and_appends_rows(tmp_path):
    workbook_path = tmp_path / "expenses.xlsx"
    storage = ExcelExpenseStorage(workbook_path)

    storage.append_row(ExpenseRow(date="2026-03-29", merchant_item="星巴克咖啡", amount="32.00"))
    storage.append_row(ExpenseRow(date="2026-03-30", merchant_item="便利店", amount="8.50"))

    assert workbook_path.exists()
    assert storage.list_rows() == [
        ExpenseRow(date="2026-03-29", merchant_item="星巴克咖啡", amount="32.00"),
        ExpenseRow(date="2026-03-30", merchant_item="便利店", amount="8.50"),
    ]
