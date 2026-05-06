"""Typer CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import duckdb
import typer
from rich.console import Console
from rich.table import Table

from dvf_etl.config import get_settings
from dvf_etl.download import download_dvf
from dvf_etl.load import register_views, write_warehouse
from dvf_etl.model import build_warehouse

app = typer.Typer(
    name="dvf-etl",
    help="Batch ETL: data.gouv DVF -> Parquet star schema + DuckDB views.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def download(
    year: Annotated[int | None, typer.Option(help="Override the configured year")] = None,
    departement: Annotated[
        str | None, typer.Option(help="Override the configured departement")
    ] = None,
) -> None:
    """Download a (year, departement) DVF CSV.gz from data.gouv.fr."""
    s = get_settings()
    path = download_dvf(
        s.dvf_base_url,
        year or s.dvf_year,
        departement or s.dvf_departement,
        s.data_raw_dir,
    )
    console.print(f"[green]Downloaded -> {path}[/]")


@app.command()
def model(
    source: Annotated[Path | None, typer.Option(help="Override the source CSV path")] = None,
) -> None:
    """Clean + model the source CSV into the Parquet warehouse."""
    s = get_settings()
    src = source or s.sample_csv
    if not src.exists():
        raise typer.BadParameter(
            f"source not found: {src}. Did you run `dvf-etl download` or generate the sample?"
        )

    tables = build_warehouse(src)
    paths = write_warehouse(tables, s.warehouse_dir)

    table = Table(title="Warehouse")
    table.add_column("Table")
    table.add_column("Rows", justify="right")
    table.add_column("Path")
    for name, df in tables.items():
        table.add_row(name, str(df.height), str(paths[name]))
    console.print(table)


@app.command()
def query(sql: Annotated[str, typer.Argument(help="SQL to execute against the warehouse")]) -> None:
    """Run a one-off SQL query against the Parquet warehouse via DuckDB."""
    s = get_settings()
    with duckdb.connect(":memory:") as con:
        n = register_views(con, s.warehouse_dir)
        if n == 0:
            console.print("[yellow]No views registered — run `dvf-etl model` first.[/]")
            raise typer.Exit(code=1)
        df = con.execute(sql).pl()
    console.print(df)


if __name__ == "__main__":
    app()
