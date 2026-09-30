"""Synthetic XAUUSD-like M1 data for the tests.

A random walk in USD with per-minute sigma, a wide spread for the first minutes
after each session start (so ResumeTime is exercised), and an optional
**planted edge**: whenever an M5 bar closes with r60 > ``trigger_atr`` x ATR60
(Wilder 14 on M5), the price drifts by ``+drift_atr`` x ATR60 over the next 60
minutes (and the mirror image for r60 < -trigger_atr x ATR60, so that the
planted pattern adds no unconditional drift that "always long" could exploit).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


F1_START = "2020-07-01"


def trading_days(years, days_per_year=None, start=F1_START):
    """Weekdays of ``years`` on or after ``start`` (F1 data begins 2020-07-01)."""
    out = []
    for y in years:
        d = pd.bdate_range(max(pd.Timestamp(f"{y}-01-01"), pd.Timestamp(start)), f"{y}-12-31")
        if days_per_year:
            d = d[:days_per_year]
        out.extend(d)
    return out


def make_m1(years=(2020, 2021, 2022), days_per_year=None, session=(6 * 60, 22 * 60),
            sigma=0.15, price0=1500.0, spread_pts=12, open_spread_pts=80, open_wide_min=7,
            planted=False, trigger_atr=2.0, drift_atr=0.3, seed=1, digits=2):
    rng = np.random.default_rng(seed)
    days = trading_days(years, days_per_year)
    s0, s1 = session
    n_per = s1 - s0
    n = len(days) * n_per
    noise = rng.normal(0.0, sigma, size=n)
    wick = np.abs(rng.normal(0.0, 0.35 * sigma, size=(n, 2)))
    tv = rng.poisson(60, size=n) + 1
    sp = np.full(n, spread_pts, dtype=np.int64) + rng.integers(0, 4, size=n)
    minute_of_session = np.tile(np.arange(n_per), len(days))
    sp[minute_of_session < open_wide_min] = open_spread_pts
    times = (np.repeat(np.array(days, dtype="datetime64[m]"), n_per)
             + (s0 + minute_of_session).astype("timedelta64[m]"))

    close = np.empty(n)
    opn = np.empty(n)
    p = price0
    # online state for the planted edge
    atr = None
    tr_buf = []
    prev_c5 = None
    h5 = -np.inf
    l5 = np.inf
    drift = 0.0
    drift_left = 0
    closes_hist = []            # (minute_abs_close, close) for r60
    tmin = times.astype(np.int64)
    for i in range(n):
        o = p
        step = noise[i]
        if drift_left > 0:
            step += drift
            drift_left -= 1
        p = o + step
        opn[i] = o
        close[i] = p
        if not planted:
            continue
        hi = max(o, p) + wick[i, 0]
        lo = min(o, p) - wick[i, 1]
        h5 = max(h5, hi)
        l5 = min(l5, lo)
        tc = tmin[i] + 1
        closes_hist.append((tc, p))
        if tc % 5 == 0 or i == n - 1 or (tmin[i + 1] // 5 != tmin[i] // 5):
            tr = h5 - l5 if prev_c5 is None else max(h5 - l5, abs(h5 - prev_c5), abs(l5 - prev_c5))
            if atr is None:
                tr_buf.append(tr)
                if len(tr_buf) == 14:
                    atr = float(np.mean(tr_buf))
            else:
                atr += (tr - atr) / 14.0
            prev_c5 = p
            h5, l5 = -np.inf, np.inf
            if atr is not None and tc % 5 == 0:
                # C(t - 60): last close with close time <= tc - 60
                past = None
                for tt, cc in reversed(closes_hist):
                    if tt <= tc - 60:
                        past = cc
                        break
                if len(closes_hist) > 400:
                    del closes_hist[:-400]
                mod = tc % 1440
                if past is not None and abs(p - past) > trigger_atr * atr and mod < 20 * 60:
                    # symmetric, so the planted rule adds no unconditional drift
                    drift = np.sign(p - past) * drift_atr * atr / 60.0
                    drift_left = 60
    high = np.maximum(opn, close) + wick[:, 0]
    low = np.minimum(opn, close) - wick[:, 1]
    df = pd.DataFrame({
        "time": pd.DatetimeIndex(times),
        "open": np.round(opn, digits), "high": np.round(high, digits),
        "low": np.round(low, digits), "close": np.round(close, digits),
        "tick_volume": tv.astype(np.int64), "spread_pts": sp,
    })
    # rounding can break o/h/l/c ordering by a cent; restore it
    df["high"] = df[["open", "high", "low", "close"]].max(axis=1)
    df["low"] = df[["open", "high", "low", "close"]].min(axis=1)
    return df


def flat_day(date: str, start="01:00", end="23:55", price=1800.0, spread_pts=20, tick_volume=50):
    """One day of flat M1 bars (open time from ``start`` to ``end`` inclusive)."""
    t = pd.date_range(f"{date} {start}", f"{date} {end}", freq="1min")
    n = len(t)
    return pd.DataFrame({
        "time": t, "open": np.full(n, price), "high": np.full(n, price), "low": np.full(n, price),
        "close": np.full(n, price), "tick_volume": np.full(n, tick_volume, dtype=np.int64),
        "spread_pts": np.full(n, spread_pts, dtype=np.int64),
    })


def set_bar(df: pd.DataFrame, when: str, **values):
    """Set columns of the bar with open time ``when`` (in place); returns the frame."""
    m = df["time"] == pd.Timestamp(when)
    assert m.sum() == 1, when
    for k, v in values.items():
        df.loc[m, k] = v
    return df
