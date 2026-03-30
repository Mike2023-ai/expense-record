"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path


APP_DATA_DIR = Path.home() / ".expense-screenshot-tool"
DEFAULT_EXCEL_PATH = APP_DATA_DIR / "expenses.xlsx"


def resolve_excel_path() -> Path:
    override = os.environ.get("EXPENSE_RECORD_EXCEL_PATH")
    if override:
        return Path(override)
    return DEFAULT_EXCEL_PATH


class Config:
    SECRET_KEY = "dev"
    EXCEL_PATH = resolve_excel_path()


class TestConfig(Config):
    TESTING = True
