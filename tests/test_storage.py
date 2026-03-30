from expense_record.models import ExpenseRow
from expense_record.storage import ExcelExpenseStorage
from datetime import date, datetime
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


def test_excel_storage_uses_named_expenses_sheet_in_multi_sheet_workbook(tmp_path):
    workbook_path = tmp_path / "expenses.xlsx"
    workbook = Workbook()
    default_sheet = workbook.active
    default_sheet.title = "summary"
    default_sheet.append(["ignore", "these", "rows"])

    expenses_sheet = workbook.create_sheet("expenses")
    expenses_sheet.append(["date", "merchant/item", "amount"])
    expenses_sheet.append(["2026-03-01", "Existing Shop", "11.00"])
    workbook.active = 0
    workbook.save(workbook_path)

    storage = ExcelExpenseStorage(workbook_path)

    assert storage.list_rows() == [ExpenseRow(date="2026-03-01", merchant_item="Existing Shop", amount="11.00")]

    storage.append_row(ExpenseRow(date="2026-03-02", merchant_item="New Shop", amount="12.00"))

    reloaded = load_workbook(workbook_path)
    assert [row for row in reloaded["summary"].iter_rows(values_only=True)] == [("ignore", "these", "rows")]
    assert [row for row in reloaded["expenses"].iter_rows(values_only=True)] == [
        ("date", "merchant/item", "amount"),
        ("2026-03-01", "Existing Shop", "11.00"),
        ("2026-03-02", "New Shop", "12.00"),
    ]


def test_excel_storage_creates_missing_expenses_sheet_with_headers(tmp_path):
    workbook_path = tmp_path / "expenses.xlsx"
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "summary"
    summary_sheet.append(["ignore", "these", "rows"])
    workbook.save(workbook_path)

    storage = ExcelExpenseStorage(workbook_path)

    assert storage.list_rows() == []

    storage.append_row(ExpenseRow(date="2026-03-02", merchant_item="New Shop", amount="12.00"))

    reloaded = load_workbook(workbook_path)
    assert [row for row in reloaded["summary"].iter_rows(values_only=True)] == [("ignore", "these", "rows")]
    assert [row for row in reloaded["expenses"].iter_rows(values_only=True)] == [
        ("date", "merchant/item", "amount"),
        ("2026-03-02", "New Shop", "12.00"),
    ]


def test_excel_storage_initializes_blank_existing_expenses_sheet(tmp_path):
    workbook_path = tmp_path / "expenses.xlsx"
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "summary"
    summary_sheet.append(["ignore", "these", "rows"])
    workbook.create_sheet("expenses")
    workbook.save(workbook_path)

    storage = ExcelExpenseStorage(workbook_path)

    assert storage.list_rows() == []

    storage.append_row(ExpenseRow(date="2026-03-03", merchant_item="Blank Sheet Shop", amount="13.00"))

    reloaded = load_workbook(workbook_path)
    assert [row for row in reloaded["summary"].iter_rows(values_only=True)] == [("ignore", "these", "rows")]
    assert [row for row in reloaded["expenses"].iter_rows(values_only=True)] == [
        ("date", "merchant/item", "amount"),
        ("2026-03-03", "Blank Sheet Shop", "13.00"),
    ]


def test_excel_storage_normalizes_typed_date_cells(tmp_path):
    workbook_path = tmp_path / "expenses.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "expenses"
    worksheet.append(["date", "merchant/item", "amount"])
    worksheet.append([date(2026, 3, 4), "Typed Date Shop", "14.00"])
    worksheet.append([datetime(2026, 3, 5, 15, 30), "Typed Datetime Shop", "15.00"])
    workbook.save(workbook_path)

    storage = ExcelExpenseStorage(workbook_path)

    assert storage.list_rows() == [
        ExpenseRow(date="2026-03-04", merchant_item="Typed Date Shop", amount="14.00"),
        ExpenseRow(date="2026-03-05", merchant_item="Typed Datetime Shop", amount="15.00"),
    ]
