"""Pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = REPO_ROOT / "data" / "sample" / "dvf_sample.csv"


@pytest.fixture(scope="session")
def sample_csv() -> Path:
    if not SAMPLE_CSV.exists():
        pytest.skip(f"sample missing — run scripts/generate_sample.py ({SAMPLE_CSV})")
    return SAMPLE_CSV
