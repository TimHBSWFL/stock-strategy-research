"""Daily MACD job: read prices from Databricks, write crossover signals back.

Same output as the old stock-data-etl/scripts/compute_macd.py (12/26/9 into
analytics.macd_signals); the indicator math now lives in signals/macd.py.

Run from anywhere:  python scripts/compute_macd.py
Needs DATABRICKS_HOST, DATABRICKS_TOKEN and DATABRICKS_WAREHOUSE_ID set.
"""
import os
import sys
from datetime import datetime, timezone

import pandas as pd

# Put the repo root on the path so `db` and `signals` import no matter where
# the script is launched from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from db.databricks_sql import execute_merge, execute_statement, fetch_rows  # noqa: E402
from signals.macd import macd_crossovers  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

FAST, SLOW, SIGNAL = 12, 26, 9
TARGET_TABLE = "analytics.macd_signals"


def load_prices() -> pd.DataFrame:
    body = execute_statement("""
        SELECT ticker, trade_date, close
        FROM analytics.stock_prices
        ORDER BY ticker, trade_date
    """)
    columns = [col["name"] for col in body["manifest"]["schema"]["columns"]]
    df = pd.DataFrame(fetch_rows(body), columns=columns)
    df["close"] = df["close"].astype(float)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def build_merge_sql(batch, run_ts):
    ts = run_ts.strftime("%Y-%m-%d %H:%M:%S.%f")
    values_sql = ",".join(
        f"('{r.ticker}', '{str(r.trade_date)[:10]}', {r.close}, {r.macd_line}, "
        f"{r.signal_line}, {r.histogram}, TIMESTAMP '{ts}')"
        for r in batch
    )
    return f"""
MERGE INTO {TARGET_TABLE} AS target
USING (
    SELECT ticker, trade_date, close, macd_line, signal_line, histogram, run_ts
    FROM VALUES {values_sql}
    AS source(ticker, trade_date, close, macd_line, signal_line, histogram, run_ts)
)
ON target.ticker = source.ticker AND target.trade_date = source.trade_date
WHEN MATCHED THEN UPDATE SET
    close = source.close,
    macd_line = source.macd_line,
    signal_line = source.signal_line,
    histogram = source.histogram,
    run_ts = source.run_ts
WHEN NOT MATCHED THEN INSERT (ticker, trade_date, close, macd_line, signal_line, histogram, run_ts)
VALUES (source.ticker, source.trade_date, source.close, source.macd_line, source.signal_line, source.histogram, source.run_ts)
"""


def main():
    prices = load_prices()
    signals = macd_crossovers(prices, fast=FAST, slow=SLOW, signal=SIGNAL)
    run_ts = datetime.now(timezone.utc)
    loaded = execute_merge(
        list(signals.itertuples()),
        lambda batch: build_merge_sql(batch, run_ts),
        label="crossover signals",
    )
    print(f"MACD signals written successfully. {loaded} crossover signals loaded.")


if __name__ == "__main__":
    main()
