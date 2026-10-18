import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.macd import add_macd, macd_crossovers  # noqa: E402


def _prices():
    dates = pd.bdate_range("2026-01-01", periods=120)
    t = np.arange(len(dates))
    frames = [
        pd.DataFrame({"ticker": "AAA", "trade_date": dates, "close": 100 + 10 * np.sin(t / 8)}),
        pd.DataFrame({"ticker": "BBB", "trade_date": dates, "close": 50 + 5 * np.cos(t / 5)}),
    ]
    return pd.concat(frames, ignore_index=True)


def test_crossovers_are_real_upward_crosses():
    sig = macd_crossovers(_prices())
    assert not sig.empty
    assert list(sig.columns) == ["ticker", "trade_date", "close", "macd_line", "signal_line", "histogram"]
    assert (sig["macd_line"] >= sig["signal_line"]).all()


def test_tickers_do_not_bleed_into_each_other():
    prices = _prices()
    together = add_macd(prices)
    alone = add_macd(prices[prices["ticker"] == "BBB"])
    pd.testing.assert_series_equal(
        together.loc[together["ticker"] == "BBB", "macd_line"].reset_index(drop=True),
        alone["macd_line"].reset_index(drop=True),
    )


def test_parameters_change_the_result():
    prices = _prices()
    assert not macd_crossovers(prices).equals(macd_crossovers(prices, fast=5, slow=35, signal=5))


@pytest.mark.parametrize("fast,slow", [(26, 12), (12, 12), (0, 26)])
def test_bad_windows_rejected(fast, slow):
    with pytest.raises(ValueError):
        add_macd(_prices(), fast=fast, slow=slow)
