"""Tradeable window and decision moments (roadmap Section 2).

* ResumeTime(d) = the first M1 *close* of day d at which the last 5 M1 spreads of
  the day are each <= 1.5 x the median M1 spread of the previous trading day's
  bars with open time in [10:00, 21:30). If that is not met by 16:30 (or there
  is no previous day to compare with), ResumeTime(d) = 16:30.
* Window = [ResumeTime(d), 21:30). A decision moment is the close t of an M5 bar
  of day d with ResumeTime(d) <= t < 21:30, on a day that is neither quarantined
  nor a weekend day. Per-horizon validity (t + H <= 21:30) is applied in
  ``targets.py``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import DEFAULT, F1Config, MIN_PER_DAY
from .data import Bars, weekday_of_day

REASON_RULE, REASON_DEADLINE, REASON_NO_REF = 0, 1, 2


@dataclass
class Resume:
    """Per trading day (rows aligned with ``bars.days``)."""

    minute: np.ndarray      # ResumeTime as minute of day (close-time semantics)
    abs: np.ndarray         # ResumeTime as absolute minutes
    reason: np.ndarray      # REASON_*
    ref_spread: np.ndarray  # previous day's median spread (points), NaN if none


def resume_times(bars: Bars, cfg: F1Config = DEFAULT) -> Resume:
    n = bars.n_days
    minute = np.full(n, cfg.resume_deadline, dtype=np.int64)
    reason = np.full(n, REASON_NO_REF, dtype=np.int64)
    ref = np.full(n, np.nan)
    weekday = weekday_of_day(bars.days)
    prev = -1
    for k in range(n):
        s, e = bars.d_first[k], bars.d_last[k] + 1
        if prev >= 0:
            ps, pe = bars.d_first[prev], bars.d_last[prev] + 1
            mod = bars.t[ps:pe] % MIN_PER_DAY
            sel = (mod >= cfg.resume_ref_start) & (mod < cfg.resume_ref_end)
            if sel.any():
                ref[k] = float(np.median(bars.spread_pts[ps:pe][sel]))
        if not np.isnan(ref[k]):
            reason[k] = REASON_DEADLINE
            thr = cfg.resume_spread_mult * ref[k]
            ok = bars.spread_pts[s:e] <= thr
            nb = cfg.resume_n_bars
            if len(ok) >= nb:
                # all of the last nb spreads ok  <=>  window sum of ok == nb
                win = np.convolve(ok.astype(np.int64), np.ones(nb, dtype=np.int64), "valid")
                hit = np.flatnonzero(win == nb)
                if len(hit):
                    i = s + hit[0] + nb - 1
                    m = int(bars.tc[i] - bars.days[k] * MIN_PER_DAY)
                    if m <= cfg.resume_deadline:
                        minute[k] = m
                        reason[k] = REASON_RULE
        if weekday[k] < 5:
            prev = k
    return Resume(minute=minute, abs=bars.days * MIN_PER_DAY + minute, reason=reason, ref_spread=ref)


def decision_moments(bars: Bars, resume: Resume, excluded_days=(), cfg: F1Config = DEFAULT) -> np.ndarray:
    """M5 bar indices whose close is a decision moment."""
    row = bars.day_row(bars.day5)
    tmod = bars.tc5 - bars.day5 * MIN_PER_DAY
    ok = (tmod >= resume.minute[row]) & (tmod < cfg.window_end)
    ok &= weekday_of_day(bars.day5) < 5
    if len(excluded_days):
        ok &= ~np.isin(bars.day5, np.asarray(list(excluded_days), dtype=np.int64))
    return np.flatnonzero(ok)
