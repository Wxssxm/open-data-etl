"""Parquet writer.

Dimensions are written as a single file each (small).
The fact table is partitioned by (year, code_departement) — a common access
pattern for DVF analytics ("show me 2023 sales in Paris").
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from loguru import logger


def write_warehouse(tables: dict[str, pl.DataFrame], warehouse_dir: Path) -> dict[str, Path]:
    warehouse_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    for dim_name in ("dim_date", "dim_location", "dim_property_type"):
        df = tables[dim_name]
        out = warehouse_dir / f"{dim_name}.parquet"
        df.write_parquet(out, compression="zstd")
        logger.info("wrote {} ({} rows) -> {}", dim_name, df.height, out)
        paths[dim_name] = out

    fact = tables["fact_transactions"]
    fact_root = warehouse_dir / "fact_transactions"
    fact_root.mkdir(parents=True, exist_ok=True)
    partitions = fact.group_by(["year", "code_departement"]).agg(pl.len().alias("rows"))
    for row in partitions.iter_rows(named=True):
        year, dept = row["year"], row["code_departement"]
        sub = fact.filter((pl.col("year") == year) & (pl.col("code_departement") == dept))
        partition_dir = fact_root / f"year={year}" / f"departement={dept}"
        partition_dir.mkdir(parents=True, exist_ok=True)
        sub.write_parquet(partition_dir / "part-0.parquet", compression="zstd")

    paths["fact_transactions"] = fact_root
    logger.success(
        "fact_transactions: {} rows across {} partitions -> {}",
        fact.height,
        partitions.height,
        fact_root,
    )
    return paths
