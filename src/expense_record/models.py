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
