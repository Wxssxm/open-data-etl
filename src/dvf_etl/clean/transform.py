"""Cleaning + strict typing for DVF rows.

The real DVF CSV has 40+ columns; we keep the dozen that drive a useful
star schema and drop everything else. Polars LazyFrames let us defer the
materialisation, which matters when the source CSV is multi-GB.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from loguru import logger

# Columns we keep from the source CSV; everything else is dropped.
REQUIRED_COLUMNS: tuple[str, ...] = (
    "id_mutation",
    "date_mutation",
    "numero_disposition",
    "nature_mutation",
    "valeur_fonciere",
    "code_postal",
    "code_commune",
    "nom_commune",
    "code_departement",
    "type_local",
    "surface_reelle_bati",
    "nombre_pieces_principales",
)

# Strict source schema — Polars enforces these types when reading.
SOURCE_DTYPES: dict[str, pl.DataType] = {
    "id_mutation": pl.Utf8,
    "date_mutation": pl.Utf8,  # parsed in clean_dvf
    "numero_disposition": pl.Int32,
    "nature_mutation": pl.Utf8,
    "valeur_fonciere": pl.Float64,
    "code_postal": pl.Utf8,
    "code_commune": pl.Utf8,
    "nom_commune": pl.Utf8,
    "code_departement": pl.Utf8,
    "type_local": pl.Utf8,
    "surface_reelle_bati": pl.Float64,
    "nombre_pieces_principales": pl.Int32,
}


def scan_source(source: Path) -> pl.LazyFrame:
    """Stream-scan the source CSV (gz-compressed or plain) with strict types."""
    if source.suffix == ".gz" or source.name.endswith(".csv.gz"):
        # Polars supports compressed CSVs natively
        return pl.scan_csv(
            str(source),
            schema_overrides=SOURCE_DTYPES,
            ignore_errors=True,
            try_parse_dates=False,
        ).select(REQUIRED_COLUMNS)
    return pl.scan_csv(
        str(source),
        schema_overrides=SOURCE_DTYPES,
        ignore_errors=True,
        try_parse_dates=False,
    ).select(REQUIRED_COLUMNS)


def clean_dvf(lazy: pl.LazyFrame) -> pl.LazyFrame:
    """Apply cleaning + canonical transformations.

    - parse `date_mutation` to Date
    - drop transactions with `valeur_fonciere <= 0`
    - drop missing `surface_reelle_bati` for residential types (would yield NaN price/m²)
    - dedupe on (id_mutation, numero_disposition) — same disposition can repeat across rows
    - derive `prix_m2` (rounded), `year`, `month`
    """
    return (
        lazy.with_columns(
            pl.col("date_mutation").str.strptime(pl.Date, format="%Y-%m-%d", strict=False),
        )
        .filter(pl.col("valeur_fonciere") > 0)
        .filter(
            ~(
                pl.col("type_local").is_in(["Maison", "Appartement"])
                & (pl.col("surface_reelle_bati").is_null() | (pl.col("surface_reelle_bati") <= 0))
            )
        )
        .unique(subset=["id_mutation", "numero_disposition"])
        .with_columns(
            pl.col("date_mutation").dt.year().alias("year"),
            pl.col("date_mutation").dt.month().alias("month"),
            (pl.col("valeur_fonciere") / pl.col("surface_reelle_bati"))
            .round(0)
            .cast(pl.Int64)
            .alias("prix_m2"),
        )
    )


def clean_to_dataframe(source: Path) -> pl.DataFrame:
    """Convenience: scan + clean + collect."""
    df = clean_dvf(scan_source(source)).collect()
    logger.info("clean_dvf: {} rows after filtering + dedup", df.height)
    return df
