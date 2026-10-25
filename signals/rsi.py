"""RSI indicator and oversold signals.

Pure functions: a DataFrame in, a DataFrame out, no database access. Matches
dbt's mart_rsi_signals: a simple rolling average of gains and losses (not
Wilder smoothing), partial windows for a ticker's first rows, and a first-day
change of 0.
"""
import pandas as pd

REQUIRED_COLUMNS = {"ticker", "trade_date", "close"}

def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:

    """Return a copy of df with RSI columns added, computed per ticker.
    df needs ticker, trade_date and close. Adds gain, loss, avg_gain, avg_loss
    and rsi (unrounded).
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"df is missing columns: {sorted(missing)}")
    if window < 2:
        raise ValueError(f"window must be >= 2, got {window}")

    out = df.sort_values(["ticker", "trade_date"]).reset_index(drop=True)
    # dbt's CASE turns the first row's NULL change into a 0 gain/loss, and
    # that 0 still counts toward the average, so fill rather than drop it.

    change = out.groupby("ticker")["close"].diff().fillna(0)
    out["gain"] = change.clip(lower=0)
    out["loss"] = (-change).clip(lower=0)

    by_ticker = out.groupby("ticker")
    out["avg_gain"] = by_ticker["gain"].transform(lambda x: x.rolling(window, min_periods=1).mean())
    out["avg_loss"] = by_ticker["loss"].transform(lambda x: x.rolling(window, min_periods=1).mean())

    rs = out["avg_gain"] / out["avg_loss"]
    out["rsi"] = (100 - 100 / (1 + rs)).where(out["avg_loss"] != 0, 100.0)
    return out

def rsi_oversold(df: pd.DataFrame, window: int = 14, threshold: float = 30) -> pd.DataFrame:
    """Rows where RSI is below threshold (every day, not just the first).

    Returns ticker, trade_date, close, rsi. Compares the RSI rounded to 2
    places, as dbt does, so 29.996 is not a signal.
    """

    r = add_rsi(df, window=window)
    r["rsi"] = r["rsi"].round(2)
    cols = ["ticker", "trade_date", "close", "rsi"]
    return r.loc[r["rsi"] < threshold, cols].reset_index(drop=True)


