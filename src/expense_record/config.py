"""Application configuration."""

from pathlib import Path


APP_DATA_DIR = Path.home() / ".expense-screenshot-tool"
DEFAULT_EXCEL_PATH = APP_DATA_DIR / "expenses.xlsx"


class Config:
    SECRET_KEY = "dev"
    EXCEL_PATH = DEFAULT_EXCEL_PATH


class TestConfig(Config):
    TESTING = True
