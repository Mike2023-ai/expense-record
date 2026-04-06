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


def test_detect_statement_source_rejects_malformed_xlsx_bytes():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        detect_statement_source("wechat.xlsx", b"not a zip archive")


def test_detect_statement_source_rejects_malformed_csv_bytes():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        detect_statement_source("alipay.csv", b"\xff\xfe\x00\x00")


def test_detect_statement_source_rejects_wechat_missing_source_marker_with_valid_full_header():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        detect_statement_source("wechat.xlsx", _wechat_missing_marker_fixture_bytes())


def test_detect_statement_source_rejects_alipay_missing_source_marker_with_valid_full_header():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        detect_statement_source("alipay.csv", _alipay_missing_marker_fixture_bytes())


def test_detect_statement_source_rejects_wechat_generic_marker_with_valid_full_header():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        detect_statement_source("wechat.xlsx", _wechat_generic_marker_fixture_bytes())


def test_detect_statement_source_rejects_alipay_generic_marker_with_valid_full_header():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        detect_statement_source("alipay.csv", _alipay_generic_marker_fixture_bytes())


def test_detect_statement_source_rejects_wechat_marker_with_header_subset_layout():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        detect_statement_source("wechat.xlsx", _wechat_marker_subset_fixture_bytes())


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


def test_import_statement_rows_rejects_malformed_xlsx_bytes():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        import_statement_rows("wechat.xlsx", b"not a zip archive")


def test_import_statement_rows_rejects_malformed_csv_bytes():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        import_statement_rows("alipay.csv", b"\xff\xfe\x00\x00")


def test_import_statement_rows_rejects_wechat_missing_source_marker_with_valid_full_header():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        import_statement_rows("wechat.xlsx", _wechat_missing_marker_fixture_bytes())


def test_import_statement_rows_rejects_alipay_missing_source_marker_with_valid_full_header():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        import_statement_rows("alipay.csv", _alipay_missing_marker_fixture_bytes())


def test_import_statement_rows_rejects_wechat_generic_marker_with_valid_full_header():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        import_statement_rows("wechat.xlsx", _wechat_generic_marker_fixture_bytes())


def test_import_statement_rows_rejects_alipay_generic_marker_with_valid_full_header():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        import_statement_rows("alipay.csv", _alipay_generic_marker_fixture_bytes())


def test_import_statement_rows_rejects_wechat_marker_with_header_subset_layout():
    with pytest.raises(UnsupportedStatementFileError, match="Unsupported or ambiguous statement file."):
        import_statement_rows("wechat.xlsx", _wechat_marker_subset_fixture_bytes())


def _wechat_fixture_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "微信账单"
    worksheet.append(["微信支付账单明细", "2026-04-06"])
    worksheet.append(["账单说明", "微信支付账单明细"])
    worksheet.append([])
    worksheet.append(["交易时间", "交易类型", "交易对方", "商品说明", "收/支", "金额(元)"])
    worksheet.append([46110.78055555555, "支付", "叫了个炸鸡", "晚餐", "支出", 26.5])
    worksheet.append([46110.77847222222, "支付", "商户_沈菊", "早餐", "支出", 10])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _wechat_missing_marker_fixture_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "微信账单"
    worksheet.append(["导出时间", "2026-04-06"])
    worksheet.append(["账单说明", "普通导出"])
    worksheet.append([])
    worksheet.append(["交易时间", "交易类型", "交易对方", "商品说明", "收/支", "金额(元)"])
    worksheet.append([46110.78055555555, "支付", "叫了个炸鸡", "晚餐", "支出", 26.5])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _wechat_generic_marker_fixture_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "微信账单"
    worksheet.append(["微信账单", "2026-04-06"])
    worksheet.append(["账单说明", "微信导出"])
    worksheet.append([])
    worksheet.append(["交易时间", "交易类型", "交易对方", "商品说明", "收/支", "金额(元)"])
    worksheet.append([46110.78055555555, "支付", "叫了个炸鸡", "晚餐", "支出", 26.5])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _wechat_marker_subset_fixture_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "微信账单"
    worksheet.append(["微信支付账单明细", "2026-04-06"])
    worksheet.append(["账单说明", "微信支付账单明细"])
    worksheet.append([])
    worksheet.append(["交易时间", "交易对方", "收/支", "金额(元)"])
    worksheet.append([46110.78055555555, "叫了个炸鸡", "支出", 26.5])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _alipay_fixture_bytes() -> bytes:
    return (
        "支付宝支付科技有限公司\n"
        "账单说明,支付宝账户\n"
        "交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易订单号,商家订单号,备注\n"
        "2026-04-03 18:40:31,消费,淘宝闪购,支付宝账户,外卖,支出,25.4,余额宝,成功,202604030001,202604030001A,外卖\n"
        "2026-04-05 04:08:45,理财,中欧基金管理有限公司,支付宝账户,基金,不计收支,0.02,余额宝,成功,202604050001,202604050001A,基金\n"
    ).encode("gb18030")


def _alipay_missing_marker_fixture_bytes() -> bytes:
    return (
        "账单说明,电子账单\n"
        "收支明细导出,2026-04-06\n"
        "交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易订单号,商家订单号,备注\n"
        "2026-04-03 18:40:31,消费,淘宝闪购,支付宝账户,外卖,支出,25.4,余额宝,成功,202604030001,202604030001A,外卖\n"
    ).encode("gb18030")


def _alipay_generic_marker_fixture_bytes() -> bytes:
    return (
        "支付宝账单\n"
        "账单说明,支付宝导出\n"
        "交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易订单号,商家订单号,备注\n"
        "2026-04-03 18:40:31,消费,淘宝闪购,支付宝账户,外卖,支出,25.4,余额宝,成功,202604030001,202604030001A,外卖\n"
    ).encode("gb18030")
