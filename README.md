# Strategy Research

Python strategy logic and backtesting research for the stock pipeline.

- **stock-data-etl** ingests daily prices into Databricks
- **stock-analytics-dbt** cleans, models and tests them
- **strategy-research** (this repo) computes indicator signals and runs parameter sweeps, reading from and writing back to Databricks

## Layout

| Path | What it is |
|---|---|
| `signals/` | Pure indicator functions: DataFrame in, DataFrame out, no I/O. Reused by daily jobs, sweeps and notebooks. |
| `db/databricks_sql.py` | Databricks SQL Statement API client, copied from stock-data-etl. Used when running outside Databricks. |
| `scripts/` | Entry points that read data, call `signals/`, and write results. |
| `notebooks/` | Exploratory research and sweeps. |
| `tests/` | pytest tests for `signals/`. |

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Set `DATABRICKS_HOST`, `DATABRICKS_TOKEN` and `DATABRICKS_WAREHOUSE_ID` (see `.env.example`).

## Run

```
python scripts/compute_macd.py   # daily MACD crossovers -> analytics.macd_signals
pytest                            # tests
```

## Notes

- `db/databricks_sql.py` is a copy; fixes made in stock-data-etl need to be copied over by hand.
- Inside a Databricks notebook, read with `spark.table(...)` instead of the SQL client. The `signals/` functions work unchanged.
