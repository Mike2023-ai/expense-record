from __future__ import annotations

from io import BytesIO

import pytest
from openpyxl import Workbook

from expense_record.models import StatementImportRow
from expense_record.statement_import import (
    UnsupportedStatementFileError,
    detect_statement_source,
    import_statement_rows,
)


def test_detect_statement_source_identifies_wechat_xlsx_bytes():
    source = detect_statement_source("wechat.xlsx", _wechat_fixture_bytes())

    assert source == "wechat"


def test_detect_statement_source_identifies_alipay_csv_bytes():
    source = detect_statement_source("alipay.csv", _alipay_fixture_bytes())

    assert source == "alipay"


def test_import_statement_rows_normalizes_wechat_rows():
    rows = import_statement_rows("wechat.xlsx", _wechat_fixture_bytes())

    assert rows == [
        StatementImportRow(
            transaction_time="2026-03-29 18:44:00",
            counterparty="叫了个炸鸡",
            direction="支出",
            amount="26.50",
        ),
        StatementImportRow(
            transaction_time="2026-03-29 18:41:00",
            counterparty="商户_沈菊",
            direction="支出",
            amount="10.00",
        ),
    ]


def test_import_statement_rows_normalizes_alipay_rows():
    rows = import_statement_rows("alipay.csv", _alipay_fixture_bytes())

    assert rows == [
        StatementImportRow(
            transaction_time="2026-04-03 18:40:31",
            counterparty="淘宝闪购",
            direction="支出",
            amount="25.40",
        ),
        StatementImportRow(
            transaction_time="2026-04-05 04:08:45",
            counterparty="中欧基金管理有限公司",
            direction="不计收支",
            amount="0.02",
        ),
    ]


def test_import_statement_rows_rejects_unsupported_file():
    with pytest.raises(UnsupportedStatementFileError):
        import_statement_rows("notes.txt", b"not a statement")


def _wechat_fixture_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "微信账单"
    worksheet.append(["导出时间", "2026-04-06"])
    worksheet.append(["账单说明", "微信账单"])
    worksheet.append([])
    worksheet.append(["交易时间", "交易类型", "交易对方", "商品说明", "收/支", "金额(元)"])
    worksheet.append([46110.78055555555, "支付", "叫了个炸鸡", "晚餐", "支出", 26.5])
    worksheet.append([46110.77847222222, "支付", "商户_沈菊", "早餐", "支出", 10])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _alipay_fixture_bytes() -> bytes:
    return (
        "支付宝账单\n"
        "账单说明,支付宝账单\n"
        "交易时间,交易分类,交易对方,商品说明,资金状态,收/支,金额\n"
        "2026-04-03 18:40:31,消费,淘宝闪购,外卖,成功,支出,25.4\n"
        "2026-04-05 04:08:45,理财,中欧基金管理有限公司,基金,成功,不计收支,0.02\n"
    ).encode("gb18030")
