from __future__ import annotations

from decimal import Decimal

from expense_record.models import AssetSnapshot, LedgerEntry


def build_category_expense_summary(rows: list[LedgerEntry]) -> list[dict[str, str]]:
    totals: dict[str, Decimal] = {}
    for row in rows:
        if row.direction != "expense":
            continue
        amount = _absolute_amount(row.amount)
        if amount is None:
            continue
        totals[row.category] = totals.get(row.category, Decimal("0")) + amount

    return [
        {"category": category, "amount": _format_decimal(totals[category])}
        for category in sorted(totals)
    ]


def build_member_category_summary(rows: list[LedgerEntry]) -> list[dict[str, str]]:
    totals: dict[tuple[str, str], Decimal] = {}
    for row in rows:
        if row.direction != "expense":
            continue
        amount = _absolute_amount(row.amount)
        if amount is None:
            continue
        key = (row.member, row.category)
        totals[key] = totals.get(key, Decimal("0")) + amount

    return [
        {
            "member": member,
            "category": category,
            "amount": _format_decimal(totals[(member, category)]),
        }
        for member, category in sorted(totals)
    ]


def build_monthly_cash_flow_summary(rows: list[LedgerEntry]) -> list[dict[str, str]]:
    totals: dict[str, dict[str, Decimal]] = {}
    for row in rows:
        month = _month_key(row.date)
        amount = _signed_amount(row.amount)
        if month is None or amount is None:
            continue
        bucket = totals.setdefault(
            month,
            {"income_total": Decimal("0"), "expense_total": Decimal("0"), "net_total": Decimal("0")},
        )
        if amount >= 0:
            bucket["income_total"] += amount
        else:
            bucket["expense_total"] += abs(amount)
        bucket["net_total"] += amount

    return [
        {
            "month": month,
            "income_total": _format_decimal(totals[month]["income_total"]),
            "expense_total": _format_decimal(totals[month]["expense_total"]),
            "net_total": _format_decimal(totals[month]["net_total"]),
        }
        for month in sorted(totals)
    ]


def build_asset_trend(snapshots: list[AssetSnapshot]) -> list[dict[str, str]]:
    trend: list[dict[str, str]] = []
    for snapshot in sorted(snapshots, key=lambda item: item.date):
        month = _month_key(snapshot.date)
        if month is None:
            continue
        cash = _unsigned_amount(snapshot.cash_or_balance_total)
        stock = _unsigned_amount(snapshot.stock_total_value)
        if cash is None or stock is None:
            continue
        trend.append(
            {
                "month": month,
                "cash_or_balance_total": _format_decimal(cash),
                "stock_total_value": _format_decimal(stock),
                "total_assets": _format_decimal(cash + stock),
            }
        )
    return trend


def _month_key(date_text: str) -> str | None:
    text = (date_text or "").strip()
    if len(text) < 7:
        return None
    return text[:7]


def _signed_amount(value: str) -> Decimal | None:
    text = (value or "").strip()
    if not text:
        return None
    return Decimal(text)


def _absolute_amount(value: str) -> Decimal | None:
    amount = _signed_amount(value)
    if amount is None:
        return None
    return abs(amount)


def _unsigned_amount(value: str) -> Decimal | None:
    text = (value or "").strip()
    if not text:
        return None
    return Decimal(text)


def _format_decimal(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")
