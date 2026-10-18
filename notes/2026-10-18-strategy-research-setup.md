# Strategy Research Setup: Session Summary (2026-10-18)

## 1. Grid search for backtesting indicators

**Question:** Can different indicators and oscillators be tested across many parameter combinations, like GridSearchCV in ML?

**Answer:** Yes. This is called *parameter optimization* or a *parameter sweep*. You define a grid (e.g., RSI window 7/14/21, oversold threshold 20/25/30, MACD fast/slow/signal periods, optional MACD confirmation on RSI entries), backtest every combination, and rank them by a metric such as Sharpe, max drawdown, or profit factor.

**Tooling:**
- **vectorbt** is built for this. Pass lists of parameters and it runs every combination as one vectorized operation:
  ```python
  import vectorbt as vbt

  rsi = vbt.RSI.run(close, window=[7, 14, 21])
  entries = rsi.rsi_crossed_below(30)
  exits = rsi.rsi_crossed_above(70)

  pf = vbt.Portfolio.from_signals(close, entries, exits)
  pf.sharpe_ratio().sort_values(ascending=False)
  ```
  - `param_product=True` crosses multiple parameters.
  - `vbt.MA.run_combs` handles moving-average crossover pairs.
- **Optuna** does Bayesian search for large grids (like RandomizedSearch vs. GridSearch).
- Run sweeps in Python, write the results to Databricks, and let a dbt mart rank and filter them. Don't try to do combinatorial sweeps in SQL.

**Overfitting guardrails.** Test 500 combinations and some will look great by chance.
- **Hold out data:** optimize on the earlier period and test only the winner on later data. Walk-forward analysis rolls this window forward over time.
- **Prefer stable regions:** a good parameter has good neighbors. If RSI-14/30 works but 13/30 and 15/30 fall apart, it's noise.
- **Penalize trial count:** the deflated Sharpe ratio adjusts for how many combinations were tested.
- With about 10 months of data (daily since Dec 2025), **backfill more history** before running large sweeps.

## 2. Where this code should live

Not in the dbt project: dbt is for scheduled SQL transformations, and sweeps are exploratory Python work. Not in stock-data-etl either, since its job is reliable ingestion. Create a separate repo:

| Repo | Responsibility |
|---|---|
| stock-data-etl | Ingest raw data (Yahoo Finance → Databricks) |
| stock-analytics-dbt | Clean, model, test |
| **strategy-research** | Read dbt marts, compute signals, run sweeps, write results back |

- The research repo should read from **dbt outputs**, not raw tables, so every experiment uses tested, cleaned data.
- The results table can become a **dbt source**, so a mart can rank strategies and feed dashboards.
- Longer term: research locally in VS Code, then move scheduled runs to **Databricks notebooks/jobs**. First confirm that scheduled notebook jobs run on the Free Edition compute, since dbt Python models don't.

## 3. Moving the MACD script

**Before:** `stock-data-etl/scripts/compute_macd.py` was run manually (not part of GitHub Actions). It imported `execute_statement`, `fetch_rows` and `execute_merge` from `databricks_sql.py`, and ran everything at the top level with 12/26/9 hardcoded.

**Findings:**
- `databricks_sql.py` depends only on `requests` and three environment variables (`DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_WAREHOUSE_ID`). `pull_stock_data.py` and `backfill_ticker.py` also use it, so the original stays in stock-data-etl.
- **Decision:** copy it into the new repo rather than build a shared package. Trade-off: fixes must be copied by hand.
- Inside Databricks notebooks this client isn't needed. Read with `spark.table("analytics.stock_prices").toPandas()` and write with a Delta `MERGE`.
- **Key refactor:** separate the indicator math (pure functions) from the reading and writing, so the daily job, grid sweeps, and future notebooks all reuse the same code.

## 4. What was built

Location: `C:\Users\tokud\Projects\strategy-research`

```
strategy-research/
├── README.md
├── requirements.txt        # pandas, requests, pytest (vectorbt commented out)
├── .gitignore
├── .env.example
├── db/databricks_sql.py    # unchanged copy from stock-data-etl
├── signals/macd.py         # add_macd(), macd_crossovers(): pure, parameterized
├── scripts/compute_macd.py # daily job: read → macd_crossovers(12,26,9) → MERGE into analytics.macd_signals
├── tests/test_macd.py      # 6 pytest tests
├── notebooks/
└── notes/                  # this file
```

- `add_macd(df, fast, slow, signal)` returns all rows with the indicator columns. **Use this for sweeps.**
- `macd_crossovers(df, fast, slow, signal)` returns only bullish crossover rows.
- **Verified:** produces exactly the same signals as the original script on test data. All 6 tests pass. Not yet run against live Databricks.

## 5. Next steps

1. Create `.venv`, `pip install -r requirements.txt`, `git init`, push to GitHub.
2. Run `python scripts/compute_macd.py` once with the Databricks environment variables set. If it loads the expected signals, delete the old `compute_macd.py` from stock-data-etl.
3. Refactor the RSI logic the same way (pure function in `signals/`).
4. Backfill more price history before large sweeps.
5. Add vectorbt and build the first sweep notebook, using a held-out period and walk-forward validation.
6. Later: confirm Free Edition supports scheduled notebook jobs, then move the daily signal jobs to Databricks.
