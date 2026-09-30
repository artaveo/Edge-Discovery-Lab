"""The market snapshot at a decision moment t (roadmap Section 4).

All features use only M1 bars with close time <= t. The list is frozen: adding,
removing or redefining a feature is a new counted trial.

Definitions (C(x) = Bid close of the last M1 bar with close time <= x;
ATR = ATR60(t) = Wilder ATR(14) of clock-aligned M5 bars, value of the M5 bar
closing at t; "day" = the trading day of t; "previous day" = the previous
trading day; "20-day" statistics use the previous 20 trading days (not the
current one) and need at least 10 valid values, else NaN):

Recent returns
  r5, r15, r60, r240   (C(t) - C(t-k)) / ATR
  r_day                100 * ln(C(t) / day open)  -- percent, so it is not a copy of d_open
Volatility
  atr_rel20            ATR / mean of ATR60 at the same time of day over the previous 20 days
  range60              (max high - min low of M1 bars closing in (t-60, t]) / ATR
  rv30_rel             rv30(t) / median of rv30 at the same time of day over the previous 20 days,
                       rv30 = sqrt(mean of the last 30 squared M1 log returns)
Position
  pos_day              (C - day low) / (day high - day low), day extremes up to t (0.5 if flat)
  d_pdh, d_pdl         (C - previous day high / low) / ATR
  d_asia_hi, d_asia_lo (C - Asian high / low) / ATR; Asian range = M1 bars closing in
                       [ResumeTime, min(08:00, t)] (session start instead of ResumeTime
                       when ResumeTime >= 08:00)
  d_open               (C - day open) / ATR
Structure
  consec               signed count of consecutive same-direction M5 close-to-close moves
                       ending at t (0 if the last move is flat)
  bars_since_high/low  M5 bars of the day since the latest M5 bar at the day high / low
  overlap12            sum of the last 12 M5 ranges / (max high - min low of those bars)
Activity
  tv_rel               tick volume of M1 bars closing in (t-15, t] / its 20-day median at the
                       same time of day
  spread_rel           spread_pts(t) / median M1 spread_pts of all bars of the previous 20 days
Calendar
  min_since_resume     t - ResumeTime (minutes)
  hour_bucket          0..5 for 00-08, 08-10, 10-13, 13-16:30, 16:30-18, 18-21:30 (by t)
  weekday              0 = Monday
Previous day
  pd_ret               (close - open) of the previous day / its daily Wilder ATR(14)
  pd_range_rel         previous day range / median daily range of the previous 20 days
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from .config import DEFAULT, F1Config, MIN_PER_DAY
from .data import Bars, weekday_of_day, wilder_atr
from .window import Resume

FEATURES = (
    "r5", "r15", "r60", "r240", "r_day",
    "atr_rel20", "range60", "rv30_rel",
    "pos_day", "d_pdh", "d_pdl", "d_asia_hi", "d_asia_lo", "d_open",
    "consec", "bars_since_high", "bars_since_low", "overlap12",
    "tv_rel", "spread_rel",
    "min_since_resume", "hour_bucket", "weekday",
    "pd_ret", "pd_range_rel",
)

# features expressed in ATR60 units (invariant to an affine price change a + k*p)
ATR_SCALED = ("r5", "r15", "r60", "r240", "range60", "d_pdh", "d_pdl",
              "d_asia_hi", "d_asia_lo", "d_open")

SLOTS = MIN_PER_DAY // 5


def m5_atr(bars: Bars, cfg: F1Config = DEFAULT) -> np.ndarray:
    return wilder_atr(bars.h5, bars.l5, bars.c5, cfg.atr_period)


def _slot5(bars: Bars) -> np.ndarray:
    return (bars.k5 % MIN_PER_DAY) // 5


def same_slot_history(bars: Bars, values5: np.ndarray, stat: str, cfg: F1Config = DEFAULT) -> np.ndarray:
    """For each M5 bar: ``stat`` of the same quantity at the same time of day over the
    previous ``hist_days`` trading days (value on a past day = its latest M5 value at or
    before that clock time on that day)."""
    rows = bars.day_row(bars.day5)
    slot = _slot5(bars)
    mat = np.full((bars.n_days, SLOTS), np.nan)
    mat[rows, slot] = values5
    df = pd.DataFrame(mat).ffill(axis=1).shift(1)
    roll = df.rolling(cfg.hist_days, min_periods=cfg.hist_min_days)
    hist = (roll.mean() if stat == "mean" else roll.median()).to_numpy()
    return hist[rows, slot]


def _day_cum(values: np.ndarray, day: np.ndarray, how: str) -> np.ndarray:
    s = pd.Series(values)
    g = s.groupby(day, sort=False)
    return (g.cummax() if how == "max" else g.cummin()).to_numpy()


def _rolling_window_extreme(k5, arr, t, j, span, how):
    """Max/min of arr over M5 bars with key >= t - span, up to and including j."""
    j0 = np.searchsorted(k5, t - span, side="left")
    nmax = span // 5
    fill = -np.inf if how == "max" else np.inf
    out = np.full(len(j), fill)
    for off in range(nmax):
        jj = j - off
        ok = jj >= j0
        v = np.where(ok, arr[np.clip(jj, 0, None)], fill)
        out = np.maximum(out, v) if how == "max" else np.minimum(out, v)
    return out


def _rolling_window_sum(k5, arr, t, j, span):
    j0 = np.searchsorted(k5, t - span, side="left")
    out = np.zeros(len(j))
    for off in range(span // 5):
        jj = j - off
        out += np.where(jj >= j0, arr[np.clip(jj, 0, None)], 0.0)
    return out


def _consec(c5: np.ndarray) -> np.ndarray:
    sgn = np.zeros(len(c5), dtype=np.int64)
    sgn[1:] = np.sign(np.diff(c5)).astype(np.int64)
    out = np.zeros(len(c5))
    run = 0
    for i, s in enumerate(sgn.tolist()):
        if s == 0:
            run = 0
        elif run != 0 and (run > 0) == (s > 0):
            run += s
        else:
            run = s
        out[i] = run
    return out


def _bars_since_extremes(h5, l5, day5):
    n = len(h5)
    bsh = np.zeros(n)
    bsl = np.zeros(n)
    hl, ll, dl = h5.tolist(), l5.tolist(), day5.tolist()
    cur = None
    hi = lo = 0.0
    jh = jl = 0
    for j in range(n):
        if dl[j] != cur:
            cur, hi, lo, jh, jl = dl[j], hl[j], ll[j], j, j
        else:
            if hl[j] >= hi:
                hi, jh = hl[j], j
            if ll[j] <= lo:
                lo, jl = ll[j], j
        bsh[j] = j - jh
        bsl[j] = j - jl
    return bsh, bsl


def _pooled_spread_median(bars: Bars, cfg: F1Config) -> np.ndarray:
    """Per day row: median spread_pts over all M1 bars of the previous 20 trading days."""
    n = bars.n_days
    out = np.full(n, np.nan)
    for r in range(n):
        lo = max(0, r - cfg.hist_days)
        if r - lo < cfg.hist_min_days:
            continue
        s, e = bars.d_first[lo], bars.d_last[r - 1] + 1
        out[r] = float(np.median(bars.spread_pts[s:e]))
    return out


def _prev_row_median(values: np.ndarray, cfg: F1Config) -> np.ndarray:
    return pd.Series(values).shift(1).rolling(cfg.hist_days, min_periods=cfg.hist_min_days).median().to_numpy()


def compute_features(bars: Bars, resume: Resume, moments: np.ndarray, atr5: np.ndarray | None = None,
                     cfg: F1Config = DEFAULT) -> pd.DataFrame:
    """Feature matrix (one row per moment, columns = FEATURES)."""
    j = np.asarray(moments, dtype=np.int64)
    if atr5 is None:
        atr5 = m5_atr(bars, cfg)
    all5 = np.arange(len(bars.k5))
    t5 = bars.tc5
    t = t5[j]
    i_t = bars.last5[j]
    C = bars.c[i_t]
    atr = atr5[j]
    day = bars.day5[j]
    row = bars.day_row(day)
    f = {}

    def close_asof(tau):
        i = bars.asof_index(tau)
        return np.where(i >= 0, bars.c[np.clip(i, 0, None)], np.nan)

    for k in (5, 15, 60, 240):
        f[f"r{k}"] = (C - close_asof(t - k)) / atr
    f["r_day"] = 100.0 * np.log(C / bars.d_open[row])

    # --- volatility
    f["atr_rel20"] = atr / same_slot_history(bars, atr5, "mean", cfg)[j]
    hi60 = _rolling_window_extreme(bars.k5, bars.h5, t, j, 60, "max")
    lo60 = _rolling_window_extreme(bars.k5, bars.l5, t, j, 60, "min")
    f["range60"] = (hi60 - lo60) / atr
    lr = np.zeros(len(bars.c))
    lr[1:] = np.diff(np.log(bars.c))
    rv = np.full(len(bars.c), np.nan)
    if len(lr) > 30:
        rv[30:] = np.sqrt(sliding_window_view(lr[1:] ** 2, 30).mean(axis=1))
    rv5 = rv[bars.last5]
    f["rv30_rel"] = rv5[j] / same_slot_history(bars, rv5, "median", cfg)[j]

    # --- position
    dhi = _day_cum(bars.h, bars.day, "max")[i_t]
    dlo = _day_cum(bars.l, bars.day, "min")[i_t]
    rng = dhi - dlo
    f["pos_day"] = np.where(rng > 0, (C - dlo) / np.where(rng > 0, rng, 1.0), 0.5)
    prev = row - 1
    prev_ok = prev >= 0
    pcl = np.clip(prev, 0, None)
    f["d_pdh"] = np.where(prev_ok, (C - bars.d_high[pcl]) / atr, np.nan)
    f["d_pdl"] = np.where(prev_ok, (C - bars.d_low[pcl]) / atr, np.nan)
    asia_start_day = np.where(resume.minute < cfg.asia_end, resume.abs,
                              bars.tc[bars.d_first])
    brow = bars.day_row(bars.day)
    in_asia = (bars.tc >= asia_start_day[brow]) & (bars.tc <= bars.day * MIN_PER_DAY + cfg.asia_end)
    ahi = _day_cum(np.where(in_asia, bars.h, -np.inf), bars.day, "max")[i_t]
    alo = _day_cum(np.where(in_asia, bars.l, np.inf), bars.day, "min")[i_t]
    f["d_asia_hi"] = np.where(np.isfinite(ahi), (C - ahi) / atr, np.nan)
    f["d_asia_lo"] = np.where(np.isfinite(alo), (C - alo) / atr, np.nan)
    f["d_open"] = (C - bars.d_open[row]) / atr

    # --- structure
    f["consec"] = _consec(bars.c5)[j]
    bsh, bsl = _bars_since_extremes(bars.h5, bars.l5, bars.day5)
    f["bars_since_high"] = bsh[j]
    f["bars_since_low"] = bsl[j]
    ov = np.full(len(bars.k5), np.nan)
    if len(bars.k5) >= 12:
        w_h = sliding_window_view(bars.h5, 12)
        w_l = sliding_window_view(bars.l5, 12)
        den = w_h.max(axis=1) - w_l.min(axis=1)
        num = (w_h - w_l).sum(axis=1)
        ov[11:] = np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)
    f["overlap12"] = ov[j]

    # --- activity
    tv15_all = _rolling_window_sum(bars.k5, bars.tv5, t5, all5, 15)
    f["tv_rel"] = tv15_all[j] / same_slot_history(bars, tv15_all, "median", cfg)[j]
    f["spread_rel"] = bars.spread_pts[i_t] / _pooled_spread_median(bars, cfg)[row]

    # --- calendar
    f["min_since_resume"] = (t - resume.abs[row]).astype(float)
    tmod = t - day * MIN_PER_DAY
    f["hour_bucket"] = (np.searchsorted(np.asarray(cfg.hour_buckets), tmod, side="right") - 1).astype(float)
    f["weekday"] = weekday_of_day(day).astype(float)

    # --- previous day
    atr_d = wilder_atr(bars.d_high, bars.d_low, bars.d_close, cfg.atr_period)
    f["pd_ret"] = np.where(prev_ok, (bars.d_close[pcl] - bars.d_open[pcl]) / atr_d[pcl], np.nan)
    d_range = bars.d_high - bars.d_low
    f["pd_range_rel"] = np.where(prev_ok, d_range[pcl], np.nan) / _prev_row_median(d_range, cfg)[row]

    out = pd.DataFrame({k: np.asarray(f[k], dtype=float) for k in FEATURES})
    return out.replace([np.inf, -np.inf], np.nan)
