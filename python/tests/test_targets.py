"""Targets: hand-computed long/short net (roadmap Section 8)."""
import numpy as np
import pandas as pd
import pytest

from edgelab.config import DEFAULT, MIN_PER_DAY
from edgelab.data import InstrumentSpec, build_bars
from edgelab.features import m5_atr
from edgelab.targets import compute_targets
from synth import flat_day, set_bar


def _moment(bars, when):
    """M5 index whose close time equals ``when``."""
    t = int(pd.Timestamp(when).value // 60_000_000_000)
    j = np.flatnonzero(bars.tc5 == t)
    assert len(j) == 1
    return j


def _example():
    # The four bars that matter:
    #   entry   20:29 (closes 20:30): Bid 1800.00, spread 20 pts
    #   H30     20:59 (closes 21:00): Bid 1803.50, spread 35 pts
    #   H60/EOD 21:29 (closes 21:30): Bid 1797.20, spread 25 pts
    #   after   21:30..23:55: 1900.00 (must never be used: beyond 21:30)
    df = flat_day("2019-03-05", price=1790.0, spread_pts=30)
    df.loc[df["time"] >= pd.Timestamp("2019-03-05 21:30"), ["open", "high", "low", "close"]] = 1900.0
    set_bar(df, "2019-03-05 20:29", open=1800.0, high=1800.0, low=1800.0, close=1800.0, spread_pts=20)
    set_bar(df, "2019-03-05 20:59", open=1803.5, high=1803.5, low=1803.5, close=1803.5, spread_pts=35)
    set_bar(df, "2019-03-05 21:29", open=1797.2, high=1797.2, low=1797.2, close=1797.2, spread_pts=25)
    return df


def test_hand_computed_long_short_net():
    bars = build_bars(_example(), InstrumentSpec(point=0.01, digits=2))
    j = _moment(bars, "2019-03-05 20:30")
    T = compute_targets(bars, j, np.full(len(bars.k5), 2.0), DEFAULT)
    comm = 2 * 0.000016 * 1800.0                     # 0.0576 USD/oz, open + close
    assert T["commission"][0] == pytest.approx(0.0576)
    assert T["spread0"][0] == pytest.approx(0.20)
    # H30: move +3.50; long pays the entry spread 0.20, short pays the exit spread 0.35
    assert T["long_H30"][0] == pytest.approx(3.50 - 0.20 - comm)       # 3.2424
    assert T["short_H30"][0] == pytest.approx(-3.50 - 0.35 - comm)     # -3.9076
    assert T["long_H30"][0] == pytest.approx(3.2424)
    assert T["short_H30"][0] == pytest.approx(-3.9076)
    # H60 exits at the 21:30 close: move -2.80, exit spread 0.25
    assert T["long_H60"][0] == pytest.approx(-2.80 - 0.20 - comm)      # -3.0576
    assert T["short_H60"][0] == pytest.approx(2.80 - 0.25 - comm)      # 2.4924
    assert T["long_H60"][0] == pytest.approx(-3.0576)
    assert T["short_H60"][0] == pytest.approx(2.4924)
    # EOD = last M1 close at or before 21:30 = the same bar as H60 here
    assert T["long_EOD"][0] == pytest.approx(-3.0576)
    assert T["short_EOD"][0] == pytest.approx(2.4924)
    # H120 would end at 22:30 -> crosses 21:30 -> invalid
    assert np.isnan(T["long_H120"][0]) and np.isnan(T["short_H120"][0])
    # ATR units: divided by ATR60(t) (2.0 here)
    assert T["long_atr_H30"][0] == pytest.approx(3.2424 / 2.0)
    assert T["short_atr_H60"][0] == pytest.approx(2.4924 / 2.0)
    # exits are the close times of the exit bars
    day = bars.day5[j][0] * MIN_PER_DAY
    assert T["exit_t_H30"][0] == day + 21 * 60
    assert T["exit_t_H60"][0] == day + 21 * 60 + 30


def test_exit_uses_last_close_before_horizon_when_bar_missing():
    df = _example()
    df = df[df["time"] != pd.Timestamp("2019-03-05 20:59")]           # the H30 bar is missing
    set_bar(df, "2019-03-05 20:58", open=1801.0, high=1801.0, low=1801.0, close=1801.0, spread_pts=40)
    bars = build_bars(df)
    j = _moment(bars, "2019-03-05 20:30")
    T = compute_targets(bars, j, np.full(len(bars.k5), 1.0), DEFAULT)
    comm = 2 * 0.000016 * 1800.0
    assert T["long_H30"][0] == pytest.approx(1.0 - 0.20 - comm)
    assert T["short_H30"][0] == pytest.approx(-1.0 - 0.40 - comm)


def test_long_plus_short_is_minus_total_cost():
    bars = build_bars(_example())
    j = np.arange(len(bars.k5))
    j = j[(bars.tc5[j] % MIN_PER_DAY) < 21 * 60]
    T = compute_targets(bars, j, np.full(len(bars.k5), 1.0), DEFAULT)
    ok = np.isfinite(T["long_H30"])
    i1 = bars.asof_index(T["exit_t_H30"][ok])
    total = T["spread0"][ok] + bars.spread_pts[i1] * 0.01 + 2 * T["commission"][ok]
    assert np.allclose(T["long_H30"][ok] + T["short_H30"][ok], -total)


def test_atr_units_use_m5_wilder_atr():
    rng = np.random.default_rng(3)
    df = flat_day("2019-03-05")
    p = 1800 + np.cumsum(rng.normal(0, 0.2, len(df)))
    df["open"] = np.r_[p[0], p[:-1]]
    df["close"] = p
    df["high"] = np.maximum(df["open"], df["close"]) + 0.05
    df["low"] = np.minimum(df["open"], df["close"]) - 0.05
    bars = build_bars(df)
    atr = m5_atr(bars, DEFAULT)
    j = _moment(bars, "2019-03-05 15:00")
    T = compute_targets(bars, j, atr, DEFAULT)
    assert T["atr60"][0] == atr[j][0] and np.isfinite(atr[j][0])
    assert T["long_atr_H60"][0] == pytest.approx(T["long_H60"][0] / atr[j][0])
