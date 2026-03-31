from __future__ import annotations

import re
from datetime import date
from collections.abc import Iterable

from expense_record.models import ExpenseRow


DATE_PATTERNS = (
    re.compile(r"(?P<date>\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"),
    re.compile(r"(?P<date>\d{4}年\d{1,2}月\d{1,2}日)"),
)
MONTH_DAY_WITH_CHINESE_RE = re.compile(
    r"(?:^|[\s(（\[\{【<,，:：;；])"
    r"(?P<date>(?:0?[1-9]|1[0-2])月(?:0?[1-9]|[12]\d|3[01])日)"
    r"(?:\s*\d{1,2}:\d{2}(?::\d{2})?)?"
    r"(?=$|[\s)）\]\}】>,，。.!！？?])"
)
MONTH_DAY_WITH_SEPARATOR_RE = re.compile(
    r"(?:^|[\s(（\[\{【<,，:：;；])"
    r"(?P<date>(?:0?[1-9]|1[0-2])[/.](?:0?[1-9]|[12]\d|3[01]))"
    r"(?=$|[\s)）\]\}】>,，。.!！？?])"
)
MONTH_DAY_WITH_SEPARATOR_AND_TIME_RE = re.compile(
    r"(?:^|[\s(（\[\{【<,，:：;；])"
    r"(?P<date>(?:0?[1-9]|1[0-2])[/.](?:0?[1-9]|[12]\d|3[01]))"
    r"\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?)"
    r"(?=$|[\s)）\]\}】>,，。.!！？?])"
)
TIME_ONLY_RE = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
AMOUNT_BODY_RE = re.compile(r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?")
LABELLED_AMOUNT_RE = re.compile(
    r"^(?:金额|付款|支付|实付|消费|支出|合计|总计)\s*[:：]?\s*(?:￥|¥|CNY\s*)?(?P<amount>-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)"
    r"(?:元)?$"
)
PAYMENT_NOISE = (
    "微信支付",
    "支付宝",
    "支付成功",
    "付款成功",
    "交易成功",
    "交易明细",
    "收款",
    "收钱吧",
    "余额",
    "订单",
    "账单",
    "零钱",
)
MERCHANT_LABELS = (
    "商户名称",
    "商家名称",
    "商户",
    "商家",
    "门店名称",
    "交易对象",
)
MERCHANT_METADATA_PREFIXES = (
    "交易单号",
    "尾号",
    "付款方式",
    "支付方式",
    "卡号",
    "银行卡号",
    "流水号",
    "订单号",
)


def parse_expense_row(text_lines: str | Iterable[str]) -> ExpenseRow:
    lines = _normalize_lines(text_lines)
    date = _extract_date(lines)
    amount = _extract_amount(lines)
    merchant_item = _extract_merchant_item(lines, date=date, amount=amount)
    return ExpenseRow(date=date, merchant_item=merchant_item, amount=amount)


def extract_expense_rows(text_lines: str | Iterable[str]) -> list[ExpenseRow]:
    lines = _normalize_lines(text_lines)
    return [
        row
        for row in (
            parse_expense_row(group) for group in _group_expense_lines(lines)
        )
        if row.merchant_item or row.amount
    ]


def _normalize_lines(text_lines: str | Iterable[str]) -> list[str]:
    if isinstance(text_lines, str):
        candidates = text_lines.splitlines()
    else:
        candidates = list(text_lines)
    return [line.strip() for line in candidates if line and line.strip()]


def _group_expense_lines(lines: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current_group: list[str] = []
    pending_prefix: list[str] = []
    has_transaction_content = False
    for line in lines:
        if pending_prefix and not _is_preamble_line(line) and not _looks_like_merchant_like_line(line):
            if _looks_like_amount_line(line) and _pending_prefix_starts_new_transaction(
                current_group, pending_prefix
            ):
                if current_group:
                    groups.append(current_group)
                current_group = pending_prefix
                pending_prefix = []
                has_transaction_content = False
            else:
                current_group.extend(pending_prefix)
                pending_prefix = []
        if current_group and has_transaction_content and _looks_like_merchant_like_line(
            line
        ):
            groups.append(current_group)
            current_group = pending_prefix
            pending_prefix = []
            has_transaction_content = False
        if has_transaction_content and _is_preamble_line(line):
            pending_prefix.append(line)
            continue
        current_group.append(line)
        if _looks_like_merchant_like_line(line) or _looks_like_amount_line(line):
            has_transaction_content = True
    if pending_prefix:
        current_group.extend(pending_prefix)
    if current_group:
        groups.append(current_group)
    return groups


def _extract_date(lines: list[str]) -> str:
    for line in lines:
        if date_text := _match_date_text(line):
            return _canonicalize_date(date_text)
    return ""


def _match_date_text(line: str) -> str:
    for pattern in DATE_PATTERNS:
        match = pattern.search(line)
        if match:
            return match.group("date")
    match = MONTH_DAY_WITH_CHINESE_RE.search(line)
    if match:
        return match.group("date")
    if match := MONTH_DAY_WITH_SEPARATOR_AND_TIME_RE.search(line):
        return match.group("date")
    return ""


def _canonicalize_date(raw_date: str) -> str:
    cleaned = raw_date.replace("年", "-").replace("月", "-").replace("日", "")
    cleaned = cleaned.replace("/", "-").replace(".", "-")
    parts = cleaned.split("-")
    if len(parts) == 2:
        month, day = parts
        return _canonicalize_month_day(int(month), int(day))
    if len(parts) != 3:
        return cleaned
    year, month, day = parts
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _canonicalize_month_day(month: int, day: int) -> str:
    year = date.today().year
    try:
        date(year, month, day)
    except ValueError:
        return ""
    return f"{month:02d}-{day:02d}"


def _extract_amount(lines: list[str]) -> str:
    candidates: list[tuple[str, bool]] = []
    for line in lines:
        if _looks_like_date_or_time(line):
            continue
        if candidate := _match_amount_candidate(line):
            candidates.append(candidate)
    for amount, is_negative in reversed(candidates):
        if is_negative:
            return amount
    if candidates:
        return candidates[-1][0]
    return ""


def _extract_merchant_item(lines: list[str], *, date: str, amount: str) -> str:
    for index, line in enumerate(lines):
        if line == date or line == amount:
            continue
        if _looks_like_date_or_time(line) or _looks_like_amount_line(line):
            continue
        if _contains_payment_noise(line):
            continue
        if _contains_merchant_metadata(line):
            continue
        if _is_split_merchant_label_piece(lines, index):
            continue
        if _contains_merchandise_signal(line):
            merchant_item = _strip_merchant_label(line)
            if merchant_item:
                return merchant_item
    return ""


def _looks_like_date_or_time(line: str) -> bool:
    return bool(_match_date_text(line) or TIME_ONLY_RE.fullmatch(line))


def _looks_like_amount_line(line: str) -> bool:
    return _match_amount(line) != ""


def _contains_payment_noise(line: str) -> bool:
    return any(token in line for token in PAYMENT_NOISE)


def _contains_merchant_metadata(line: str) -> bool:
    return any(line.startswith(prefix) for prefix in MERCHANT_METADATA_PREFIXES)


def _contains_merchandise_signal(line: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in line) or any(char.isalnum() for char in line)


def _is_preamble_line(line: str) -> bool:
    return (
        _looks_like_date_or_time(line)
        or _contains_payment_noise(line)
        or _contains_merchant_metadata(line)
        or line in {"商户", "商家", "名称"}
    )


def _pending_prefix_starts_new_transaction(
    current_group: list[str], lines: list[str]
) -> bool:
    current_group_has_positive_amount = _group_contains_positive_amount_line(current_group)
    return any(
        (_looks_like_date_or_time(line) and current_group_has_positive_amount)
        or _contains_payment_noise(line)
        or _contains_merchant_metadata(line)
        for line in lines
    ) or any(_is_split_merchant_label_piece(lines, index) for index in range(len(lines)))


def _group_contains_positive_amount_line(lines: list[str]) -> bool:
    return any(
        (candidate := _match_amount_candidate(line)) is not None and not candidate[1]
        for line in lines
    )


def _group_contains_date_or_time(lines: list[str]) -> bool:
    return any(_looks_like_date_or_time(line) for line in lines)


def _looks_like_merchant_like_line(line: str) -> bool:
    return (
        not _looks_like_date_or_time(line)
        and not _contains_payment_noise(line)
        and not _contains_merchant_metadata(line)
        and line not in {"商户", "商家", "名称"}
        and not _looks_like_amount_line(line)
        and _contains_merchandise_signal(line)
    )


def _match_amount(line: str) -> str:
    if candidate := _parse_amount_candidate(line):
        return candidate[0]
    return ""


def _match_amount_candidate(line: str) -> tuple[str, bool] | None:
    return _parse_amount_candidate(line)


def _parse_amount_candidate(line: str) -> tuple[str, bool] | None:
    cleaned = _clean_amount_text(line)
    if match := LABELLED_AMOUNT_RE.fullmatch(cleaned):
        amount = match.group("amount")
        return amount.removeprefix("-"), amount.startswith("-")
    if AMOUNT_BODY_RE.fullmatch(cleaned):
        return cleaned.removeprefix("-"), cleaned.startswith("-")
    if cleaned.endswith("元"):
        amount = cleaned.removesuffix("元").strip()
        if AMOUNT_BODY_RE.fullmatch(amount):
            return amount.removeprefix("-"), amount.startswith("-")
    return None


def _clean_amount_text(line: str) -> str:
    cleaned = line.replace(",", "").strip()
    cleaned = cleaned.removeprefix("￥").removeprefix("¥")
    cleaned = cleaned.removeprefix("CNY").strip()
    return cleaned


def _strip_merchant_label(line: str) -> str:
    for label in MERCHANT_LABELS:
        if line.startswith(label):
            return line[len(label) :].strip(" ：:，,")
    return line


def _is_split_merchant_label_piece(lines: list[str], index: int) -> bool:
    line = lines[index]
    if line in {"商户", "商家"} and index + 1 < len(lines) and lines[index + 1] == "名称":
        return True
    if line == "名称" and index > 0 and lines[index - 1] in {"商户", "商家"}:
        return True
    return False
