"""MACD indicator and bullish-crossover signals.

Pure functions: a DataFrame in, a DataFrame out, no database access. The daily
script, a parameter sweep and a Databricks notebook can all call the same code
and only differ in how they read and write data.
"""
import pandas as pd

REQUIRED_COLUMNS = {"ticker", "trade_date", "close"}


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Return a copy of df with MACD columns added, computed per ticker.

    df needs ticker, trade_date and close. Adds ema_fast, ema_slow, macd_line,
    signal_line, histogram, prev_macd and prev_signal.
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"df is missing columns: {sorted(missing)}")
    if not 0 < fast < slow:
        raise ValueError(f"Need 0 < fast < slow, got fast={fast}, slow={slow}")
    if signal < 1:
        raise ValueError(f"signal must be >= 1, got {signal}")

    out = df.sort_values(["ticker", "trade_date"]).reset_index(drop=True)
    by_ticker = out.groupby("ticker")["close"]

    out["ema_fast"] = by_ticker.transform(lambda x: x.ewm(span=fast, adjust=False).mean())
    out["ema_slow"] = by_ticker.transform(lambda x: x.ewm(span=slow, adjust=False).mean())
    out["macd_line"] = out["ema_fast"] - out["ema_slow"]
    out["signal_line"] = out.groupby("ticker")["macd_line"].transform(
        lambda x: x.ewm(span=signal, adjust=False).mean())
    out["histogram"] = out["macd_line"] - out["signal_line"]
    out["prev_macd"] = out.groupby("ticker")["macd_line"].shift(1)
    out["prev_signal"] = out.groupby("ticker")["signal_line"].shift(1)
    return out


def macd_crossovers(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Rows where the MACD line crosses above the signal line (bullish entry).

    Returns ticker, trade_date, close, macd_line, signal_line, histogram.
    """
    m = add_macd(df, fast=fast, slow=slow, signal=signal)
    crossed_up = (m["prev_macd"] < m["prev_signal"]) & (m["macd_line"] >= m["signal_line"])
    cols = ["ticker", "trade_date", "close", "macd_line", "signal_line", "histogram"]
    return m.loc[crossed_up, cols].reset_index(drop=True)
