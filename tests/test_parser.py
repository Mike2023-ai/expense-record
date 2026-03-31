from datetime import date
from datetime import date as real_date

from expense_record.models import ExpenseRow
import expense_record.parser as parser_module
from expense_record.parser import parse_expense_row


class FixedDate(real_date):
    @classmethod
    def today(cls):
        return cls(2025, 1, 1)


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


def test_parse_expense_row_supports_labeled_amount_lines():
    row = parse_expense_row(
        [
            "2026-03-29",
            "付款 ¥32.00",
        ]
    )

    assert row.amount == "32.00"


def test_parse_expense_row_supports_amount_suffixes_and_labels():
    row = parse_expense_row(
        [
            "2026-03-29",
            "金额 32.00",
            "-32.00元",
        ]
    )

    assert row.amount == "32.00"


def test_parse_expense_row_extracts_labeled_merchant_name():
    row = parse_expense_row(
        [
            "2026-03-29 18:21",
            "商户名称 瑞幸咖啡",
            "付款 ¥32.00",
        ]
    )

    assert row.merchant_item == "瑞幸咖啡"


def test_parse_expense_row_skips_metadata_before_merchant():
    row = parse_expense_row(
        [
            "2026-03-29 18:21",
            "交易单号 123456",
            "尾号1234",
            "付款方式 储蓄卡",
            "商户名称 瑞幸咖啡",
            "付款 ¥32.00",
        ]
    )

    assert row.merchant_item == "瑞幸咖啡"


def test_parse_expense_row_handles_split_merchant_label_and_value():
    row = parse_expense_row(
        [
            "2026-03-29 18:21",
            "商户名称",
            "瑞幸咖啡",
            "付款 ¥32.00",
        ]
    )

    assert row.merchant_item == "瑞幸咖啡"


def test_parse_expense_row_handles_split_merchant_label_tokens():
    row = parse_expense_row(
        [
            "2026-03-29 18:21",
            "商户",
            "名称",
            "瑞幸咖啡",
            "付款 ¥32.00",
        ]
    )

    assert row.merchant_item == "瑞幸咖啡"


def test_parse_expense_row_handles_split_business_label_tokens():
    row = parse_expense_row(
        [
            "2026-03-29 18:21",
            "商家",
            "名称",
            "瑞幸咖啡",
            "付款 ¥32.00",
        ]
    )

    assert row.merchant_item == "瑞幸咖啡"


def test_parse_expense_row_supports_month_day_date_with_time():
    row = parse_expense_row(
        [
            "3月29日 08:42",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == f"{date.today().year}-03-29"


def test_parse_expense_row_supports_month_day_date_without_time():
    row = parse_expense_row(
        [
            "3月29日",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == f"{date.today().year}-03-29"


def test_parse_expense_row_supports_slash_month_day_date_with_time():
    row = parse_expense_row(
        [
            "3/29 08:42",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == f"{date.today().year}-03-29"


def test_parse_expense_row_supports_realistic_month_day_row():
    row = parse_expense_row(
        [
            "扫二维码付款-给早餐",
            "3月29日 08:42",
            "-5.00",
        ]
    )

    assert row == ExpenseRow(
        date=f"{date.today().year}-03-29",
        merchant_item="扫二维码付款-给早餐",
        amount="5.00",
    )


def test_parse_expense_row_supports_dot_delimited_month_day_date_with_time():
    row = parse_expense_row(
        [
            "3.29 08:42",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == f"{date.today().year}-03-29"


def test_parse_expense_row_rejects_invalid_synthesized_month_day_date_on_non_leap_year(
    monkeypatch,
):
    monkeypatch.setattr(parser_module, "date", FixedDate)

    row = parse_expense_row(
        [
            "2月29日",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == ""


def test_parse_expense_row_allows_leap_day_month_day_date(monkeypatch):
    class LeapDate(real_date):
        @classmethod
        def today(cls):
            return cls(2024, 1, 1)

    monkeypatch.setattr(parser_module, "date", LeapDate)

    row = parse_expense_row(
        [
            "2月29日",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == "2024-02-29"


def test_extract_date_does_not_treat_plain_decimal_as_month_day():
    assert parser_module._extract_date(["1.23"]) == ""


def test_extract_date_does_not_treat_ambiguous_slash_token_as_month_day():
    assert parser_module._extract_date(["11/12"]) == ""
