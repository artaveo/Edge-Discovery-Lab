"""Window: ResumeTime, the 21:30 cut, and no horizon crossing 21:30 (roadmap Section 8)."""
import numpy as np
import pandas as pd

from edgelab.config import DEFAULT, MIN_PER_DAY
from edgelab.data import build_bars
from edgelab.features import m5_atr
from edgelab.targets import compute_targets
from edgelab.window import REASON_DEADLINE, REASON_NO_REF, REASON_RULE, decision_moments, resume_times
from synth import flat_day, set_bar


def _days():
    # Mon 2019-01-07 .. Fri 2019-01-11; reference median spread 20 -> threshold 30
    # (for d4 the reference is d3, whose [10:00, 21:30) median is 31 -> threshold 46.5)
    d1 = flat_day("2019-01-07")                       # first day: no reference -> 16:30
    d2 = flat_day("2019-01-08")
    d2.loc[d2["time"] < pd.Timestamp("2019-01-08 01:10"), "spread_pts"] = 80   # wide open
    d3 = flat_day("2019-01-09")
    d3.loc[d3["time"] < pd.Timestamp("2019-01-09 17:00"), "spread_pts"] = 31   # just above 1.5x
    d4 = flat_day("2019-01-10")
    set_bar(d4, "2019-01-10 01:04", spread_pts=100)   # one wide bar breaks the first streak
    d5 = flat_day("2019-01-11")
    d5.loc[d5["time"] < pd.Timestamp("2019-01-11 01:03"), "spread_pts"] = 30   # == 1.5x is ok
    return pd.concat([d1, d2, d3, d4, d5], ignore_index=True)


def _hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def test_resume_time_rule_and_deadline():
    bars = build_bars(_days())
    r = resume_times(bars, DEFAULT)
    got = [_hm(m) for m in r.minute]
    # d2: first 5 normal bars are 01:10..01:14 -> resume at the close of 01:14 = 01:15
    # d4: 01:00..01:03 ok, 01:04 wide, 01:05..01:09 ok -> 01:10
    # d5: spreads equal to the threshold count as normal -> 01:00..01:04 -> 01:05
    assert got == ["16:30", "01:15", "16:30", "01:10", "01:05"]
    assert list(r.reason) == [REASON_NO_REF, REASON_RULE, REASON_DEADLINE, REASON_RULE, REASON_RULE]
    assert np.isnan(r.ref_spread[0])
    assert list(r.ref_spread[1:]) == [20.0, 20.0, 31.0, 20.0]


def test_reference_is_previous_day_10_to_2130_median():
    d1 = flat_day("2019-01-07", spread_pts=100)
    d1.loc[(d1["time"] >= pd.Timestamp("2019-01-07 10:00")) & (d1["time"] < pd.Timestamp("2019-01-07 21:30")),
           "spread_pts"] = 10                         # only [10:00, 21:30) counts -> median 10
    d2 = flat_day("2019-01-08", spread_pts=16)       # 16 > 1.5 * 10 -> never normal -> 16:30
    d3 = flat_day("2019-01-09", spread_pts=16)       # reference is d2 (median 16) -> 01:05
    bars = build_bars(pd.concat([d1, d2, d3], ignore_index=True))
    r = resume_times(bars, DEFAULT)
    assert r.ref_spread[1] == 10 and r.ref_spread[2] == 16
    assert [_hm(m) for m in r.minute] == ["16:30", "16:30", "01:05"]


def test_decision_moments_inside_window():
    bars = build_bars(_days())
    r = resume_times(bars, DEFAULT)
    j = decision_moments(bars, r, (), DEFAULT)
    t = bars.tc5[j]
    day = bars.day5[j]
    tmod = t - day * MIN_PER_DAY
    row = bars.day_row(day)
    assert (tmod >= r.minute[row]).all()
    assert (tmod < DEFAULT.window_end).all()
    assert tmod.max() == 21 * 60 + 25
    firsts = {int(d): _hm(int(tmod[day == d].min())) for d in np.unique(day)}
    assert list(firsts.values()) == ["16:30", "01:15", "16:30", "01:10", "01:05"]
    # every M5 close in the window is a moment (flat data has no gaps)
    for d in np.unique(day):
        k = bars.day_row([d])[0]
        n_expected = (DEFAULT.window_end - 1 - r.minute[k]) // 5 + 1
        assert (day == d).sum() == n_expected


def test_quarantined_and_weekend_days_have_no_moments():
    sat = flat_day("2019-01-12")
    df = pd.concat([_days(), sat], ignore_index=True)
    bars = build_bars(df)
    r = resume_times(bars, DEFAULT)
    q = int(pd.Timestamp("2019-01-09").value // 86_400_000_000_000)
    j = decision_moments(bars, r, [q], DEFAULT)
    days = set(bars.day5[j].tolist())
    assert q not in days
    assert int(pd.Timestamp("2019-01-12").value // 86_400_000_000_000) not in days
    assert len(days) == 4


def test_no_horizon_crosses_2130():
    bars = build_bars(_days())
    r = resume_times(bars, DEFAULT)
    j = decision_moments(bars, r, (), DEFAULT)
    T = compute_targets(bars, j, m5_atr(bars, DEFAULT), DEFAULT)
    day_end = bars.day5[j] * MIN_PER_DAY + DEFAULT.window_end
    tmod = bars.tc5[j] - bars.day5[j] * MIN_PER_DAY
    for h, name in ((30, "H30"), (60, "H60"), (120, "H120"), ("EOD", "EOD")):
        valid = np.isfinite(T[f"long_{name}"])
        ex = T[f"exit_t_{name}"]
        assert (ex[valid] <= day_end[valid]).all()
        assert (ex[valid] > bars.tc5[j][valid]).all()
        if h != "EOD":
            # valid exactly when t + H <= 21:30
            assert np.array_equal(valid, tmod + h <= DEFAULT.window_end)
        else:
            assert valid.all()
    # the last moment (21:25) only has EOD; 21:00 still has H30
    last = tmod == 21 * 60 + 25
    assert np.isnan(T["long_H30"][last]).all() and np.isfinite(T["long_EOD"][last]).all()
    assert np.isfinite(T["long_H30"][tmod == 21 * 60]).all()
    assert np.isnan(T["long_H60"][tmod == 21 * 60 + 5]).all()


def test_early_close_day_invalidates_horizons_beyond_last_bar():
    d1 = flat_day("2019-01-07")
    d2 = flat_day("2019-01-08", end="19:59")           # early close
    bars = build_bars(pd.concat([d1, d2], ignore_index=True))
    r = resume_times(bars, DEFAULT)
    j = decision_moments(bars, r, (), DEFAULT)
    T = compute_targets(bars, j, m5_atr(bars, DEFAULT), DEFAULT)
    d2_id = bars.days[1]
    sel = bars.day5[j] == d2_id
    tmod = bars.tc5[j][sel] - d2_id * MIN_PER_DAY
    assert tmod.max() == 20 * 60                       # the last M5 bar 19:55 closes at 20:00
    v30 = np.isfinite(T["long_H30"][sel])
    assert np.array_equal(v30, tmod + 30 <= 20 * 60)
    eod = T["exit_t_EOD"][sel]
    ok = np.isfinite(T["long_EOD"][sel])
    assert (eod[ok] == d2_id * MIN_PER_DAY + 20 * 60).all()   # exit at the day's last close
    assert not ok[tmod == 20 * 60].any()                       # nothing left after the last bar
