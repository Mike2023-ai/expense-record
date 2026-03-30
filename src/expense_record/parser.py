from __future__ import annotations

import re
from collections.abc import Iterable

from expense_record.models import ExpenseRow


DATE_PATTERNS = (
    re.compile(r"(?P<date>\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"),
    re.compile(r"(?P<date>\d{4}年\d{1,2}月\d{1,2}日)"),
)
TIME_SUFFIX_RE = re.compile(r"\s+\d{1,2}:\d{2}(?::\d{2})?")
AMOUNT_RE = re.compile(r"(?:￥|¥|CNY\s*)?(?P<amount>-?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)")
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


def parse_expense_row(text_lines: str | Iterable[str]) -> ExpenseRow:
    lines = _normalize_lines(text_lines)
    date = _extract_date(lines)
    amount = _extract_amount(lines)
    merchant_item = _extract_merchant_item(lines, date=date, amount=amount)
    return ExpenseRow(date=date, merchant_item=merchant_item, amount=amount)


def _normalize_lines(text_lines: str | Iterable[str]) -> list[str]:
    if isinstance(text_lines, str):
        candidates = text_lines.splitlines()
    else:
        candidates = list(text_lines)
    return [line.strip() for line in candidates if line and line.strip()]


def _extract_date(lines: list[str]) -> str:
    for line in lines:
        for pattern in DATE_PATTERNS:
            match = pattern.search(line)
            if match:
                return _canonicalize_date(match.group("date"))
    return ""


def _canonicalize_date(raw_date: str) -> str:
    cleaned = raw_date.replace("年", "-").replace("月", "-").replace("日", "")
    cleaned = cleaned.replace("/", "-").replace(".", "-")
    parts = cleaned.split("-")
    if len(parts) != 3:
        return cleaned
    year, month, day = parts
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _extract_amount(lines: list[str]) -> str:
    for line in reversed(lines):
        if _looks_like_date_or_time(line):
            continue
        match = AMOUNT_RE.search(line.replace(",", ""))
        if match:
            return match.group("amount")
    return ""


def _extract_merchant_item(lines: list[str], *, date: str, amount: str) -> str:
    for line in lines:
        if line == date or line == amount:
            continue
        if _looks_like_date_or_time(line) or _looks_like_amount_line(line):
            continue
        if _contains_payment_noise(line):
            continue
        if _contains_merchandise_signal(line):
            return line
    return ""


def _looks_like_date_or_time(line: str) -> bool:
    return bool(any(pattern.search(line) for pattern in DATE_PATTERNS) or TIME_SUFFIX_RE.search(line))


def _looks_like_amount_line(line: str) -> bool:
    return bool(AMOUNT_RE.search(line.replace(",", "")))


def _contains_payment_noise(line: str) -> bool:
    return any(token in line for token in PAYMENT_NOISE)


def _contains_merchandise_signal(line: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in line) or any(char.isalnum() for char in line)
