"""Tests for the load module."""

from __future__ import annotations

from pathlib import Path

import duckdb

from dvf_etl.load import register_views, write_warehouse
from dvf_etl.model import build_warehouse


def test_write_warehouse_creates_files(sample_csv: Path, tmp_path: Path) -> None:
    tables = build_warehouse(sample_csv)
    paths = write_warehouse(tables, tmp_path)

    for dim in ("dim_date", "dim_location", "dim_property_type"):
        assert paths[dim].exists()
        assert paths[dim].suffix == ".parquet"

    fact_root = paths["fact_transactions"]
    parquet_files = list(fact_root.rglob("*.parquet"))
    assert len(parquet_files) >= 1
    # Hive-style partition dirs
    assert any("year=" in str(p) for p in parquet_files)
    assert any("departement=" in str(p) for p in parquet_files)


def test_duckdb_views_register_and_query(sample_csv: Path, tmp_path: Path) -> None:
    tables = build_warehouse(sample_csv)
    write_warehouse(tables, tmp_path)

    with duckdb.connect(":memory:") as con:
        n = register_views(con, tmp_path)
        assert n == 4

        # Star-schema join must work end-to-end through views
        rows = con.execute("""
            SELECT COUNT(*) FROM fact_transactions f
            JOIN dim_location l USING (location_sk)
            JOIN dim_date d USING (date_sk)
            JOIN dim_property_type p USING (property_type_sk)
            """).fetchone()
        assert rows[0] == tables["fact_transactions"].height


def test_register_views_returns_zero_when_empty(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with duckdb.connect(":memory:") as con:
        assert register_views(con, empty) == 0
