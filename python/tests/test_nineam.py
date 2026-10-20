"""F6: the New York 9 AM candle sweep + MSS (roadmap Section 14.7).

Hand-built days on Wed 2021-03-10 (broker time, offset 7 h: the 9 AM NY candle is broker
16:00-16:59 and the window is 17:00-17:59). Flat bars have equal highs and lows, so they make
no pivots; only the bars set by a test do. Spread 20 points (0.20); commission 2 x 0.000016 x entry.
"""
import gzip
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

from edgelab import nineam as f6
from edgelab.data import InstrumentSpec
from synth import flat_day, make_m1, set_bar, trading_days

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import verify_export  # noqa: E402

D, D2 = "2021-03-10", "2021-03-11"
SP = 0.20


def comm(px):
    return 2 * 0.000016 * px


def bar(df, when, date=D, **kw):
    return set_bar(df, f"{date} {when}", **kw)


def seg(df, start, end, price, date=D):
    m = (df["time"] >= pd.Timestamp(f"{date} {start}")) & (df["time"] <= pd.Timestamp(f"{date} {end}"))
    for c in ("open", "high", "low", "close"):
        df.loc[m, c] = price
    return df


def setup_of(df, offset=7):
    bars = f6.weekday_bars(df, InstrumentSpec())
    flags, st = f6.day_setup(bars, 0, offset)
    return bars, flags, st


def one_trade(df):
    bars = f6.weekday_bars(df, InstrumentSpec())
    sim = f6.simulate(bars, f6.day_offsets(bars, None), f6.GOLD_COMMISSION_RATE)
    return sim["trades"]


# ----------------------------------------------------------------------------- the video's three examples

def example2(fill_low=31061.30, tp_bar="19:00"):
    """Video example 2 (long, R2): 9 AM high 31,223.50, low 31,000; low swept to 30,990.25 at
    10:10 NY; last pivot high 31,061.50 at 10:07; close above it at 10:30; limit fill at 10:35."""
    df = flat_day(D, price=31020.0)
    bar(df, "16:10", high=31223.50)
    bar(df, "16:40", low=31000.00)
    bar(df, "17:07", high=31061.50)
    bar(df, "17:10", low=30990.25)
    seg(df, "17:30", "23:55", 31070.0)
    bar(df, "17:30", open=31020.0, low=31020.0)
    bar(df, "17:35", low=fill_low)
    if tp_bar:
        bar(df, tp_bar, high=31223.50)
    return df


def example1():
    """Video example 1 (short, R3): 9 AM high 30,806, low 30,646; high swept to 30,814.75 at
    10:00 NY; last pivot low 30,772.75 at 9:57; close below it at 10:20; limit fill at 10:28."""
    df = flat_day(D, price=30790.0)
    bar(df, "16:05", high=30806.00)
    bar(df, "16:20", low=30646.00)
    bar(df, "16:57", low=30772.75)
    bar(df, "17:00", high=30814.75)
    seg(df, "17:20", "23:55", 30760.0)
    bar(df, "17:20", open=30790.0, high=30790.0)
    bar(df, "17:28", high=30772.75)
    bar(df, "19:00", low=30646.00)
    return df


def example3():
    """Video example 3 (short, R3): 9 AM high 31,275, low 31,157; price breaks above the high
    (sweep) and runs to 31,370 at 10:30 NY; last pivot low 31,321 at 10:27; close below at 10:38."""
    df = flat_day(D, price=31200.0)
    bar(df, "16:30", high=31275.00)
    bar(df, "16:35", low=31157.00)
    seg(df, "17:20", "17:37", 31330.0)
    bar(df, "17:20", open=31200.0, low=31200.0)
    bar(df, "17:27", low=31321.00)
    bar(df, "17:30", high=31370.00)
    seg(df, "17:38", "23:55", 31310.0)
    bar(df, "17:38", open=31330.0, high=31330.0)
    bar(df, "17:40", high=31321.00)
    bar(df, "19:00", low=31170.00)
    return df


def test_video_example_2_long_target_is_the_9am_high():
    bars, flags, st = setup_of(example2())
    assert flags["sweep"] == 1 and flags["break"] and flags["order"] and flags["fill"]
    assert st.side == 1 and st.entry == 31061.50 and st.stop == 30990.25 and st.tp == 31223.50
    assert st.tp_type == "9AM" and st.r == pytest.approx(71.25)
    assert (31223.50 - 31061.50) / st.r == pytest.approx(2.2737, abs=1e-4)
    tr = one_trade(example2())[0]
    assert tr["reason"] == 2 and tr["r"] == pytest.approx((162.0 - comm(31061.5)) / 71.25)


def test_video_example_1_short_target_is_3r():
    bars, flags, st = setup_of(example1())
    assert flags["sweep"] == -1 and st.side == -1
    assert st.entry == 30772.75 and st.stop == 30814.75 and st.r == pytest.approx(42.0)
    assert st.tp_type == "3R" and st.tp == pytest.approx(30646.75)          # 3R is nearer than 30,646
    tr = one_trade(example1())[0]
    assert tr["reason"] == 2 and tr["r"] == pytest.approx(3.0 - comm(30772.75) / 42.0)


def test_video_example_3_short_after_a_breakout_sweep():
    bars, flags, st = setup_of(example3())
    assert st.side == -1 and st.entry == 31321.00 and st.stop == 31370.00 and st.r == pytest.approx(49.0)
    assert st.tp_type == "3R" and st.tp == pytest.approx(31174.0)            # nearer than 31,157
    assert pd.Timestamp(int(bars.t[st.pivot_bar]) * 60, unit="s").strftime("%H:%M") == "17:27"
    tr = one_trade(example3())[0]
    assert tr["reason"] == 2 and tr["r"] == pytest.approx(3.0 - comm(31321.0) / 49.0)


# ----------------------------------------------------------------------------- time and sweep

def test_the_9am_candle_includes_everything_before_10():
    df = example2()
    bar(df, "16:59", low=30900.0)               # 9:59 NY: part of the 9 AM candle -> L9 = 30,900
    _, flags, st = setup_of(df)
    assert flags["sweep"] == 0 and st is None   # 30,990.25 at 10:10 no longer sweeps


def test_offset_moves_the_whole_schedule():
    _, flags, st = setup_of(example2(), offset=7)
    assert st is not None
    _, flags, st = setup_of(example2(), offset=6)   # 9 AM NY = broker 15:00: a different candle
    assert st is None or st.entry != 31061.50


def test_first_sweep_decides_the_day():
    df = example2()
    bar(df, "17:05", high=31230.0)              # the high is swept first -> short-only
    _, flags, st = setup_of(df)
    assert flags["sweep"] == -1 and st is None   # the later low sweep is never traded


def test_one_bar_sweeping_both_sides_skips_the_day():
    df = example2()
    bar(df, "17:10", high=31230.0)
    _, flags, st = setup_of(df)
    assert flags["skip"] == "both sides swept by one bar" and st is None


def test_gap_in_the_window_skips_the_day():
    df = example2()
    df = df[~((df["time"] >= pd.Timestamp(f"{D} 17:40")) & (df["time"] <= pd.Timestamp(f"{D} 17:45")))]
    _, flags, st = setup_of(df)
    assert flags["skip"].startswith("gap") and not flags["used"] and st is None
    df = example2()
    df = df[~((df["time"] >= pd.Timestamp(f"{D} 17:40")) & (df["time"] <= pd.Timestamp(f"{D} 17:44")))]
    _, flags, _ = setup_of(df)                  # exactly 5 missing bars is allowed
    assert flags["used"]


# ----------------------------------------------------------------------------- pivot, MSS and break

def test_pivot_is_strict():
    df = example2()
    bar(df, "17:06", high=31061.50)             # equal neighbour: 17:07 is no longer a pivot
    _, flags, st = setup_of(df)
    # the most recent pivot is now the 9 AM high (16:10) itself: no close above it, no trade
    assert not flags["break"] and st is None


def test_last_pivot_before_x_and_mss_updates_with_a_new_low():
    df = example2(fill_low=31039.80)
    bar(df, "17:12", high=31040.0)              # a newer pivot high ...
    bar(df, "17:15", low=30980.0)               # ... before a new low of X
    _, _, st = setup_of(df)
    assert st.entry == 31040.0 and st.stop == 30980.0 and st.r == pytest.approx(60.0)


def test_last_pivot_before_x_ignores_pivots_after_x():
    p = f6._last_pivot_before(np.array([1.0, 3.0, 1.0, 1.0, 2.0, 1.0]))
    assert p.tolist() == [-1, -1, 1, 1, 1, 4]  # the pivot at 1 counts for k > 1, the pivot at 4 for k > 4
    assert f6._last_pivot_before(np.array([1.0, 3.0, 1.0, 4.0, 1.0]))[4] == 3


def test_break_needs_a_close_beyond_m():
    df = example2()
    seg(df, "17:30", "23:55", 31050.0)
    bar(df, "17:30", high=31070.0)              # wick above M only
    _, flags, st = setup_of(df)
    assert flags["sweep"] == 1 and not flags["break"] and st is None


# ----------------------------------------------------------------------------- limit

def test_long_fill_uses_bid_plus_spread():
    _, flags, st = setup_of(example2(fill_low=31061.31))    # 31,061.51 > M: no fill
    assert flags["order"] and not flags["fill"] and st is None
    df = example2(fill_low=31061.31)
    bar(df, "17:40", low=31061.30)
    _, _, st = setup_of(df)
    assert pd.Timestamp(st.t_entry * 60, unit="s").strftime("%H:%M") == "17:41"


def test_short_fill_uses_bid():
    df = example1()
    bar(df, "17:28", high=30772.74)
    _, flags, st = setup_of(df)
    assert flags["order"] and not flags["fill"]


def test_limit_is_cancelled_at_11_ny():
    df = example2(fill_low=31070.0)
    bar(df, "18:00", low=31061.30)              # 11:00 NY: too late
    _, flags, st = setup_of(df)
    assert flags["order"] and not flags["fill"] and st is None
    df = example2(fill_low=31070.0)
    bar(df, "17:59", low=31061.30)              # 10:59 NY: still live
    assert setup_of(df)[2] is not None


def test_limit_is_cancelled_when_the_target_comes_first():
    df = example2()
    bar(df, "17:33", high=31223.50)
    _, flags, st = setup_of(df)
    assert flags["order"] and not flags["fill"] and st is None
    df = example2()
    bar(df, "17:35", high=31223.50)             # TP and fill in one bar: cancelled
    assert setup_of(df)[2] is None


def test_no_order_without_room():
    df = example2()
    bar(df, "16:10", high=31050.0)              # the 9 AM high is the last pivot: M = H9, no room
    bar(df, "17:07", high=31020.0)
    _, flags, st = setup_of(df)
    assert flags["break"] and not flags["order"] and st is None


def test_long_target_3r_when_nearer():
    df = example2()
    bar(df, "16:10", high=31300.0)
    _, _, st = setup_of(df)
    assert st.tp_type == "3R" and st.tp == pytest.approx(31061.50 + 3 * 71.25)


# ----------------------------------------------------------------------------- exits

def test_same_bar_conflict_counts_the_stop():
    df = example2(tp_bar=None)
    bar(df, "18:30", high=31223.50, low=30990.0)
    tr = one_trade(df)[0]
    assert tr["reason"] == 1 and tr["conflict"] and tr["r"] == pytest.approx(-1 - comm(31061.5) / 71.25)


def test_stop_in_the_fill_bar():
    df = example2(fill_low=30990.0)             # the fill bar also reaches the stop
    tr = one_trade(df)[0]
    assert tr["reason"] == 1 and tr["conflict"] and tr["exit_i"] == tr["fill_bar"]


def test_stop_gap_fills_at_the_worse_open():
    df = example2(tp_bar=None)
    bar(df, "18:30", open=30950.0, high=30950.0, low=30950.0, close=30950.0)
    tr = one_trade(df)[0]
    assert tr["reason"] == 1 and tr["exit_px"] == 30950.0


def test_short_stop_triggers_on_ask():
    df = example1()
    bar(df, "18:30", high=30814.60)             # Bid 30,814.60 + 0.20 >= 30,814.75
    tr = one_trade(df)[0]
    assert tr["reason"] == 1 and tr["exit_px"] == 30814.75


def test_overnight_hold_and_unfinished_trade():
    d1 = example2(tp_bar=None)
    d2 = flat_day(D2, price=31070.0)
    bar(d2, "03:00", high=31223.50, date=D2)
    tr = one_trade(pd.concat([d1, d2], ignore_index=True))
    assert len(tr) == 1 and tr[0]["reason"] == 2 and tr[0]["overnight"]
    tr = one_trade(example2(tp_bar=None))[0]
    assert tr["reason"] == 0 and tr["exit_i"] == len(example2()) - 1


def test_one_trade_per_day():
    df = example2(tp_bar=None)
    bar(df, "17:45", low=30980.0)               # stopped out inside the window ...
    bar(df, "17:50", low=31061.30)              # ... a second touch of M is not a new trade
    assert len(one_trade(df)) == 1


def test_flip_is_the_mirrored_trade_on_the_same_path():
    bars = f6.weekday_bars(example2(), InstrumentSpec())
    _, st = f6.day_setup(bars, 0, 7)
    flp = f6.trade_result(bars, st, f6.GOLD_COMMISSION_RATE, flip=True)
    assert flp["reason"] == 1 and flp["exit_px"] == pytest.approx(31061.50 + 71.25)
    assert flp["r"] == pytest.approx(-1 - comm(31061.5) / 71.25)


def test_flip_pvalue_is_deterministic():
    days = np.arange(100)
    r = np.where(days % 2 == 0, 2.0, -1.0)
    p1, n1 = f6.flip_pvalue(days, r, -r)
    p2, n2 = f6.flip_pvalue(days, r, -r)
    assert p1 == p2 and np.array_equal(n1, n2) and 0.0 <= p1 <= 1.0


# ----------------------------------------------------------------------------- time check

def test_cash_open_check_finds_the_offset():
    base = flat_day(D, price=100.0)
    for when, expect in (("16:30", 7), ("15:30", 6), ("17:30", 8), (None, 7)):
        df = base.copy()
        if when:
            t0 = pd.Timestamp(f"{D} {when}")
            df.loc[(df["time"] >= t0) & (df["time"] < t0 + pd.Timedelta(minutes=30)), "tick_volume"] = 400
        bars = f6.weekday_bars(df, InstrumentSpec())
        wc = f6.cash_open_check(bars)
        assert [w["offset_h"] for w in wc.values()] == [expect]
        assert f6.day_offsets(bars, wc).tolist() == [expect]


# ----------------------------------------------------------------------------- planted edge / random walk

def planted_days(years=(2020, 2021, 2022)):
    """Every weekday is example 2 (long) or example 1 (short), shifted in price; every trade wins."""
    frames = []
    for k, d in enumerate(trading_days(years)):
        ds = d.strftime("%Y-%m-%d")
        df = (example2() if k % 2 == 0 else example1()).copy()
        df["time"] = df["time"].map(lambda t: pd.Timestamp(f"{ds} {t:%H:%M}"))
        shift = 50.0 * (k % 7)
        for c in ("open", "high", "low", "close"):
            df[c] = df[c] + shift
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def test_planted_edge_passes(tmp_path):
    bars = f6.weekday_bars(planted_days(), InstrumentSpec())
    run = f6.run_instrument(bars, None, f6.GOLD_COMMISSION_RATE, n_perm=50)
    res = run["res"]
    assert res["verdict_rule"] == "F6_PASS", res["checks"]
    assert res["per_year"]["2021"]["trades"] >= 250 and res["win_rate"] == 1.0
    run["bars"] = bars
    s = f6.write_report({"nas": run, "gold": None}, tmp_path, {}, {"source": "synthetic"}, "synthetic")
    js = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert js["verdict"] == "F6_PASS" and len(s["charts"]["nas"]) == 10
    svg = (tmp_path / s["charts"]["nas"][0]["file"]).read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "MSS / entry" in svg and "9AM high" in svg
    assert "F6 — COMPLETE" in (tmp_path / "report.md").read_text(encoding="utf-8")
    assert len((tmp_path / "trials_ledger.jsonl").read_text(encoding="utf-8").strip().splitlines()) == 1


def test_random_walk_stops():
    df = make_m1(sigma=0.3, seed=3)
    bars = f6.weekday_bars(df, InstrumentSpec())
    res = f6.run_instrument(bars, None, f6.GOLD_COMMISSION_RATE, n_perm=50)["res"]
    assert res["trades"] >= 100
    assert res["verdict_rule"] == "F6_STOP", (res["per_year"], res["p_flip"])


def _write_f6_export(d, symbol="NDX100"):
    """A tiny export like EL_ExportM1 v3.00 writes it into data/f6."""
    d.mkdir(parents=True)
    df = make_m1(years=(2020, 2021, 2022), days_per_year=2, seed=2)
    files = []
    for y in (2020, 2021, 2022):
        out = df[df["time"].dt.year == y].copy()
        out["time"] = out["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        for c in ("open", "high", "low", "close"):
            out[c] = out[c].map(lambda v: f"{v:.2f}")
        name = f"{symbol.lower()}_m1_{y}.csv.gz"
        (d / name).write_bytes(gzip.compress(out.to_csv(index=False, lineterminator="\n").encode(), mtime=0))
        files.append({"file": name, "year": y, "rows": len(out), "first_bar": out["time"].iloc[0],
                      "last_bar": out["time"].iloc[-1], "sha256": hashlib.sha256((d / name).read_bytes()).hexdigest()})
    man = {"schema": "edgelab.export.v1", "phase": "F6", "symbol": symbol, "digits": 2, "point": 0.01,
           "contract_size": 1.0, "files": files}
    (d / "manifest.json").write_text(json.dumps(man))
    return df


def test_f6_export_loads_and_verifies(tmp_path):
    df = _write_f6_export(tmp_path / "f6")
    got, spec, man = f6.load_f6(tmp_path / "f6")
    assert len(got) == len(df) and spec.symbol == "NDX100" and spec.contract_size == 1.0
    assert verify_export.verify(tmp_path / "f6") == []
    _write_f6_export(tmp_path / "x" / "f6", symbol="XAUUSD")
    with pytest.raises(ValueError):
        f6.load_f6(tmp_path / "x" / "f6")
    assert verify_export.verify(tmp_path / "x" / "f6")


def test_run_refuses_twice_and_without_commission(tmp_path):
    (tmp_path / "report.json").write_text("{}")
    assert f6.main(["--out", str(tmp_path)]) == 2
    assert f6.NAS_COMMISSION_RATE is None
    assert f6.main(["--out", str(tmp_path / "new")]) == 2
