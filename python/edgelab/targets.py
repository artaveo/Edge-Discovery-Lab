"""Targets: what happened next, net of cost (roadmap Section 3).

For a decision moment t (M5 close) and horizon H:

* ``p0 = Bid_close(t)``, ``p1 = Bid_close(t+H)`` (as-of: the last M1 close <= t+H),
  ``move = p1 - p0``;
* ``spread(x) = spread_pts(x) * point`` of the same M1 bars;
* ``commission = 2 * 0.000016 * p0`` (open + close, per ounce, on the entry price);
* long net  = move - spread(t) - commission;
* short net = -move - spread(t+H) - commission.

Valid only if t + H <= 21:30 of the same day and the day still has a bar closing
at or after t + H. ``EOD`` exits at the last M1 close at or before 21:30 of the
day and is valid when that close is after t. Values are also given in ATR60(t)
units (Wilder ATR(14) on M5).
"""
from __future__ import annotations

import numpy as np

from .config import DEFAULT, F1Config, MIN_PER_DAY, horizon_name
from .data import Bars


def exit_time(bars: Bars, j: np.ndarray, h, cfg: F1Config = DEFAULT) -> np.ndarray:
    t = bars.tc5[j]
    if h == "EOD":
        return bars.day5[j] * MIN_PER_DAY + cfg.window_end
    return t + int(h)


def compute_targets(bars: Bars, moments: np.ndarray, atr5: np.ndarray, cfg: F1Config = DEFAULT) -> dict:
    """Return a dict of arrays aligned with ``moments`` (M5 indices).

    Keys: ``p0``, ``spread0``, ``commission``, and for each horizon name
    (H30, H60, H120, EOD): ``long_<H>``, ``short_<H>``, ``long_atr_<H>``,
    ``short_atr_<H>``, ``move_<H>``, ``exit_t_<H>`` (NaN / -1 where invalid).
    """
    j = np.asarray(moments, dtype=np.int64)
    point = bars.spec.point
    i0 = bars.last5[j]
    t = bars.tc5[j]
    d = bars.day5[j]
    row = bars.day_row(d)
    day_last_close = bars.tc[bars.d_last[row]]
    p0 = bars.c[i0]
    s0 = bars.spread_pts[i0] * point
    comm = 2.0 * cfg.commission_rate * p0
    atr = atr5[j]
    out = {"p0": p0, "spread0": s0, "commission": comm, "atr60": atr}
    end_abs = d * MIN_PER_DAY + cfg.window_end
    for h in cfg.horizons:
        name = horizon_name(h)
        tau = exit_time(bars, j, h, cfg)
        i1 = bars.asof_index(tau)
        if h == "EOD":
            valid = bars.tc[i1] > t
        else:
            valid = (tau <= end_abs) & (day_last_close >= tau)
        i1 = np.where(valid, i1, i0)
        move = bars.c[i1] - p0
        s1 = bars.spread_pts[i1] * point
        lng = np.where(valid, move - s0 - comm, np.nan)
        sht = np.where(valid, -move - s1 - comm, np.nan)
        out[f"move_{name}"] = np.where(valid, move, np.nan)
        out[f"long_{name}"] = lng
        out[f"short_{name}"] = sht
        with np.errstate(divide="ignore", invalid="ignore"):
            out[f"long_atr_{name}"] = np.where(atr > 0, lng / atr, np.nan)
            out[f"short_atr_{name}"] = np.where(atr > 0, sht / atr, np.nan)
        out[f"exit_t_{name}"] = np.where(valid, bars.tc[i1], -1)
    return out
