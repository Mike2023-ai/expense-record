from expense_record.models import ExpenseRow
from expense_record.parser import parse_expense_row


def test_parse_expense_row_extracts_chinese_text():
    row = parse_expense_row(
        [
            "微信支付",
            "2026-03-29 18:21",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row == ExpenseRow(date="2026-03-29", merchant_item="星巴克咖啡", amount="32.00")


def test_parse_expense_row_leaves_missing_fields_blank():
    row = parse_expense_row(
        [
            "支付宝",
            "2026年03月29日",
        ]
    )

    assert row.date == "2026-03-29"
    assert row.merchant_item == ""
    assert row.amount == ""


def test_parse_expense_row_supports_ungrouped_amounts():
    row = parse_expense_row(
        [
            "2026-03-29 18:21",
            "星巴克咖啡",
            "￥1234.56",
        ]
    )

    assert row.amount == "1234.56"


def test_parse_expense_row_keeps_digit_bearing_merchant_names():
    row = parse_expense_row(
        [
            "2026-03-29",
            "7-Eleven",
            "￥8.50",
        ]
    )

    assert row.merchant_item == "7-Eleven"
