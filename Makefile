.PHONY: help install run download model load notebook test lint format clean

help:
	@echo "Available targets:"
	@echo "  install      Create venv + install dev deps"
	@echo "  download     Download DVF CSV from data.gouv.fr (large)"
	@echo "  model        Clean + model into Parquet star schema"
	@echo "  load         model from bundled sample (offline-friendly)"
	@echo "  run          download + model (full pipeline against real data)"
	@echo "  notebook     Launch the exploration notebook"
	@echo "  test         pytest with coverage"
	@echo "  lint         ruff + black checks"
	@echo "  format       Auto-fix lint and format"
	@echo "  clean        Remove venv, caches, and derived data"

install:
	uv venv --python 3.11
	uv pip install -e ".[dev]"

download:
	uv run dvf-etl download

model:
	uv run dvf-etl model

load:
	uv run dvf-etl model --source data/sample/dvf_sample.csv

run: download model

notebook:
	uv run jupyter notebook notebooks/exploration.ipynb

test:
	uv run pytest --cov=src/dvf_etl --cov-report=term-missing --cov-fail-under=70

lint:
	uv run ruff check .
	uv run black --check .

format:
	uv run ruff check --fix .
	uv run black .

clean:
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache .coverage htmlcov dist build
	rm -rf data/raw data/warehouse
	find . -type d -name __pycache__ -exec rm -rf {} +
