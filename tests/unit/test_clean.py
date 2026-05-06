"""Tests for the clean module."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from dvf_etl.clean import scan_source
from dvf_etl.clean.transform import REQUIRED_COLUMNS, clean_to_dataframe


def test_scan_source_returns_lazyframe(sample_csv: Path) -> None:
    lazy = scan_source(sample_csv)
    assert isinstance(lazy, pl.LazyFrame)
    assert set(REQUIRED_COLUMNS) <= set(lazy.collect().columns)


def test_clean_drops_zero_valeur_fonciere(sample_csv: Path) -> None:
    cleaned = clean_to_dataframe(sample_csv)
    assert (cleaned["valeur_fonciere"] > 0).all()


def test_clean_residential_has_surface(sample_csv: Path) -> None:
    cleaned = clean_to_dataframe(sample_csv)
    residential = cleaned.filter(pl.col("type_local").is_in(["Maison", "Appartement"]))
    assert residential.filter(pl.col("surface_reelle_bati").is_null()).height == 0
    assert (residential["surface_reelle_bati"] > 0).all()


def test_clean_dedupes_on_natural_key(sample_csv: Path) -> None:
    cleaned = clean_to_dataframe(sample_csv)
    pairs = cleaned.select(["id_mutation", "numero_disposition"])
    assert pairs.is_unique().all()


def test_clean_derives_year_and_prix_m2(sample_csv: Path) -> None:
    cleaned = clean_to_dataframe(sample_csv)
    assert "year" in cleaned.columns
    assert "prix_m2" in cleaned.columns
    assert (cleaned["prix_m2"] > 0).all()


def test_clean_handles_missing_columns_gracefully(tmp_path: Path) -> None:
    """If a required column is missing in the source, scan_source raises."""
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n")
    with pytest.raises(pl.exceptions.PolarsError):
        scan_source(bad).collect()
