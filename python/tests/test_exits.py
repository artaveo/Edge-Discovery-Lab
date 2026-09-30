"""F3 exits on hand-computed M1 paths (roadmap Section 12.3, 12.7).

One flat day at 1800.00 with a 20-point (0.20) spread; ATR60 fixed at 2.00; the decision
moment is the M5 close at 10:00 (entry bar 09:59). Commission = 2 x 0.000016 x 1800 = 0.0576.
Long entry = Ask 1800.20; short entry = Bid 1800.00.
"""
import numpy as np
import pandas as pd
import pytest

from edgelab.config import DEFAULT
from edgelab.data import build_bars, to_minutes
from edgelab.exits import EXIT_GRID, ExitRule, TIME_EXIT, one_at_a_time, simulate
from synth import flat_day, set_bar

D = "2021-03-09"
A = 2.0
COMM = 2 * 0.000016 * 1800.0
SP = 0.20


def run(df, rule, side, at="10:00"):
    bars = build_bars(df)
    t = int(to_minutes(pd.DatetimeIndex([pd.Timestamp(f"{D} {at}")]))[0])
    j = np.flatnonzero(bars.tc5 == t)
    assert len(j) == 1
    atr5 = np.full(len(bars.k5), A)
    o = simulate(bars, j, atr5, DEFAULT, [rule])[(rule.name, side)]
    ex = pd.Timestamp(np.int64(o["exit_t"][0]) * 60, unit="s") if o["exit_t"][0] >= 0 else None
    return {k: v[0] for k, v in o.items()} | {"exit": ex}


def day():
    return flat_day(D, price=1800.0, spread_pts=20)


SLTP = ExitRule("sltp", 1.0, 2.0)          # S = 2.00, long SL 1798.20, TP 1804.20; short SL 1802.00, TP 1796.00


def test_grid_has_28_rules():
    assert len(EXIT_GRID) == 28
    kinds = [e.kind for e in EXIT_GRID]
    assert kinds.count("sltp") == 16 and kinds.count("sl") == 4 and kinds.count("trail") == 4 and kinds.count("be") == 4


def test_long_stop_loss():
    df = set_bar(day(), f"{D} 10:05", low=1798.0)
    o = run(df, SLTP, "long")
    assert o["reason"] == 1 and o["net_usd"] == pytest.approx(1798.20 - 1800.20 - COMM)
    assert o["r"] == pytest.approx((1798.20 - 1800.20 - COMM) / (2.0 + SP + COMM))
    assert o["exit"] == pd.Timestamp(f"{D} 10:06") and not o["conflict"]


def test_long_take_profit():
    df = set_bar(day(), f"{D} 10:10", high=1804.30)
    o = run(df, SLTP, "long")
    assert o["reason"] == 2 and o["net_usd"] == pytest.approx(4.0 - COMM)
    assert o["exit"] == pd.Timestamp(f"{D} 10:11")


def test_same_bar_conflict_counts_the_stop():
    df = set_bar(day(), f"{D} 10:05", low=1798.0, high=1804.30)
    o = run(df, SLTP, "long")
    assert o["reason"] == 1 and o["conflict"] and o["net_usd"] == pytest.approx(-2.0 - COMM)


def test_gap_fills_at_the_worse_open():
    df = set_bar(day(), f"{D} 10:05", open=1797.0, high=1797.0, low=1796.5, close=1797.0)
    o = run(df, SLTP, "long")
    assert o["reason"] == 1 and o["net_usd"] == pytest.approx(1797.0 - 1800.20 - COMM)


def test_short_stop_triggers_on_ask():
    # Bid high 1801.85 < 1802 but Ask high 1802.05 >= 1802
    df = set_bar(day(), f"{D} 10:05", high=1801.85)
    o = run(df, SLTP, "short")
    assert o["reason"] == 1 and o["net_usd"] == pytest.approx(1800.0 - 1802.0 - COMM)
    # 1801.75 + 0.20 = 1801.95 < 1802: no stop
    df = set_bar(day(), f"{D} 10:05", high=1801.75)
    assert run(df, SLTP, "short")["reason"] == 0


def test_short_take_profit_uses_ask_low():
    df = set_bar(day(), f"{D} 10:05", low=1795.85)          # Ask low 1796.05: not reached
    assert run(df, SLTP, "short")["reason"] == 0
    df = set_bar(day(), f"{D} 10:05", low=1795.75)          # Ask low 1795.95 <= 1796
    o = run(df, SLTP, "short")
    assert o["reason"] == 2 and o["net_usd"] == pytest.approx(4.0 - COMM)


def test_eod_exit_long_and_short():
    df = set_bar(day(), f"{D} 21:29", close=1801.0, high=1801.0)
    o = run(df, SLTP, "long")
    assert o["reason"] == 0 and o["exit"] == pd.Timestamp(f"{D} 21:30")
    assert o["net_usd"] == pytest.approx(1801.0 - 1800.20 - COMM)
    df = set_bar(day(), f"{D} 21:29", close=1799.0, low=1799.0)
    o = run(df, SLTP, "short")
    assert o["reason"] == 0 and o["net_usd"] == pytest.approx(1800.0 - (1799.0 + SP) - COMM)
    o = run(df, TIME_EXIT, "short")
    assert o["reason"] == 0 and o["net_usd"] == pytest.approx(1800.0 - 1799.2 - COMM)


def test_sl_only_has_no_take_profit():
    df = set_bar(day(), f"{D} 10:10", high=1830.0)
    df = set_bar(df, f"{D} 21:29", close=1800.5)
    o = run(df, ExitRule("sl", 1.0), "long")
    assert o["reason"] == 0 and o["net_usd"] == pytest.approx(0.3 - COMM)


def test_long_trailing_stop_updates_after_the_close():
    tr = ExitRule("trail", 1.0, 0.0, 1.0)
    df = set_bar(day(), f"{D} 10:00", open=1800.0, high=1803.0, low=1799.0, close=1803.0)
    # the 10:00 bar itself does not trigger (its low 1799 > initial stop 1798.20); after its close
    # the stop trails to 1803 - 2 = 1801
    df = set_bar(df, f"{D} 10:01", open=1802.0, high=1802.0, low=1800.9, close=1801.0)
    o = run(df, tr, "long")
    assert o["reason"] == 3 and o["net_usd"] == pytest.approx(1801.0 - 1800.20 - COMM)
    assert o["exit"] == pd.Timestamp(f"{D} 10:02")


def test_short_trailing_stop_uses_ask():
    tr = ExitRule("trail", 1.0, 0.0, 1.0)
    df = set_bar(day(), f"{D} 10:00", open=1800.0, high=1800.0, low=1797.0, close=1797.0)
    # lowest Ask close 1797.20 -> stop 1799.20; Ask high of the next bar 1799.0 + 0.2 reaches it
    df = set_bar(df, f"{D} 10:01", open=1798.0, high=1799.0, low=1798.0, close=1798.0)
    o = run(df, tr, "short")
    assert o["reason"] == 3 and o["net_usd"] == pytest.approx(1800.0 - 1799.2 - COMM)


def test_breakeven_moves_the_stop_and_nets_zero():
    be = ExitRule("be", 1.0, 2.0)
    df = set_bar(day(), f"{D} 10:00", open=1800.0, high=1802.5, low=1800.0, close=1802.0)   # +1 S reached
    df = set_bar(df, f"{D} 10:01", open=1801.0, high=1801.0, low=1800.1, close=1800.5)
    o = run(df, be, "long")
    assert o["reason"] == 4 and o["net_usd"] == pytest.approx(0.0, abs=1e-9)


def test_breakeven_stop_in_the_activation_bar_is_the_original_stop():
    be = ExitRule("be", 1.0, 2.0)
    df = set_bar(day(), f"{D} 10:00", open=1800.0, high=1802.5, low=1798.0, close=1800.0)
    o = run(df, be, "long")
    assert o["reason"] == 1 and o["net_usd"] == pytest.approx(-2.0 - COMM)


def test_breakeven_take_profit_after_activation():
    be = ExitRule("be", 1.0, 2.0)
    df = set_bar(day(), f"{D} 10:00", open=1800.0, high=1802.5, low=1800.3, close=1802.0)
    df = set_bar(df, f"{D} 10:01", open=1802.0, high=1804.5, low=1801.0, close=1804.0)
    o = run(df, be, "long")
    assert o["reason"] == 2 and o["net_usd"] == pytest.approx(4.0 - COMM)


def test_no_path_after_2130_gives_nan():
    df = flat_day(D, start="01:00", end="21:29")
    o = run(df, SLTP, "long", at="21:30")
    assert np.isnan(o["net_usd"]) and np.isnan(o["r"])


def test_one_position_at_a_time_skips_signals_during_an_open_trade():
    entry = np.array([0, 5, 10, 12, 20])
    exit_ = np.array([12, 8, 15, 30, 25])
    # 0 is taken (busy until 12); 5 and 10 are skipped; 12 >= 12 is taken (busy until 30); 20 skipped
    assert one_at_a_time(entry, exit_).tolist() == [True, False, False, True, False]
    # input order does not matter
    perm = np.array([3, 0, 4, 2, 1])
    assert one_at_a_time(entry[perm], exit_[perm]).tolist() == [True, True, False, False, False]
