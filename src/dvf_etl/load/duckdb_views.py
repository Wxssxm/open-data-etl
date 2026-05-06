"""Create DuckDB views over the Parquet warehouse."""

from __future__ import annotations

from pathlib import Path

import duckdb


def register_views(con: duckdb.DuckDBPyConnection, warehouse_dir: Path) -> int:
    """Register dim_* + fact_transactions views over the parquet outputs."""
    n_views = 0
    for dim_name in ("dim_date", "dim_location", "dim_property_type"):
        path = warehouse_dir / f"{dim_name}.parquet"
        if not path.exists():
            continue
        con.execute(f"CREATE OR REPLACE VIEW {dim_name} AS SELECT * FROM read_parquet('{path}')")
        n_views += 1

    fact_glob = warehouse_dir / "fact_transactions" / "year=*" / "departement=*" / "*.parquet"
    if list(fact_glob.parent.parent.parent.glob("*/*/*.parquet")):
        con.execute(f"""
            CREATE OR REPLACE VIEW fact_transactions AS
            SELECT * FROM read_parquet('{fact_glob}', hive_partitioning=true)
            """)
        n_views += 1
    return n_views
