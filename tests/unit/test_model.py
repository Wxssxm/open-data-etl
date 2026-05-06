"""Tests for the model module."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from dvf_etl.clean import clean_to_dataframe
from dvf_etl.model import (
    build_dim_date,
    build_dim_location,
    build_dim_property_type,
    build_warehouse,
)


@pytest.fixture(scope="module")
def cleaned_sample(sample_csv: Path) -> pl.DataFrame:
    return clean_to_dataframe(sample_csv)


def test_dim_date_covers_full_range(cleaned_sample: pl.DataFrame) -> None:
    dim = build_dim_date(cleaned_sample)
    assert dim.height >= cleaned_sample["date_mutation"].n_unique()
    assert {"date_sk", "full_date", "year", "month", "is_weekend"} <= set(dim.columns)


def test_dim_date_sk_is_yyyymmdd(cleaned_sample: pl.DataFrame) -> None:
    dim = build_dim_date(cleaned_sample)
    sample = dim.row(0, named=True)
    expected = (
        sample["full_date"].year * 10000 + sample["full_date"].month * 100 + sample["full_date"].day
    )
    assert sample["date_sk"] == expected


def test_dim_location_unique_keys(cleaned_sample: pl.DataFrame) -> None:
    dim = build_dim_location(cleaned_sample)
    assert dim["location_sk"].is_unique().all()
    assert dim.select(["code_commune", "code_postal"]).is_unique().all()


def test_dim_property_type_residential_flag(cleaned_sample: pl.DataFrame) -> None:
    dim = build_dim_property_type(cleaned_sample)
    residential = dim.filter(pl.col("type_local").is_in(["Maison", "Appartement"]))
    assert residential["is_residential"].all()


def test_build_warehouse_returns_4_tables(sample_csv: Path) -> None:
    tables = build_warehouse(sample_csv)
    assert set(tables.keys()) == {
        "dim_date",
        "dim_location",
        "dim_property_type",
        "fact_transactions",
    }
    assert all(t.height > 0 for t in tables.values())
    assert {"date_sk", "location_sk", "property_type_sk"} <= set(
        tables["fact_transactions"].columns
    )


def test_fact_joins_resolve(sample_csv: Path) -> None:
    """Every fact row should have non-null FKs after the joins."""
    tables = build_warehouse(sample_csv)
    fact = tables["fact_transactions"]
    assert fact["date_sk"].is_null().sum() == 0
    assert fact["location_sk"].is_null().sum() == 0
    assert fact["property_type_sk"].is_null().sum() == 0
