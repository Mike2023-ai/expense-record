from expense_record.dashboard import (
    build_asset_trend,
    build_category_expense_summary,
    build_member_category_summary,
    build_monthly_cash_flow_summary,
)
from expense_record.models import AssetSnapshot, LedgerEntry


def test_build_category_expense_summary_groups_negative_expenses_by_category():
    rows = [
        LedgerEntry(
            date="2026-04-01",
            description="Lunch",
            amount="-26.50",
            direction="expense",
            category="food",
            member="Mike",
            source="manual",
            entry_type="expense",
            note="",
        ),
        LedgerEntry(
            date="2026-04-02",
            description="Dinner",
            amount="-10.00",
            direction="expense",
            category="food",
            member="Lucy",
            source="manual",
            entry_type="expense",
            note="",
        ),
        LedgerEntry(
            date="2026-04-03",
            description="Rent",
            amount="-1500.00",
            direction="expense",
            category="rent",
            member="Mike",
            source="manual",
            entry_type="expense",
            note="",
        ),
        LedgerEntry(
            date="2026-04-04",
            description="Salary",
            amount="+5000.00",
            direction="income",
            category="salary",
            member="Mike",
            source="manual",
            entry_type="income",
            note="",
        ),
    ]

    assert build_category_expense_summary(rows) == [
        {"category": "food", "amount": "36.50"},
        {"category": "rent", "amount": "1500.00"},
    ]


def test_build_member_category_summary_groups_by_member_and_category():
    rows = [
        LedgerEntry(
            date="2026-04-01",
            description="Lunch",
            amount="-26.50",
            direction="expense",
            category="food",
            member="Mike",
            source="manual",
            entry_type="expense",
            note="",
        ),
        LedgerEntry(
            date="2026-04-02",
            description="Dinner",
            amount="-10.00",
            direction="expense",
            category="food",
            member="Lucy",
            source="manual",
            entry_type="expense",
            note="",
        ),
        LedgerEntry(
            date="2026-04-03",
            description="Commute",
            amount="-8.00",
            direction="expense",
            category="commute",
            member="Mike",
            source="manual",
            entry_type="expense",
            note="",
        ),
    ]

    assert build_member_category_summary(rows) == [
        {"member": "Lucy", "category": "food", "amount": "10.00"},
        {"member": "Mike", "category": "commute", "amount": "8.00"},
        {"member": "Mike", "category": "food", "amount": "26.50"},
    ]


def test_build_monthly_cash_flow_summary_returns_income_expense_and_net():
    rows = [
        LedgerEntry(
            date="2026-04-01",
            description="Salary",
            amount="+5000.00",
            direction="income",
            category="salary",
            member="Mike",
            source="manual",
            entry_type="income",
            note="",
        ),
        LedgerEntry(
            date="2026-04-02",
            description="Rent",
            amount="-1500.00",
            direction="expense",
            category="rent",
            member="Mike",
            source="manual",
            entry_type="expense",
            note="",
        ),
        LedgerEntry(
            date="2026-05-01",
            description="Bonus",
            amount="+800.00",
            direction="income",
            category="bonus",
            member="Mike",
            source="manual",
            entry_type="income",
            note="",
        ),
    ]

    assert build_monthly_cash_flow_summary(rows) == [
        {
            "month": "2026-04",
            "income_total": "5000.00",
            "expense_total": "1500.00",
            "net_total": "3500.00",
        },
        {
            "month": "2026-05",
            "income_total": "800.00",
            "expense_total": "0.00",
            "net_total": "800.00",
        },
    ]


def test_build_asset_trend_returns_snapshot_values_by_month():
    snapshots = [
        AssetSnapshot(
            date="2026-04-30",
            cash_or_balance_total="20000.00",
            stock_total_value="150000.00",
            note="April",
        ),
        AssetSnapshot(
            date="2026-05-31",
            cash_or_balance_total="21000.00",
            stock_total_value="152500.00",
            note="May",
        ),
    ]

    assert build_asset_trend(snapshots) == [
        {
            "month": "2026-04",
            "cash_or_balance_total": "20000.00",
            "stock_total_value": "150000.00",
            "total_assets": "170000.00",
        },
        {
            "month": "2026-05",
            "cash_or_balance_total": "21000.00",
            "stock_total_value": "152500.00",
            "total_assets": "173500.00",
        },
    ]
