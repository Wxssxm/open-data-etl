"""Application configuration."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    data_raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    warehouse_dir: Path = PROJECT_ROOT / "data" / "warehouse"
    sample_csv: Path = PROJECT_ROOT / "data" / "sample" / "dvf_sample.csv"

    dvf_base_url: str = "https://files.data.gouv.fr/geo-dvf/latest/csv"
    dvf_year: int = Field(default=2023, ge=2014, le=2099)
    dvf_departement: str = "75"

    log_level: str = "INFO"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        configure_logging(_settings.log_level)
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None


def configure_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(sys.stderr, level=level.upper(), format="{time:HH:mm:ss} | {level: <8} | {message}")
