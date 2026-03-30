"""Application configuration."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_EXCEL_PATH = BASE_DIR / "data" / "expenses.xlsx"


class Config:
    SECRET_KEY = "dev"
    EXCEL_PATH = DEFAULT_EXCEL_PATH


class TestConfig(Config):
    TESTING = True
