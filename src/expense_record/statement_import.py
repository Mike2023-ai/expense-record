from __future__ import annotations

from csv import reader as csv_reader
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from io import BytesIO, StringIO
import re
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from expense_record.models import StatementImportRow


class UnsupportedStatementFileError(ValueError):
    pass


WECHAT_HEADER_ROW = ("交易时间", "交易类型", "交易对方", "商品说明", "收/支", "金额(元)")
ALIPAY_HEADER_ROW = (
    "交易时间",
    "交易分类",
    "交易对方",
    "对方账号",
    "商品说明",
    "收/支",
    "金额",
    "收/付款方式",
    "交易状态",
    "交易订单号",
    "商家订单号",
    "备注",
)
WECHAT_SOURCE_MARKERS = ("微信支付账单明细",)
ALIPAY_SOURCE_MARKERS = ("电子客户回单", "电子回单", "支付宝支付科技有限公司")

XML_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XML_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
PARSE_ERROR_TYPES = (UnicodeDecodeError, BadZipFile, ET.ParseError, InvalidOperation, KeyError, IndexError, ValueError)
WECHAT_TIME_CANDIDATE_RE = re.compile(
    r"^(?:"
    r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"
    r"(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"
    r"|\d+(?:\.\d+)?"
    r")$"
)
ALIPAY_TIME_CANDIDATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?$")


def detect_statement_source(filename: str, raw_bytes: bytes) -> str:
    try:
        lowered = filename.lower()
        if lowered.endswith(".xlsx"):
            _detect_wechat_xlsx_layout(raw_bytes)
            return "wechat"
        if lowered.endswith(".csv"):
            _detect_alipay_csv_layout(raw_bytes)
            return "alipay"
    except UnsupportedStatementFileError:
        raise
    except PARSE_ERROR_TYPES:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")
    raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")


def import_statement_rows(filename: str, raw_bytes: bytes) -> list[StatementImportRow]:
    try:
        source = detect_statement_source(filename, raw_bytes)
        if source == "wechat":
            return _import_wechat_rows(raw_bytes)
        if source == "alipay":
            return _import_alipay_rows(raw_bytes)
    except UnsupportedStatementFileError:
        raise
    except PARSE_ERROR_TYPES:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")
    raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")


def _import_wechat_rows(raw_bytes: bytes) -> list[StatementImportRow]:
    sheet_rows = _read_xlsx_rows(raw_bytes)
    header_index = _find_header_row_index(sheet_rows, WECHAT_HEADER_ROW)
    rows: list[StatementImportRow] = []
    for row in sheet_rows[header_index + 1 :]:
        normalized_row = _normalize_trailing_empty_cells(row)
        if _is_empty_row(normalized_row):
            continue
        if len(normalized_row) < len(WECHAT_HEADER_ROW):
            if _row_looks_like_wechat_transaction_candidate(normalized_row):
                raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")
            continue
        _require_exact_row_shape(normalized_row, len(WECHAT_HEADER_ROW))
        rows.append(
            StatementImportRow(
                transaction_time=_normalize_statement_time(normalized_row[0]),
                counterparty=normalized_row[2],
                direction=normalized_row[4],
                amount=_normalize_amount(normalized_row[5]),
            )
        )
    return rows


def _import_alipay_rows(raw_bytes: bytes) -> list[StatementImportRow]:
    csv_rows = _read_alipay_csv_rows(raw_bytes)
    header_index = _find_header_row_index(csv_rows, ALIPAY_HEADER_ROW)
    rows: list[StatementImportRow] = []
    for row in csv_rows[header_index + 1 :]:
        normalized_row = _normalize_trailing_empty_cells(row)
        if _is_empty_row(normalized_row):
            continue
        if len(normalized_row) < len(ALIPAY_HEADER_ROW):
            if _row_looks_like_alipay_transaction_candidate(normalized_row):
                raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")
            continue
        _require_row_shape_with_optional_trailing_empty(normalized_row, len(ALIPAY_HEADER_ROW))
        rows.append(
            StatementImportRow(
                transaction_time=_normalize_alipay_statement_time(normalized_row[0]),
                counterparty=normalized_row[2],
                direction=normalized_row[5],
                amount=_normalize_amount(normalized_row[6]),
            )
        )
    return rows


def _find_header_row_index(rows: list[list[str]], header_signature: tuple[str, ...]) -> int:
    for index, row in enumerate(rows):
        if _row_matches_signature(row, header_signature):
            return index
    raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")


def _row_matches_signature(row: list[str], signature: tuple[str, ...]) -> bool:
    return tuple(_normalize_trailing_empty_cells(row)) == signature


def _require_exact_row_shape(row: list[str], expected_length: int) -> None:
    if len(row) != expected_length:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")


def _require_row_shape_with_optional_trailing_empty(row: list[str], expected_length: int) -> None:
    if len(_normalize_trailing_empty_cells(row)) != expected_length:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")


def _normalize_trailing_empty_cells(row: list[str]) -> list[str]:
    normalized = list(row)
    while normalized and normalized[-1].strip() == "":
        normalized.pop()
    return [cell.strip() for cell in normalized]


def _is_empty_row(row: list[str]) -> bool:
    return not row or not any(cell.strip() for cell in row)


def _row_looks_like_wechat_transaction_candidate(row: list[str]) -> bool:
    return bool(row[0].strip()) and bool(WECHAT_TIME_CANDIDATE_RE.match(row[0].strip()))


def _row_looks_like_alipay_transaction_candidate(row: list[str]) -> bool:
    return bool(row[0].strip()) and bool(ALIPAY_TIME_CANDIDATE_RE.match(row[0].strip()))


def _normalize_statement_time(value: str) -> str:
    text = value.strip()
    if not text:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")
    if _looks_like_excel_serial(text):
        return _excel_serial_to_timestamp(text)
    return text


def _normalize_alipay_statement_time(value: str) -> str:
    text = value.strip()
    try:
        timestamp = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.") from exc
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _looks_like_excel_serial(value: str) -> bool:
    if value.count(":") > 0:
        return False
    try:
        Decimal(value)
    except Exception:
        return False
    return True


def _excel_serial_to_timestamp(value: str) -> str:
    serial = Decimal(value)
    base = datetime(1899, 12, 30)
    seconds = (serial * Decimal("86400")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    timestamp = base + timedelta(seconds=int(seconds))
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_amount(value: str) -> str:
    text = value.strip().replace("￥", "").replace("¥", "")
    amount = Decimal(text)
    normalized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(normalized, "f")


def _read_alipay_csv_rows(raw_bytes: bytes) -> list[list[str]]:
    try:
        decoded = raw_bytes.decode("gb18030")
    except UnicodeDecodeError as exc:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.") from exc
    return [row for row in csv_reader(StringIO(decoded))]


def _detect_wechat_xlsx_layout(raw_bytes: bytes) -> None:
    sheet_rows = _read_xlsx_rows(raw_bytes)
    header_index = _find_header_row_index(sheet_rows, WECHAT_HEADER_ROW)
    _require_source_marker(sheet_rows[:header_index], WECHAT_SOURCE_MARKERS)


def _detect_alipay_csv_layout(raw_bytes: bytes) -> None:
    csv_rows = _read_alipay_csv_rows(raw_bytes)
    header_index = _find_header_row_index(csv_rows, ALIPAY_HEADER_ROW)
    _require_source_marker(csv_rows[:header_index], ALIPAY_SOURCE_MARKERS)


def _require_source_marker(rows: list[list[str]], markers: tuple[str, ...]) -> None:
    haystack = "\n".join(" ".join(cell.strip() for cell in row if cell.strip()) for row in rows)
    if not haystack or not any(marker in haystack for marker in markers):
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")


def _read_xlsx_rows(raw_bytes: bytes) -> list[list[str]]:
    with ZipFile(BytesIO(raw_bytes)) as archive:
        shared_strings = _read_shared_strings(archive)
        workbook_path = _read_first_sheet_path(archive)
        worksheet_xml = archive.read(workbook_path)
    return _parse_worksheet_rows(worksheet_xml, shared_strings)


def _read_shared_strings(archive: ZipFile) -> list[str]:
    try:
        data = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(data)
    strings: list[str] = []
    for item in root.findall(f"{{{XML_MAIN_NS}}}si"):
        strings.append("".join(node.text or "" for node in item.iterfind(f".//{{{XML_MAIN_NS}}}t")))
    return strings


def _read_first_sheet_path(archive: ZipFile) -> str:
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    sheet = workbook_root.find(f".//{{{XML_MAIN_NS}}}sheet")
    if sheet is None:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")
    sheet_id = sheet.attrib.get(f"{{{XML_REL_NS}}}id")
    if not sheet_id:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")

    rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for rel in rels_root.findall(f"{{{XML_PKG_REL_NS}}}Relationship"):
        if rel.attrib.get("Id") == sheet_id:
            target = rel.attrib.get("Target")
            if not target:
                break
            if target.startswith("/"):
                return target.lstrip("/")
            return f"xl/{target}"
    raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")


def _parse_worksheet_rows(worksheet_xml: bytes, shared_strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(worksheet_xml)
    sheet_data = root.find(f"{{{XML_MAIN_NS}}}sheetData")
    if sheet_data is None:
        raise UnsupportedStatementFileError("Unsupported or ambiguous statement file.")

    rows: list[list[str]] = []
    for xml_row in sheet_data.findall(f"{{{XML_MAIN_NS}}}row"):
        cells: list[str] = []
        expected_column = 1
        for cell in xml_row.findall(f"{{{XML_MAIN_NS}}}c"):
            column_index = _column_index_from_ref(cell.attrib.get("r", ""))
            if column_index is None:
                column_index = expected_column
            while len(cells) < column_index - 1:
                cells.append("")
            cells.append(_read_cell_value(cell, shared_strings))
            expected_column = column_index + 1
        rows.append(cells)
    return rows


def _column_index_from_ref(reference: str) -> int | None:
    letters = "".join(character for character in reference if character.isalpha())
    if not letters:
        return None
    index = 0
    for character in letters:
        index = index * 26 + (ord(character.upper()) - ord("A") + 1)
    return index


def _read_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "s":
        value = cell.findtext(f"{{{XML_MAIN_NS}}}v", default="")
        if not value:
            return ""
        return shared_strings[int(value)]
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iterfind(f".//{{{XML_MAIN_NS}}}t"))
    if cell_type == "str":
        return cell.findtext(f"{{{XML_MAIN_NS}}}v", default="")
    return cell.findtext(f"{{{XML_MAIN_NS}}}v", default="")
