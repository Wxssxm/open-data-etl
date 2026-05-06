"""Build the fact table by joining cleaned DVF rows to the dimensions."""

from __future__ import annotations

from pathlib import Path

import polars as pl
from loguru import logger

from dvf_etl.clean import clean_to_dataframe
from dvf_etl.model.dimensions import (
    build_dim_date,
    build_dim_location,
    build_dim_property_type,
)


def build_fact_transactions(
    cleaned: pl.DataFrame,
    dim_date: pl.DataFrame,
    dim_location: pl.DataFrame,
    dim_property_type: pl.DataFrame,
) -> pl.DataFrame:
    """Join cleaned rows to the 3 dimensions, returning the fact DataFrame."""
    fact = (
        cleaned.lazy()
        .join(
            dim_date.lazy().select(["full_date", "date_sk"]),
            left_on="date_mutation",
            right_on="full_date",
            how="left",
        )
        .join(
            dim_location.lazy().select(["code_commune", "code_postal", "location_sk"]),
            on=["code_commune", "code_postal"],
            how="left",
        )
        .join(
            dim_property_type.lazy().select(["type_local", "property_type_sk"]),
            on="type_local",
            how="left",
        )
        .select(
            pl.col("id_mutation"),
            pl.col("numero_disposition"),
            pl.col("date_sk"),
            pl.col("location_sk"),
            pl.col("property_type_sk"),
            pl.col("nature_mutation"),
            pl.col("valeur_fonciere"),
            pl.col("surface_reelle_bati"),
            pl.col("nombre_pieces_principales"),
            pl.col("prix_m2"),
            pl.col("year"),
            pl.col("code_departement"),
        )
        .collect()
    )
    return fact


def build_warehouse(source: Path) -> dict[str, pl.DataFrame]:
    """Run the whole ETL in memory and return all 4 tables.

    For real-data multi-GB inputs, use the streaming variant in `load.parquet`.
    """
    cleaned = clean_to_dataframe(source)

    dim_date = build_dim_date(cleaned)
    dim_location = build_dim_location(cleaned)
    dim_property_type = build_dim_property_type(cleaned)
    fact = build_fact_transactions(cleaned, dim_date, dim_location, dim_property_type)

    logger.success(
        "warehouse: dim_date={}, dim_location={}, dim_property_type={}, fact={}",
        dim_date.height,
        dim_location.height,
        dim_property_type.height,
        fact.height,
    )
    return {
        "dim_date": dim_date,
        "dim_location": dim_location,
        "dim_property_type": dim_property_type,
        "fact_transactions": fact,
    }
