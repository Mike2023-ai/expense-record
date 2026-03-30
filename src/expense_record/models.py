from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExpenseRow:
    date: str = ""
    merchant_item: str = ""
    amount: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "merchant_item": self.merchant_item,
            "amount": self.amount,
        }
