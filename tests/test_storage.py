from expense_record.models import ExpenseRow
from expense_record.storage import ExcelExpenseStorage
from openpyxl import Workbook, load_workbook


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


def test_excel_storage_preserves_preexisting_rows_with_custom_header(tmp_path):
    workbook_path = tmp_path / "expenses.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "expenses"
    worksheet.append(["Date", "Merchant", "Amount"])
    worksheet.append(["2026-03-01", "Existing Shop", "11.00"])
    workbook.save(workbook_path)

    storage = ExcelExpenseStorage(workbook_path)

    assert storage.list_rows() == [ExpenseRow(date="2026-03-01", merchant_item="Existing Shop", amount="11.00")]

    storage.append_row(ExpenseRow(date="2026-03-02", merchant_item="New Shop", amount="12.00"))

    reloaded = load_workbook(workbook_path).active
    assert [row for row in reloaded.iter_rows(values_only=True)] == [
        ("Date", "Merchant", "Amount"),
        ("2026-03-01", "Existing Shop", "11.00"),
        ("2026-03-02", "New Shop", "12.00"),
    ]
