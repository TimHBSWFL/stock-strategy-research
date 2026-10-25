import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.rsi import add_rsi, rsi_oversold  # noqa: E402


def _prices():
    dates = pd.bdate_range("2026-01-01", periods=120)
    t = np.arange(len(dates))
    frames = [
        pd.DataFrame({"ticker": "AAA", "trade_date": dates, "close": 100 + 10 * np.sin(t / 8)}),
        pd.DataFrame({"ticker": "BBB", "trade_date": dates, "close": 50 + 5 * np.cos(t / 5)}),
    ]
    return pd.concat(frames, ignore_index=True)


def test_rsi_stays_in_range():
    rsi = add_rsi(_prices())["rsi"]
    assert rsi.between(0, 100).all()


def test_only_rising_prices_give_100():
    dates = pd.bdate_range("2026-01-01", periods=30)
    up = pd.DataFrame({"ticker": "UP", "trade_date": dates, "close": np.arange(30,
dtype=float) + 100})
    assert (add_rsi(up)["rsi"] == 100).all()


def test_tickers_do_not_bleed_into_each_other():
    prices = _prices()
    together = add_rsi(prices)
    alone = add_rsi(prices[prices["ticker"] == "BBB"])
    pd.testing.assert_series_equal(
        together.loc[together["ticker"] == "BBB", "rsi"].reset_index(drop=True),
        alone["rsi"].reset_index(drop=True)
    )


@pytest.mark.parametrize("threshold", [20, 30, 40])
def test_oversold_respects_threshold(threshold):
    sig = rsi_oversold(_prices(), threshold=threshold)
    assert not sig.empty
    assert list(sig.columns) == ["ticker","trade_date","close", "rsi"]
    assert (sig["rsi"] < threshold).all()


@pytest.mark.parametrize("window", [0, 1])
def test_bad_windows_rejected(window):
    with pytest.raises(ValueError):
        add_rsi(_prices(), window=window)