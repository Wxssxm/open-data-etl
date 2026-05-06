"""Parquet writer + DuckDB view registration."""

from dvf_etl.load.duckdb_views import register_views
from dvf_etl.load.parquet import write_warehouse

__all__ = ["register_views", "write_warehouse"]
