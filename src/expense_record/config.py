"""Application configuration."""

from __future__ import annotations

from importlib import metadata
import os
from pathlib import Path
import tomllib


APP_DATA_DIR = Path.home() / ".expense-screenshot-tool"
DEFAULT_EXCEL_PATH = APP_DATA_DIR / "expenses.xlsx"
DEFAULT_CATEGORIES = (
    "food",
    "cloth",
    "commute",
    "rent",
    "insurance",
    "operation fee",
    "company",
    "festival",
)


def resolve_excel_path() -> Path:
    override = os.environ.get("EXPENSE_RECORD_EXCEL_PATH")
    if override:
        return Path(override)
    return DEFAULT_EXCEL_PATH


def resolve_app_version() -> str:
    try:
        return metadata.version("expense-screenshot-tool")
    except metadata.PackageNotFoundError:
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        with pyproject_path.open("rb") as handle:
            return tomllib.load(handle)["project"]["version"]


class Config:
    SECRET_KEY = "dev"
    EXCEL_PATH = resolve_excel_path()
    APP_VERSION = resolve_app_version()


class TestConfig(Config):
    TESTING = True
