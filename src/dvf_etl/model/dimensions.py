"""Dimension builders.

Each builder takes the cleaned DVF DataFrame and returns a dimension DataFrame
with a stable surrogate key. Dimensions are deterministic — sorting + hashing
guarantees the same surrogate keys across runs as long as the natural-key set
is identical.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

# A small lookup mapping departement code -> region (FR official 2016 list).
DEPT_TO_REGION: dict[str, str] = {
    "75": "Île-de-France",
    "77": "Île-de-France",
    "78": "Île-de-France",
    "91": "Île-de-France",
    "92": "Île-de-France",
    "93": "Île-de-France",
    "94": "Île-de-France",
    "95": "Île-de-France",
    "06": "Provence-Alpes-Côte d'Azur",
    "13": "Provence-Alpes-Côte d'Azur",
    "83": "Provence-Alpes-Côte d'Azur",
    "84": "Provence-Alpes-Côte d'Azur",
    "04": "Provence-Alpes-Côte d'Azur",
    "05": "Provence-Alpes-Côte d'Azur",
    "31": "Occitanie",
    "34": "Occitanie",
    "11": "Occitanie",
    "30": "Occitanie",
    "33": "Nouvelle-Aquitaine",
    "44": "Pays de la Loire",
    "59": "Hauts-de-France",
    "62": "Hauts-de-France",
    "67": "Grand Est",
    "68": "Grand Est",
    "35": "Bretagne",
    "29": "Bretagne",
    "22": "Bretagne",
    "56": "Bretagne",
    "69": "Auvergne-Rhône-Alpes",
    "38": "Auvergne-Rhône-Alpes",
    "63": "Auvergne-Rhône-Alpes",
    "42": "Auvergne-Rhône-Alpes",
}


def build_dim_date(df: pl.DataFrame) -> pl.DataFrame:
    """Build a date dimension covering the full range present in the fact data."""
    if df.is_empty():
        return pl.DataFrame(
            {
                "date_sk": pl.Series([], dtype=pl.Int32),
                "full_date": pl.Series([], dtype=pl.Date),
                "year": pl.Series([], dtype=pl.Int32),
                "quarter": pl.Series([], dtype=pl.Int8),
                "month": pl.Series([], dtype=pl.Int8),
                "day_of_month": pl.Series([], dtype=pl.Int8),
                "day_of_week": pl.Series([], dtype=pl.Int8),
                "is_weekend": pl.Series([], dtype=pl.Boolean),
            }
        )

    min_d: date = df["date_mutation"].min()  # type: ignore[assignment]
    max_d: date = df["date_mutation"].max()  # type: ignore[assignment]

    days = []
    cur = min_d
    while cur <= max_d:
        days.append(cur)
        cur = cur + timedelta(days=1)

    return (
        pl.DataFrame({"full_date": days})
        .with_columns(
            pl.col("full_date").dt.strftime("%Y%m%d").cast(pl.Int32).alias("date_sk"),
            pl.col("full_date").dt.year().cast(pl.Int32).alias("year"),
            pl.col("full_date").dt.quarter().cast(pl.Int8).alias("quarter"),
            pl.col("full_date").dt.month().cast(pl.Int8).alias("month"),
            pl.col("full_date").dt.day().cast(pl.Int8).alias("day_of_month"),
            pl.col("full_date").dt.weekday().cast(pl.Int8).alias("day_of_week"),
            pl.col("full_date").dt.weekday().is_in([6, 7]).alias("is_weekend"),
        )
        .unique(subset=["date_sk"])
        .select(
            "date_sk",
            "full_date",
            "year",
            "quarter",
            "month",
            "day_of_month",
            "day_of_week",
            "is_weekend",
        )
    )


def build_dim_location(df: pl.DataFrame) -> pl.DataFrame:
    """Distinct (code_postal, code_commune) pairs with derived region.

    Surrogate key = row index after sorting on the natural key, so re-runs
    produce the same surrogate as long as the natural-key set is unchanged.
    """
    return (
        df.lazy()
        .group_by("code_commune", "code_postal", "nom_commune", "code_departement")
        .agg(pl.len().alias("transactions_count"))
        .with_columns(
            pl.col("code_departement")
            .map_elements(lambda c: DEPT_TO_REGION.get(c, "Other"), return_dtype=pl.Utf8)
            .alias("region"),
        )
        .sort("code_commune", "code_postal")
        .with_columns(
            (pl.int_range(0, pl.len(), dtype=pl.Int64) + 1).alias("location_sk"),
        )
        .select(
            "location_sk",
            "code_commune",
            "code_postal",
            "nom_commune",
            "code_departement",
            "region",
        )
        .collect()
    )


def build_dim_property_type(df: pl.DataFrame) -> pl.DataFrame:
    """Distinct property types with a derived `is_residential` flag."""
    return (
        df.lazy()
        .select(pl.col("type_local").drop_nulls().unique())
        .sort("type_local")
        .with_columns(
            (pl.int_range(0, pl.len(), dtype=pl.Int64) + 1).alias("property_type_sk"),
            pl.col("type_local").is_in(["Maison", "Appartement"]).alias("is_residential"),
        )
        .select("property_type_sk", "type_local", "is_residential")
        .collect()
    )
