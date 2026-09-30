"""F5: the previous New York close level (roadmap Section 13.7).

Hand-built days: day 0 (Mon 2021-03-08) ends with a last M1 Bid close of 1800.00, so the level
L of day 1 (Tue 2021-03-09) is 1800.00. Day 1 is flat at 1805 (above L) unless stated; spread
20 points (0.20); ResumeTime of day 1 is 01:05. ATRtf is fixed at 2.00 on both timeframes, so
0.5 x ATR = 1.00. Commission = 2 x 0.000016 x entry.
"""
import json
import os

import numpy as np
import pandas as pd
import pytest

from edgelab import nyclose as ny
from edgelab.data import InstrumentSpec, build_bars, to_minutes
from edgelab.exits import ExitRule, simulate
from synth import flat_day, make_m1_nyclose, set_bar

D0, D1 = "2021-03-08", "2021-03-09"
L = 1800.0
SP = 0.20


def comm(px):
    return 2 * 0.000016 * px


def seg(df, start, end, price, **kw):
    m = (df["time"] >= pd.Timestamp(f"{D1} {start}")) & (df["time"] <= pd.Timestamp(f"{D1} {end}"))
    for c in ("open", "high", "low", "close"):
        df.loc[m, c] = price
    for k, v in kw.items():
        df.loc[m, k] = v
    return df


def bar(df, when, **kw):
    return set_bar(df, f"{D1} {when}", **kw)


def two_days(price1=1805.0):
    d0 = flat_day(D0, price=1796.0, spread_pts=20)
    d0 = set_bar(d0, f"{D0} 23:55", close=L, high=L)
    return d0, flat_day(D1, price=price1, spread_pts=20)


def prep(d0, d1):
    p = ny.prepare_f5(pd.concat([d0, d1], ignore_index=True), InstrumentSpec())
    for tf in p.tfs.values():
        tf.atr[:] = 2.0
    return p


def trades(p, variant, exit_rule, tf=5):
    return ny.simulate_all(p, tfs=(tf,), variants=[variant], exits=[exit_rule])[ny.config_name(tf, variant, exit_rule)]


def first_setup(p, variant, tf=5):
    t = p.tfs[tf]
    ctx = ny.day_contexts(p, t)[-1]
    ev = ny.candidates(p, t, ctx, variant)[0]
    return ny.resolve_setup(p, t, ctx, ev)[0], ev


def hhmm(m):
    return str(pd.Timestamp(int(m) * 60, unit="s"))[11:16]


# ----------------------------------------------------------------------------- level, side, fills

def test_grid_is_336_configurations():
    assert len(ny.VARIANTS) == 14 and len(ny.EXITS) == 12
    assert len({ny.config_name(tf, v, e) for tf in ny.TFS for v in ny.VARIANTS for e in ny.EXITS}) == 336


def test_level_is_the_previous_days_last_bid_close():
    p = prep(*two_days())
    assert np.isnan(p.levels[0]) and p.levels[1] == L


def test_approach_side():
    C = np.array([1805.0, 1800.0, 1799.0])
    assert ny._side_before(C, L, np.zeros(3), 1803.0).tolist() == [1, 1, 1]     # j0: the day's first bar
    assert ny._side_before(C, L, np.zeros(3), 1795.0).tolist() == [-1, 1, 1]
    # with a band of 1.0, closes inside (1799, 1801) are skipped
    C = np.array([1805.0, 1799.5, 1798.0, 1800.5])
    assert ny._side_before(C, L, np.ones(4), 1805.0).tolist() == [1, 1, 1, -1]
    # the first event of a day below L is a short (up approach), from the first bar
    d0, d1 = two_days(1795.0)
    d1 = bar(d1, "11:00", high=1800.0)
    tr = trades(prep(d0, d1), ("R1", None), (1.0, 1))
    assert tr[0]["side"] == -1 and tr[0]["approach"] == -1


def test_limit_fill_at_L_long_uses_bid_plus_spread():
    d0, d1 = two_days()
    d1 = bar(d1, "10:00", low=1799.81)                 # 1799.81 + 0.20 > 1800: no fill
    d1 = bar(d1, "10:30", low=1799.80)                 # 1799.80 + 0.20 = 1800: fill
    tr = trades(prep(d0, d1), ("R1", None), (1.0, 1))
    assert len(tr) == 1 and tr[0]["entry"] == L and hhmm(tr[0]["t_entry"]) == "10:31" and tr[0]["side"] == 1


def test_limit_fill_at_L_short_uses_bid():
    d0, d1 = two_days(1795.0)
    d1 = bar(d1, "10:30", high=1799.99)
    d1 = bar(d1, "11:00", high=1800.00)
    tr = trades(prep(d0, d1), ("R1", None), (1.0, 1))
    assert len(tr) == 1 and tr[0]["entry"] == L and hhmm(tr[0]["t_entry"]) == "11:01" and tr[0]["side"] == -1


def test_take_profit_is_net_of_cost():
    for k in (1, 2, 3):
        d0, d1 = two_days()
        d1 = bar(d1, "10:30", low=1799.80)
        d1 = seg(d1, "10:31", "23:55", 1810.0)                                  # beyond every TP
        tr = trades(prep(d0, d1), ("R1", None), (1.0, k))[0]
        unit = 2.0 + comm(L)
        assert tr["reason"] == 2 and tr["r"] == pytest.approx(k) and tr["usd"] == pytest.approx(k * unit)


# ----------------------------------------------------------------------------- families

def test_r1_fade_at_touch_and_structural_stop():
    d0, d1 = two_days()
    d1 = bar(d1, "10:30", low=1799.70)
    st, _ = first_setup(prep(d0, d1), ("R1", None))
    assert st.side == 1 and st.entry == L and st.struct == 1799.70 and st.fill_bar >= 0 and not st.struct_known


def test_r2_rejection_close_back_above():
    d0, d1 = two_days()
    d1 = bar(d1, "10:02", low=1799.80)
    d1 = bar(d1, "10:04", open=1801.0, high=1801.0, low=1801.0, close=1801.0)
    p = prep(d0, d1)
    st, ev = first_setup(p, ("R2", None))
    assert st.side == 1 and st.entry == pytest.approx(1801.2) and hhmm(st.t_entry) == "10:05"
    assert st.struct == pytest.approx(1799.80)                                  # the rejection bar's low
    tr = trades(p, ("R2", None), ("S", 1))[0]
    unit = (1801.2 - 1799.8) + comm(1801.2)
    assert tr["reason"] == 2 and tr["usd"] == pytest.approx(unit)


def _stair():
    d0, d1 = two_days()
    d1 = seg(d1, "10:00", "10:04", 1799.7)
    d1 = seg(d1, "10:05", "10:09", 1799.2)
    d1 = seg(d1, "10:10", "10:14", 1798.9)
    d1 = seg(d1, "10:15", "23:55", 1797.5)
    return prep(d0, d1)


@pytest.mark.parametrize("d, when, px", [(0.0, "10:05", 1799.7), (0.25, "10:10", 1799.2),
                                          (0.5, "10:15", 1798.9), (1.0, "10:20", 1797.5)])
def test_breakout_each_distance(d, when, px):
    st, _ = first_setup(_stair(), ("B", d))
    assert st.side == -1 and st.entry == pytest.approx(px) and hhmm(st.t_entry) == when
    assert st.struct == pytest.approx(px + SP)                                  # the break bar's Ask high


def _break_then(ret_when):
    d0, d1 = two_days()
    d1 = seg(d1, "10:00", "10:04", 1799.7)
    d1 = seg(d1, "10:05", "23:55", 1797.0)
    d1 = bar(d1, ret_when, high=1800.0)
    return prep(d0, d1)


def test_break_and_retest_within_12_bars():
    p = _break_then("10:30")
    st, _ = first_setup(p, ("BR", 0.0))
    assert st.side == -1 and st.entry == L and hhmm(st.t_entry) == "10:31" and st.struct_known
    assert st.struct == pytest.approx(1799.9)                                   # break bar Ask high
    tr = trades(p, ("BR", 0.0), (1.0, 1))
    assert len(tr) == 1 and tr[0]["side"] == -1


def test_break_and_retest_after_12_bars_is_no_trade():
    p = _break_then("11:10")                                                    # window ends 11:05
    st, _ = first_setup(p, ("BR", 0.0))
    assert st is None and trades(p, ("BR", 0.0), (1.0, 1)) == []


def test_failed_break():
    d0, d1 = two_days()
    d1 = seg(d1, "10:00", "10:04", 1799.7)
    d1 = seg(d1, "10:05", "10:14", 1799.0)
    d1 = seg(d1, "10:15", "23:55", 1800.5)
    st, _ = first_setup(prep(d0, d1), ("F", 0.0))
    assert st.side == 1 and st.entry == pytest.approx(1800.7) and hhmm(st.t_entry) == "10:20"
    assert st.struct == pytest.approx(1799.0)                                   # lowest low since the break


def test_structural_stop_is_floored_at_a_tenth_of_atr():
    p = _break_then("10:30")
    tr = trades(p, ("BR", 0.0), ("S", 1))[0]
    # break bar Ask high 1799.9 is below the entry L: widened to 0.2; the fill bar's Ask high
    # (1800.0 + 0.2) reaches 1800.2 in the fill bar itself -> stopped (-1 R)
    assert tr["reason"] == 1 and tr["r"] == pytest.approx(-1.0)


# ----------------------------------------------------------------------------- several events per day

def _two_touches():
    d0, d1 = two_days()
    d1 = seg(d1, "10:00", "10:59", 1800.3)                                      # closes stay 0.3 from L
    d1 = bar(d1, "10:00", low=1799.8)                                           # event 1
    d1 = bar(d1, "10:01", high=1801.2)                                          # its TP (S0.5 k1: 1801.12)
    d1 = bar(d1, "10:30", low=1799.8)                                           # not re-armed yet
    d1 = seg(d1, "11:00", "11:59", 1805.0)                                      # away by 5 >= 1.0
    d1 = bar(d1, "12:00", low=1799.8)                                           # event 2
    return prep(d0, d1)


def test_rearm_and_test_numbers():
    tr = trades(_two_touches(), ("R1", None), (0.5, 1))
    assert [hhmm(t["t_entry"]) for t in tr] == ["10:01", "12:01"]
    assert [t["test_no"] for t in tr] == [1, 2]
    assert tr[0]["reason"] == 2


def test_open_position_blocks_the_next_event_and_eod_closes():
    tr = trades(_two_touches(), ("R1", None), (2.0, 3))                         # TP far away, stop not hit
    assert len(tr) == 1 and tr[0]["reason"] == 0 and hhmm(tr[0]["exit_t"]) == "21:30"
    assert tr[0]["usd"] == pytest.approx(1805.0 - L - comm(L))


def test_no_entry_at_or_after_2100():
    d0, d1 = two_days()
    assert trades(prep(d0, bar(d1.copy(), "21:05", low=1799.8)), ("R1", None), (1.0, 1)) == []
    assert trades(prep(d0, bar(d1.copy(), "21:00", low=1799.8)), ("R1", None), (1.0, 1)) == []
    assert len(trades(prep(d0, bar(d1.copy(), "20:59", low=1799.8)), ("R1", None), (1.0, 1))) == 1


def test_path_rules_match_exits_py():
    """Same levels -> same fill as the F3 engine (SL1, TP 2 x S, long at the 10:00 moment)."""
    df = set_bar(flat_day(D1, price=1800.0), f"{D1} 10:10", high=1804.3)
    bars = build_bars(df)
    t = int(to_minutes(pd.DatetimeIndex([pd.Timestamp(f"{D1} 10:00")]))[0])
    j = np.flatnonzero(bars.tc5 == t)
    f3 = simulate(bars, j, np.full(len(bars.k5), 2.0), exits=[ExitRule("sltp", 1.0, 2.0)])[("SL1_TP2", "long")]
    i0 = int(bars.last5[j[0]])
    e = 1800.0 + SP
    px, ib, reason, _ = ny.path_exit(bars, 1, e, e - 2.0, e + 4.0, i0 + 1, len(bars.t) - 1)
    assert reason == 2 and px - e - comm(1800.0) == pytest.approx(f3["net_usd"][0])


# ----------------------------------------------------------------------------- permutation

def _toy_arr():
    base = int((pd.Timestamp("2021-01-04") - pd.Timestamp("1970-01-01")).days)
    days = np.array([base, base, base + 1, base + 2])
    mk = lambda r, rf: {"day": days, "year": np.full(4, 2021), "r": np.array(r, float), "r_flip": np.array(rf, float)}  # noqa: E731
    return {"a": mk([1, 1, 1, 1], [-1, -1, -1, -1]), "b": mk([2, 2, 2, 2], [-2, -2, -2, -2])}


def test_direction_flip_is_deterministic_and_flips_days_together():
    arr = _toy_arr()
    n1 = ny.flip_null(arr, ["a", "b"], n_perm=50, seed=7)
    n2 = ny.flip_null(arr, ["a", "b"], n_perm=50, seed=7)
    assert np.array_equal(n1, n2)
    assert not np.array_equal(n1, ny.flip_null(arr, ["a", "b"], n_perm=50, seed=8))
    # one coin per day, shared by both configurations and both trades of a day
    assert np.allclose(n1[:, 1], 2 * n1[:, 0])
    assert set(np.round(n1[:, 0] * 4).astype(int)) <= {4, 2, 0, -2, -4}          # day 1 moves 2 trades at once
    assert (np.round(n1[:, 0] * 4).astype(int) % 2 == 0).all()


# ----------------------------------------------------------------------------- planted edge and random walk

PLANT = dict(days_per_year=None, seed=1, bounce_atr=2.0)


@pytest.fixture(scope="module")
def planted():
    p = ny.prepare_f5(make_m1_nyclose(planted=True, **PLANT), InstrumentSpec())
    return p, ny.run_f5(p, n_perm=40)


@pytest.fixture(scope="module")
def noise():
    p = ny.prepare_f5(make_m1_nyclose(planted=False, **PLANT), InstrumentSpec())
    return p, ny.run_f5(p, n_perm=40)


def _top(res, n=12):
    rows = sorted(res["rows"], key=lambda r: -np.nan_to_num(r["mean_r"], nan=-9))[:n]
    return "\n".join(f"{r['config']}: n={r['trades']} mean={r['mean_r']:.3f} low={r['boot_lower_r']:.3f} "
                     f"p={r['p_rc']:.3f} {r['checks']}" for r in rows)


def test_planted_rejection_edge_passes_with_r1_r2_k2_and_breakouts_fail(planted):
    _, res = planted
    assert res["verdict"] == "F5_PASS", _top(res)
    passing = [r for r in res["rows"] if r["passes"]]
    k2 = [r for r in passing if r["variant"] in ("R1", "R2") and r["exit"].endswith("_k2")]
    assert k2, _top(res)
    assert not any(r["variant"].startswith("B(") for r in passing)
    # breakouts fail the reality check; the best of them is far below the passing fades
    b = [r for r in res["rows"] if r["variant"].startswith("B(") and r["trades"]]
    assert b and all(r["p_rc"] >= 0.10 for r in b)
    assert max(r["mean_r"] for r in b) < min(r["mean_r"] for r in k2)


def test_random_walk_reaches_stop(noise):
    _, res = noise
    assert res["verdict"] == "F5_STOP", _top(res)


def test_every_configuration_is_counted_and_heatmaps(noise):
    _, res = noise
    assert len(res["rows"]) == 336 and res["null"].shape == (40, 336)
    for tf in ("M5", "M15"):
        assert len(res["heatmaps"][tf]) == 14
        for grid in res["heatmaps"][tf].values():
            assert np.asarray(grid).shape == (4, 3)


def test_trades_respect_the_rules(noise):
    p, res = noise
    for name in res["names"][:: 7]:
        a = res["arr"][name]
        if len(a["day"]) < 2:
            continue
        mod = a["t_entry"] - a["day"] * 1440
        assert (mod <= ny.ENTRY_CUTOFF + 1).all()                                 # entries before 21:00
        for d in np.unique(a["day"]):
            m = np.flatnonzero(a["day"] == d)
            o = m[np.argsort(a["t_entry"][m])]
            assert (a["t_entry"][o][1:] >= a["exit_t"][o][:-1]).all()            # one position at a time
            assert a["test_no"][o].tolist() == sorted(a["test_no"][o].tolist())
        assert (a["r"][a["reason"] == 1] <= -1 + 1e-9).all()                     # a stop loses >= 1 R


def test_report_files(planted, tmp_path):
    p, res = planted
    s = ny.write_report(p, res, tmp_path, {"files": [{"file": "x.csv.gz", "sha256": "ab" * 32}]}, "synthetic")
    md = (tmp_path / "report.md").read_text()
    assert "F5_PASS" in md and "F5 — COMPLETE" in md
    assert json.loads((tmp_path / "report.json").read_text())["n_configurations"] == 336
    for tf in ("M5", "M15"):
        svg = (tmp_path / f"heatmap_{tf}.svg").read_text()
        assert svg.startswith("<svg") and "</svg>" in svg
    assert s["charts"]
    assert len((tmp_path / "trials_ledger.jsonl").read_text().strip().splitlines()) == 1
    assert ny.main(["--out", str(tmp_path), "--data", str(tmp_path)]) == 2
