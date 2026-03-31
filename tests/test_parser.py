import pytest
from datetime import date
from datetime import date as real_date

from expense_record.models import ExpenseRow
import expense_record.parser as parser_module
from expense_record.parser import extract_expense_rows, parse_expense_row


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


def test_parse_expense_row_prefers_negative_ocr_amount_over_crossed_out_positive_amount():
    row = parse_expense_row(
        [
            "滴滴出行",
            "-28.00",
            "3月28日11:44",
            "31.00",
        ]
    )

    assert row == ExpenseRow(date="03-28", merchant_item="滴滴出行", amount="28.00")


def test_parse_expense_row_prefers_last_negative_ocr_amount():
    row = parse_expense_row(
        [
            "折扣",
            "-5.00",
            "实付 -32.00",
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

    assert row.date == "03-29"


def test_parse_expense_row_supports_month_day_date_with_attached_time():
    row = parse_expense_row(
        [
            "3月29日08:42",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == "03-29"


def test_parse_expense_row_supports_month_day_date_without_time():
    row = parse_expense_row(
        [
            "3月29日",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == "03-29"


def test_parse_expense_row_supports_slash_month_day_date_with_time():
    row = parse_expense_row(
        [
            "3/29 08:42",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == "03-29"


@pytest.mark.parametrize("date_text", ["3/30", "3.30"])
def test_parse_expense_row_supports_separator_month_day_date_without_time(date_text):
    row = parse_expense_row(
        [
            date_text,
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == "03-30"


def test_parse_expense_row_supports_realistic_month_day_row():
    row = parse_expense_row(
        [
            "扫二维码付款-给早餐",
            "3月29日 08:42",
            "-5.00",
        ]
    )

    assert row == ExpenseRow(
        date="03-29",
        merchant_item="扫二维码付款-给早餐",
        amount="5.00",
    )


def test_extract_expense_rows_returns_single_row_through_new_entrypoint():
    rows = extract_expense_rows(
        [
            "微信支付",
            "2026-03-29 18:21",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert rows == [
        ExpenseRow(date="2026-03-29", merchant_item="星巴克咖啡", amount="32.00")
    ]


def test_extract_expense_rows_groups_multiple_transactions_and_drops_blank_rows():
    rows = extract_expense_rows(
        [
            "微信支付",
            "2026-03-29 18:21",
            "星巴克咖啡",
            "￥32.00",
            "支付宝",
            "2026-03-30 09:15",
            "便利店",
            "￥8.50",
            "微信支付",
            "支付成功",
        ]
    )

    assert rows == [
        ExpenseRow(date="2026-03-29", merchant_item="星巴克咖啡", amount="32.00"),
        ExpenseRow(date="2026-03-30", merchant_item="便利店", amount="8.50"),
    ]


def test_extract_expense_rows_keeps_merchantless_follow_up_separate():
    rows = extract_expense_rows(
        [
            "微信支付",
            "2026-03-29 18:21",
            "星巴克咖啡",
            "￥32.00",
            "支付宝",
            "2026-03-30 09:15",
            "￥8.50",
        ]
    )

    assert rows == [
        ExpenseRow(date="2026-03-29", merchant_item="星巴克咖啡", amount="32.00"),
        ExpenseRow(date="2026-03-30", merchant_item="", amount="8.50"),
    ]


def test_extract_expense_rows_keeps_date_only_prefix_merchantless_follow_up_separate():
    rows = extract_expense_rows(
        [
            "微信支付",
            "2026-03-29 18:21",
            "星巴克咖啡",
            "￥32.00",
            "2026-03-30 09:15",
            "￥8.50",
        ]
    )

    assert rows == [
        ExpenseRow(date="2026-03-29", merchant_item="星巴克咖啡", amount="32.00"),
        ExpenseRow(date="2026-03-30", merchant_item="", amount="8.50"),
    ]


def test_extract_expense_rows_splits_date_only_follow_up_after_dateless_amount_row():
    rows = extract_expense_rows(
        [
            "星巴克咖啡",
            "￥32.00",
            "2026-03-30 09:15",
            "￥8.50",
        ]
    )

    assert rows == [
        ExpenseRow(date="", merchant_item="星巴克咖啡", amount="32.00"),
        ExpenseRow(date="2026-03-30", merchant_item="", amount="8.50"),
    ]


def test_extract_expense_rows_splits_date_only_follow_up_after_negative_dateless_amount_row():
    rows = extract_expense_rows(
        [
            "滴滴出行",
            "-28.00",
            "2026-03-30 09:15",
            "￥8.50",
        ]
    )

    assert rows == [
        ExpenseRow(date="", merchant_item="滴滴出行", amount="28.00"),
        ExpenseRow(date="2026-03-30", merchant_item="", amount="8.50"),
    ]


@pytest.mark.parametrize("follow_up_date", ["3/30", "3.30"])
def test_extract_expense_rows_splits_separator_date_only_follow_up_after_negative_dateless_amount_row(
    follow_up_date,
):
    rows = extract_expense_rows(
        [
            "滴滴出行",
            "-28.00",
            follow_up_date,
            "￥8.50",
        ]
    )

    assert rows == [
        ExpenseRow(date="", merchant_item="滴滴出行", amount="28.00"),
        ExpenseRow(date="03-30", merchant_item="", amount="8.50"),
    ]


@pytest.mark.parametrize(
    "follow_up_date",
    ["3月30日 09:15", "3/30 09:15", "3.30 09:15"],
)
def test_extract_expense_rows_splits_month_day_follow_up_after_negative_dateless_amount_row(
    follow_up_date,
):
    rows = extract_expense_rows(
        [
            "滴滴出行",
            "-28.00",
            follow_up_date,
            "￥8.50",
        ]
    )

    assert rows == [
        ExpenseRow(date="", merchant_item="滴滴出行", amount="28.00"),
        ExpenseRow(date="03-30", merchant_item="", amount="8.50"),
    ]


def test_extract_expense_rows_keeps_split_merchant_label_follow_up_separate():
    rows = extract_expense_rows(
        [
            "微信支付",
            "2026-03-29 18:21",
            "星巴克咖啡",
            "￥32.00",
            "商户",
            "名称",
            "￥8.50",
        ]
    )

    assert rows == [
        ExpenseRow(date="2026-03-29", merchant_item="星巴克咖啡", amount="32.00"),
        ExpenseRow(date="", merchant_item="", amount="8.50"),
    ]


def test_extract_expense_rows_keeps_multiple_amount_lines_in_one_transaction():
    rows = extract_expense_rows(
        [
            "滴滴出行",
            "-28.00",
            "3月28日11:44",
            "31.00",
            "扫二维码付款-给早餐",
            "3月29日08:42",
            "-5.00",
        ]
    )

    assert rows == [
        ExpenseRow(date="03-28", merchant_item="滴滴出行", amount="28.00"),
        ExpenseRow(
            date="03-29",
            merchant_item="扫二维码付款-给早餐",
            amount="5.00",
        ),
    ]


def test_extract_expense_rows_drops_date_only_trailing_fragments():
    rows = extract_expense_rows(
        [
            "微信支付",
            "2026-03-29 18:21",
            "支付成功",
        ]
    )

    assert rows == []


def test_parse_expense_row_supports_dot_delimited_month_day_date_with_time():
    row = parse_expense_row(
        [
            "3.29 08:42",
            "星巴克咖啡",
            "￥32.00",
        ]
    )

    assert row.date == "03-29"


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

    assert row.date == "02-29"


def test_extract_date_does_not_treat_plain_decimal_as_month_day():
    assert parser_module._extract_date(["1.23"]) == ""


def test_extract_date_does_not_treat_ambiguous_slash_token_as_month_day():
    assert parser_module._extract_date(["11/12"]) == ""


def test_extract_date_does_not_treat_embedded_slash_token_with_time_as_month_day():
    assert parser_module._extract_date(["订单3/29 08:42"]) == ""


def test_extract_date_does_not_treat_embedded_dot_token_with_time_as_month_day():
    assert parser_module._extract_date(["备注 v3.29 08:42"]) == ""


def test_extract_date_does_not_treat_alpha_suffixed_slash_token_with_time_as_month_day():
    assert parser_module._extract_date(["3/29abc 08:42"]) == ""


def test_extract_date_does_not_treat_embedded_chinese_month_day_inside_text():
    assert parser_module._extract_date(["购买3月29日活动门票"]) == ""


def test_extract_date_does_not_treat_embedded_chinese_month_day_with_time():
    assert parser_module._extract_date(["订单3月29日 08:42"]) == ""


def test_extract_date_does_not_treat_separated_slash_token_and_time_as_month_day():
    assert parser_module._extract_date(["版本 3/29 更新于 08:42"]) == ""


def test_extract_date_does_not_treat_separated_dot_token_and_time_as_month_day():
    assert parser_module._extract_date(["3/29 note 08:42"]) == ""
