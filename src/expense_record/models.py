from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExpenseRow:
    date: str = ""
    merchant_item: str = ""
    amount: str = ""
    direction: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "merchant_item": self.merchant_item,
            "amount": self.amount,
            "direction": self.direction,
        }


@dataclass(slots=True)
class StatementImportRow:
    transaction_time: str = ""
    counterparty: str = ""
    direction: str = ""
    amount: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "transaction_time": self.transaction_time,
            "counterparty": self.counterparty,
            "direction": self.direction,
            "amount": self.amount,
        }

    def to_ledger_entry(
        self,
        *,
        amount: str,
        direction: str,
        source: str,
        entry_type: str,
    ) -> LedgerEntry:
        return LedgerEntry(
            date=self.transaction_time,
            description=self.counterparty,
            amount=amount,
            direction=direction,
            category="",
            member="",
            source=source,
            entry_type=entry_type,
            note="",
        )


@dataclass(slots=True)
class LedgerEntry:
    """LedgerEntry represents a family ledger row.\n\ndirection stores the cash flow direction, while entry_type stores the\nbusiness classification of the row."""

    date: str = ""
    description: str = ""
    amount: str = ""
    direction: str = ""
    category: str = ""
    member: str = ""
    source: str = ""
    entry_type: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "description": self.description,
            "amount": self.amount,
            "direction": self.direction,
            "category": self.category,
            "member": self.member,
            "source": self.source,
            "entry_type": self.entry_type,
            "note": self.note,
        }


@dataclass(slots=True)
class CategoryRecord:
    date: str = ""
    category: str = ""
    amount: str = ""
    direction: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "category": self.category,
            "amount": self.amount,
            "direction": self.direction,
            "note": self.note,
        }


@dataclass(slots=True)
class MemberRecord:
    date: str = ""
    member: str = ""
    amount: str = ""
    direction: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "member": self.member,
            "amount": self.amount,
            "direction": self.direction,
            "note": self.note,
        }


@dataclass(slots=True)
class AssetSnapshot:
    date: str = ""
    cash_or_balance_total: str = ""
    stock_total_value: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "cash_or_balance_total": self.cash_or_balance_total,
            "stock_total_value": self.stock_total_value,
            "note": self.note,
        }


@dataclass(slots=True)
class StockRecord:
    date: str = ""
    stock_name: str = ""
    stock_quantity: str = ""
    stock_price: str = ""
    stock_total_value: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "stock_name": self.stock_name,
            "stock_quantity": self.stock_quantity,
            "stock_price": self.stock_price,
            "stock_total_value": self.stock_total_value,
            "note": self.note,
        }
