"""Data audit (roadmap Section 1).

Per day: minutes (bars), gaps > 5 min inside the session, zero/negative spreads,
duplicate timestamps, weekend bars. A day's session is ``[first bar, last bar]``
of that date; a gap is the number of missing M1 bars between two consecutive
bars of the day. A day with a gap > 30 min is **quarantined** (excluded, never
repaired). Weekend days are reported and also produce no decision moments.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DEFAULT, F1Config, MIN_PER_DAY
from .data import clean_m1, day_to_date, to_minutes, weekday_of_day, year_of_day


def _hhmm(m: int) -> str:
    m = int(m) % MIN_PER_DAY
    return f"{m // 60:02d}:{m % 60:02d}"


def audit_m1(df_raw: pd.DataFrame, cfg: F1Config = DEFAULT) -> dict:
    """Audit a raw M1 frame. Returns a JSON-serialisable report.

    ``report["quarantined_days"]`` and ``report["excluded_days"]`` hold day ids
    (days since 1970-01-01); ``report["days"]`` holds the per-day rows.
    """
    t_raw = to_minutes(df_raw["time"])
    dup_counts = Counter(t_raw[pd.Series(t_raw).duplicated(keep=False).to_numpy()] // MIN_PER_DAY)
    n_dup_total = int(pd.Series(t_raw).duplicated(keep="first").sum())
    df, _ = clean_m1(df_raw)
    t = to_minutes(df["time"])
    sp = df["spread_pts"].to_numpy(float)
    day = t // MIN_PER_DAY

    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    ends = np.r_[starts[1:], len(t)]
    days = day[starts]

    first_mod = (t[starts] % MIN_PER_DAY)
    last_mod = (t[ends - 1] % MIN_PER_DAY)
    modal_start = int(pd.Series(first_mod).mode().iloc[0]) if len(days) else 0
    modal_end = int(pd.Series(last_mod).mode().iloc[0]) if len(days) else 0

    rows = []
    quarantined, excluded = [], []
    for k, d in enumerate(days):
        s, e = starts[k], ends[k]
        tt = t[s:e]
        gaps = np.diff(tt) - 1
        big = np.flatnonzero(gaps > cfg.gap_report_min)
        gap_list = [{"after": _hhmm(tt[i]), "missing_min": int(gaps[i])} for i in big]
        max_gap = int(gaps.max()) if len(gaps) else 0
        wd = int(weekday_of_day(d))
        weekend = wd >= 5
        reasons = []
        if max_gap > cfg.gap_quarantine_min:
            reasons.append(f"gap>{cfg.gap_quarantine_min}min")
        row = {
            "date": day_to_date(d),
            "day_id": int(d),
            "weekday": wd,
            "bars": int(e - s),
            "first_bar": _hhmm(tt[0]),
            "last_bar": _hhmm(tt[-1]),
            "late_start": bool(first_mod[k] > modal_start),
            "early_close": bool(last_mod[k] < modal_end),
            "gaps_gt5": gap_list,
            "max_gap_min": max_gap,
            "zero_spread_bars": int((sp[s:e] == 0).sum()),
            "negative_spread_bars": int((sp[s:e] < 0).sum()),
            "duplicate_timestamps": int(dup_counts.get(d, 0)),
            "weekend": weekend,
            "quarantined": bool(reasons),
            "quarantine_reasons": reasons,
        }
        rows.append(row)
        if reasons:
            quarantined.append(int(d))
        if reasons or weekend:
            excluded.append(int(d))

    years = sorted(set(int(y) for y in year_of_day(days))) if len(days) else []
    per_year = {}
    for y in years:
        ry = [r for r in rows if r["date"].startswith(str(y))]
        per_year[str(y)] = {
            "days": len(ry),
            "bars": int(sum(r["bars"] for r in ry)),
            "quarantined": int(sum(r["quarantined"] for r in ry)),
            "weekend_days": int(sum(r["weekend"] for r in ry)),
            "days_with_gap_gt5": int(sum(bool(r["gaps_gt5"]) for r in ry)),
            "zero_spread_bars": int(sum(r["zero_spread_bars"] for r in ry)),
            "negative_spread_bars": int(sum(r["negative_spread_bars"] for r in ry)),
        }
    return {
        "rows_raw": int(len(df_raw)),
        "rows_clean": int(len(df)),
        "duplicate_timestamps_dropped": n_dup_total,
        "first_bar": str(df["time"].iloc[0]) if len(df) else None,
        "last_bar": str(df["time"].iloc[-1]) if len(df) else None,
        "modal_session_start": _hhmm(modal_start),
        "modal_session_last_bar": _hhmm(modal_end),
        "rules": {
            "session": "per day [first bar, last bar]",
            "gap": "missing M1 bars between consecutive bars of a day",
            "report_gap_gt_min": cfg.gap_report_min,
            "quarantine_gap_gt_min": cfg.gap_quarantine_min,
            "weekend_days": "reported; no decision moments",
            "duplicates": "keep first, count reported",
        },
        "per_year": per_year,
        "n_days": len(rows),
        "n_quarantined": len(quarantined),
        "quarantined_days": quarantined,
        "quarantined_dates": [day_to_date(d) for d in quarantined],
        "excluded_days": excluded,
        "days": rows,
    }


def write_audit(report: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1), encoding="utf-8")
