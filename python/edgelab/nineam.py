"""Phase F6: the New York 9 AM candle sweep + MSS (EdgeLab_Roadmap.md Section 14).

Usage (F6 Step C, from ``python/``), once::

    python -m edgelab.nineam --nas ../data/f6 --gold ../data --out ../research/f6

A human-defined setup taken from a video (Section 14.1). One fixed configuration per
instrument, nothing fitted: the Nasdaq CFD decides the verdict, XAUUSD is descriptive only.

Rules (Section 14.4, for a long; a short is mirrored exactly). All levels are M1 Bid.
1. H9 / L9 = high / low of the M1 bars 9:00..9:59 New York; they exist from 10:00 NY.
2. Window = M1 bars opening 10:00..10:59 NY.
3. The first window bar with low < L9 (a wick is enough) sweeps the low -> the day is long-only;
   the first sweep decides the day. A bar sweeping both sides skips the day.
4. X = the lowest low from the sweep bar to the current bar.
5. Pivot high = a bar whose high is strictly above the highs of the bars before and after it.
6. M = the high of the most recent pivot high before the bar of X (updates with every new low).
7. Break = the first window bar after the sweep (the sweep bar included) that closes above M.
8. At the break bar's close a buy limit at M is placed. It fills when Bid low + spread <= M, at M.
   It is cancelled at the close of the 10:59 NY bar, or when Bid high >= TP comes first.
9. SL = X (no buffer); r = M - X.  10. TP = the nearer of M + 3r and H9; no order when H9 <= M.
11. One trade per day; the trade ends only at SL or TP (no time exit, overnight allowed); a trade
    still open at the end of the data closes at the last bar and is counted as unfinished.

Pre-registered details not spelled out in Section 14 (frozen here, before any F6 run):

Time (Section 14.3)
* New York time = broker time - offset; the default offset is 7 h (broker 00:00 = NY 17:00).
* Offset check on the Nasdaq CFD: per ISO week (broker dates), for each candidate cash-open
  minute c in {15:30, 16:30, 17:30} broker, the jump = median over the week's days of
  mean tick volume of [c, c+5) / mean tick volume of [c-5, c). The week's cash open is the
  candidate with the largest jump if that jump is >= 1.5 and >= 1.2 x the second largest;
  otherwise 16:30. offset = 7 + (c - 16:30) / 60 h.
* Both symbols come from the same FundedNext server clock, so the Nasdaq weeks' offsets are
  applied to XAUUSD as well. Weeks without Nasdaq data use 7 h. The check is also computed
  on XAUUSD and reported (its 8:30 NY news minute can confound it; it decides nothing).
* Days: the broker calendar date; weekends are skipped. The 9 AM hour of a day is
  broker [9:00 + offset, 10:00 + offset) of the same date.
* A day is skipped when the 9 AM hour has no bar, or when [9:00, 11:00) NY has a gap of
  more than 5 missing M1 bars (the range edges count: a first bar later than 9:05 NY or a last
  bar earlier than 10:54 NY is a gap).

Setup
* Pivots are searched on the M1 bars of the same broker day only.
* A new low of X must be strictly lower; X's bar is the first bar that printed it.
* No pivot before X's bar -> no M (no break is possible until one exists).
* r <= 0 -> no order (cannot happen with Bid data, guarded anyway).
* A TP exactly equal for both candidates is labelled "3R".
* The limit is live from the bar after the break bar. On a bar that both touches the TP and
  fills, the order is cancelled (the order inside the bar is unknown; no trade is assumed).

Exits (Section 14.5, as Section 12.3)
* Long SL at Bid low <= SL, TP at Bid high >= TP; short SL at Ask high >= SL, TP at
  Ask low <= TP. SL wins a same-bar conflict; a stop gap-fills at the worse open.
* Fill bar: checked for the SL (counted as a same-bar conflict), never for the TP.
* Result in R = net / r, net = (exit - entry) x side - commission; also USD per lot
  (net x contract size). Commission = 2 x rate x entry price: XAUUSD 0.000016 (Section 3.3);
  the Nasdaq rate is ``NAS_COMMISSION_RATE``, which the owner confirms before Step C.

Statistics (Section 14.6)
* 2020-07..12 reported only; 2021 and 2022 decide. Bootstrap: day-block, 10,000 reps,
  seed 20260930, lower 5% quantile, over 2021-2022 trades.
* Direction flip: 200 permutations, default_rng(20260930); each evaluation day's trade is
  replaced with probability 1/2 by the mirrored trade (same fill bar and entry M, the other
  side, stop M -/+ r, target 3r, same M1 path, same exit rules). p = share of permutations
  whose mean net R over 2021-2022 >= the real mean (``stats.permutation_pvalue``).
* The run refuses to start when ``<out>/report.json`` exists; every run goes to the ledger.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DEFAULT, F1_START_DATE, F1_YEARS, MIN_PER_DAY, hm
from .data import (Bars, InstrumentSpec, assert_no_forbidden_rows, build_bars, check_years_allowed, clean_m1,
                   load_f1, read_manifest, read_year_csv, sha256_file, spec_from_manifest, to_minutes,
                   weekday_of_day, year_of_day)
from .nyclose import _summ, path_exit
from .report import _esc, _fmt_t, _jsonable
from .stats import day_block_bootstrap, max_drawdown, permutation_pvalue

DEFAULT_OFFSET_H = 7
CASH_OPEN = hm(16, 30)              # broker minute of 9:30 NY at the default offset
OFFSET_SHIFTS = (-1, 0, 1)          # hours: candidate cash-open minutes 15:30 / 16:30 / 17:30
JUMP_MIN, JUMP_MARGIN = 1.5, 1.2
NINE, WINDOW_END = hm(9), hm(11)    # New York minutes
MAX_GAP_MIN = 5
K_R = 3.0
GOLD_COMMISSION_RATE = DEFAULT.commission_rate
NAS_COMMISSION_RATE = None          # owner confirms the FundedNext index commission before Step C
EVAL_YEARS = (2021, 2022)
MIN_TRADES_PER_YEAR = 50
N_PERM = 200
N_BOOT = DEFAULT.final_boot
SEED = DEFAULT.seed
P_PASS, P_WEAK = 0.05, 0.10
N_CHARTS = 10
REASONS = {0: "END", 1: "SL", 2: "TP"}


# ----------------------------------------------------------------------------- data

def load_f6(data_dir: Path, verify: bool = True):
    """Load the Nasdaq CFD export (``data/f6``): the files the manifest lists, 2020-07 .. 2022 only.
    Returns (DataFrame, InstrumentSpec, manifest)."""
    data_dir = Path(data_dir)
    manifest = read_manifest(data_dir)
    if str(manifest.get("phase", "")).upper() != "F6" or str(manifest.get("symbol", "")).upper().startswith("XAU"):
        raise ValueError("data/f6 must hold the F6 Nasdaq CFD export (manifest phase F6, not XAUUSD)")
    files = manifest.get("files", [])
    check_years_allowed([int(f["year"]) for f in files])
    frames = []
    for f in files:
        path = data_dir / f["file"]
        if verify and sha256_file(path).lower() != str(f["sha256"]).lower():
            raise ValueError(f"{f['file']}: sha256 mismatch")
        df = read_year_csv(path)
        if verify and int(f["rows"]) != len(df):
            raise ValueError(f"{f['file']}: row count {len(df)} != manifest {f['rows']}")
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    assert_no_forbidden_rows(df)
    return df, spec_from_manifest(manifest), manifest


def weekday_bars(df_raw: pd.DataFrame, spec: InstrumentSpec) -> Bars:
    df, _ = clean_m1(df_raw)
    wd = weekday_of_day(to_minutes(df["time"]) // MIN_PER_DAY)
    return build_bars(df.loc[wd < 5].reset_index(drop=True), spec)


def week_of_day(day_id) -> np.ndarray:
    """ISO-style week id (weeks start on Monday; 1970-01-01 was a Thursday)."""
    return (np.asarray(day_id, dtype=np.int64) + 3) // 7


# ----------------------------------------------------------------------------- time check (Section 14.3)

def _minute_matrix(bars: Bars) -> np.ndarray:
    """(days, 1440) tick volume by broker minute of day (NaN where there is no bar)."""
    row = np.searchsorted(bars.days, bars.day)
    m = np.full((bars.n_days, MIN_PER_DAY), np.nan)
    m[row, bars.t % MIN_PER_DAY] = bars.tv
    return m


def cash_open_check(bars: Bars) -> dict:
    """Per week: the jump at each candidate cash-open minute and the chosen offset (hours)."""
    tvm = _minute_matrix(bars)
    cands = [CASH_OPEN + 60 * s for s in OFFSET_SHIFTS]
    with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)          # days without bars around c
        jumps = np.stack([np.nanmean(tvm[:, c:c + 5], axis=1) / np.nanmean(tvm[:, c - 5:c], axis=1)
                          for c in cands], axis=1)                       # (days, 3)
    weeks = week_of_day(bars.days)
    out = {}
    for w in np.unique(weeks):
        js = jumps[weeks == w]
        js = js[np.isfinite(js).all(axis=1)]
        if len(js) == 0:
            continue
        med = np.median(js, axis=0)
        order = np.argsort(-med)
        best, second = med[order[0]], med[order[1]]
        shift = OFFSET_SHIFTS[order[0]] if (best >= JUMP_MIN and best >= JUMP_MARGIN * second) else 0
        out[int(w)] = {"jumps": [float(x) for x in med], "offset_h": DEFAULT_OFFSET_H + int(shift), "days": int(len(js))}
    return out


def day_offsets(bars: Bars, week_check: dict | None) -> np.ndarray:
    """Offset (hours) per day row: from the week check when it has the week, else 7."""
    weeks = week_of_day(bars.days)
    wc = week_check or {}
    return np.array([wc.get(int(w), {}).get("offset_h", DEFAULT_OFFSET_H) for w in weeks], dtype=np.int64)


# ----------------------------------------------------------------------------- one day

@dataclass
class Setup:
    side: int          # +1 long / -1 short
    entry: float       # M
    stop: float        # X
    tp: float
    tp_type: str       # "3R" / "9AM"
    r: float
    fill_bar: int      # global M1 index
    t_entry: int       # close time of the fill bar
    H9: float
    L9: float
    sweep_bar: int
    break_bar: int
    pivot_bar: int
    x_bar: int


def _last_pivot_before(H: np.ndarray) -> np.ndarray:
    """lp[k] = the index of the most recent pivot high strictly before k (-1 if none)."""
    n = len(H)
    piv = np.zeros(n, dtype=bool)
    if n >= 3:
        piv[1:-1] = (H[1:-1] > H[:-2]) & (H[1:-1] > H[2:])
    idx = np.where(piv, np.arange(n), -1)
    lp = np.maximum.accumulate(np.r_[-1, idx[:-1]]) if n else np.zeros(0, dtype=np.int64)
    return lp.astype(np.int64)


def day_setup(bars: Bars, row: int, offset_h: int) -> tuple[dict, Setup | None]:
    """Run the Section 14.4 rules on one broker day. Returns (funnel flags, setup or None)."""
    flags = {"used": False, "sweep": 0, "break": False, "order": False, "fill": False, "skip": ""}
    i0, i1 = int(bars.d_first[row]), int(bars.d_last[row]) + 1
    day0 = int(bars.days[row]) * MIN_PER_DAY
    nine = day0 + NINE + 60 * offset_h
    t = bars.t[i0:i1]
    # quarantine: 9 AM hour present, no gap > 5 min inside [9:00, 11:00) NY
    rng_ = (t >= nine) & (t < nine + (WINDOW_END - NINE))
    tt = t[rng_]
    if not ((tt >= nine) & (tt < nine + 60)).any():
        flags["skip"] = "no 9 AM hour"
        return flags, None
    edges = np.r_[nine - 1, tt, nine + (WINDOW_END - NINE)]
    if (np.diff(edges) - 1).max() > MAX_GAP_MIN:
        flags["skip"] = "gap > 5 min in 9:00-11:00 NY"
        return flags, None
    flags["used"] = True
    h, l, c = bars.h[i0:i1], bars.l[i0:i1], bars.c[i0:i1]
    sp = bars.spread_pts[i0:i1] * bars.spec.point
    hour = (t >= nine) & (t < nine + 60)
    H9, L9 = float(h[hour].max()), float(l[hour].min())
    win = np.flatnonzero((t >= nine + 60) & (t < nine + (WINDOW_END - NINE)))
    if len(win) == 0:
        return flags, None
    up = win[h[win] > H9]
    dn = win[l[win] < L9]
    first_up = int(up[0]) if len(up) else np.iinfo(np.int64).max
    first_dn = int(dn[0]) if len(dn) else np.iinfo(np.int64).max
    if first_up == first_dn:
        if len(up):
            flags["skip"] = "both sides swept by one bar"
        return flags, None
    side = 1 if first_dn < first_up else -1          # low swept -> long
    s = min(first_up, first_dn)
    flags["sweep"] = side
    # work in "long space": a short negates the Bid prices (rules 3-7 use Bid only)
    if side > 0:
        HH, LL, CC, far = h, l, c, H9
    else:
        HH, LL, CC, far = -l, -h, -c, -L9
    lp = _last_pivot_before(HH)
    w_end = int(win[-1])
    X, iX, brk, M, ip = np.inf, -1, -1, np.nan, -1
    for i in range(s, w_end + 1):
        if LL[i] < X:
            X, iX = float(LL[i]), i
            ip = int(lp[iX])
            M = float(HH[ip]) if ip >= 0 else np.nan
        if np.isfinite(M) and CC[i] > M:
            brk = i
            break
    if brk < 0:
        return flags, None
    flags["break"] = True
    r = M - X
    if r <= 0 or far <= M:
        return flags, None
    tp_l = min(M + K_R * r, far)
    tp_type = "3R" if M + K_R * r <= far else "9AM"
    entry, stop, tp = (M, X, tp_l) if side > 0 else (-M, -X, -tp_l)
    flags["order"] = True
    for j in range(brk + 1, w_end + 1):
        if side > 0:
            fill, tp_hit = l[j] + sp[j] <= entry, h[j] >= tp
        else:
            fill, tp_hit = h[j] >= entry, l[j] + sp[j] <= tp
        if tp_hit:
            return flags, None
        if fill:
            flags["fill"] = True
            return flags, Setup(side=side, entry=float(entry), stop=float(stop), tp=float(tp), tp_type=tp_type,
                                r=float(r), fill_bar=i0 + j, t_entry=int(bars.tc[i0 + j]), H9=H9, L9=L9,
                                sweep_bar=i0 + s, break_bar=i0 + brk, pivot_bar=i0 + ip, x_bar=i0 + iX)
    return flags, None


# ----------------------------------------------------------------------------- the trade on the M1 path

def resolve(bars: Bars, side: int, entry: float, stop: float, tp: float, fill_bar: int):
    """Exit of one trade with no time stop: (price, exit bar, reason 0 end-of-data / 1 SL / 2 TP,
    conflict). The path is scanned in growing chunks up to the last bar of the data."""
    n_last = len(bars.t) - 1
    span = 2 * MIN_PER_DAY
    while True:
        hi = min(n_last, fill_bar + span)
        px, ib, reason, conflict = path_exit(bars, side, entry, stop, tp, fill_bar + 1, hi, fill_bar, True)
        if reason != 0 or hi == n_last:
            return px, ib, reason, bool(conflict or (reason == 1 and ib == fill_bar))
        span *= 4


def trade_result(bars: Bars, st: Setup, commission_rate: float, flip: bool = False) -> dict:
    side = -st.side if flip else st.side
    if flip:
        stop, tp = st.entry - side * st.r, st.entry + side * K_R * st.r
    else:
        stop, tp = st.stop, st.tp
    px, ib, reason, conflict = resolve(bars, side, st.entry, stop, tp, st.fill_bar)
    comm = 2.0 * commission_rate * st.entry
    net = (px - st.entry) * side - comm
    return {"r": net / st.r, "usd_lot": net * bars.spec.contract_size, "exit_i": int(ib),
            "exit_t": int(bars.tc[ib]), "reason": int(reason), "conflict": bool(conflict), "exit_px": float(px)}


# ----------------------------------------------------------------------------- one instrument

def simulate(bars: Bars, offsets: np.ndarray, commission_rate: float) -> dict:
    """All days: the funnel rows and the trades (real and flipped results)."""
    funnel, trades = [], []
    for row in range(bars.n_days):
        flags, st = day_setup(bars, row, int(offsets[row]))
        d = int(bars.days[row])
        funnel.append({"day": d, **flags})
        if st is None:
            continue
        res = trade_result(bars, st, commission_rate)
        flp = trade_result(bars, st, commission_rate, flip=True)
        trades.append({"day": d, "side": st.side, "entry": st.entry, "stop": st.stop, "tp": st.tp,
                       "tp_type": st.tp_type, "risk": st.r, "t_entry": st.t_entry, "H9": st.H9, "L9": st.L9,
                       "fill_bar": st.fill_bar, "sweep_bar": st.sweep_bar, "break_bar": st.break_bar,
                       "pivot_bar": st.pivot_bar, "x_bar": st.x_bar, "offset_h": int(offsets[row]),
                       **res, "r_flip": flp["r"],
                       "hold_min": res["exit_t"] - st.t_entry,
                       "overnight": bool(res["exit_t"] // MIN_PER_DAY > st.t_entry // MIN_PER_DAY)})
    return {"funnel": funnel, "trades": trades}


def _arr(trades: list, key: str, dtype=float) -> np.ndarray:
    return np.array([t[key] for t in trades], dtype=dtype) if trades else np.zeros(0, dtype=dtype)


def flip_pvalue(days: np.ndarray, r: np.ndarray, r_flip: np.ndarray, n_perm: int = N_PERM, seed: int = SEED):
    """(p, null means): every evaluation day's trade is flipped with probability 1/2."""
    if len(r) == 0:
        return 1.0, np.zeros(0)
    ud, di = np.unique(days, return_inverse=True)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for k in range(n_perm):
        coin = rng.random(len(ud)) < 0.5
        null[k] = float(np.where(coin[di], r_flip, r).mean())
    return permutation_pvalue(float(r.mean()), null), null


def evaluate(sim: dict, n_perm: int = N_PERM) -> dict:
    tr = sim["trades"]
    year = year_of_day(_arr(tr, "day", np.int64)) if tr else np.zeros(0, dtype=np.int64)
    r, rf = _arr(tr, "r"), _arr(tr, "r_flip")
    days = _arr(tr, "day", np.int64)
    m = np.isin(year, EVAL_YEARS)
    res = {**_summ(r[m])}
    res["per_year"] = {str(y): _summ(r[year == y]) for y in (2020,) + EVAL_YEARS}
    res["boot_lower_r"] = (day_block_bootstrap(r[m], days[m], N_BOOT, SEED, DEFAULT.alpha)["lower"]
                           if m.any() else float("nan"))
    res["p_flip"], null = flip_pvalue(days[m], r[m], rf[m], n_perm)
    order = np.argsort(_arr(tr, "t_entry", np.int64)[m], kind="mergesort")
    res["max_dd_r"] = max_drawdown(r[m][order]) if m.any() else 0.0
    res["null_quantiles"] = ({q: float(np.quantile(null, q)) for q in (0.5, 0.9, 0.95)} if len(null) else {})
    if m.any():
        sub = [t for t, ok in zip(tr, m) if ok]
        side, tpt = _arr(sub, "side"), np.array([t["tp_type"] for t in sub])
        reason = _arr(sub, "reason", np.int64)
        res["splits"] = {"side": {"long": _summ(r[m][side > 0]), "short": _summ(r[m][side < 0])},
                         "target": {"3R": _summ(r[m][tpt == "3R"]), "9AM side": _summ(r[m][tpt == "9AM"])}}
        res["exit_reasons"] = {REASONS[k]: int((reason == k).sum()) for k in REASONS}
        res["hold_min_median"] = float(np.median(_arr(sub, "hold_min")))
        res["overnight_share"] = float(np.mean(_arr(sub, "overnight", bool)))
        res["conflict_share"] = float(np.mean(_arr(sub, "conflict", bool)))
        res["mean_usd_lot"] = float(np.mean(_arr(sub, "usd_lot")))
        res["unfinished"] = int((reason == 0).sum())
    fy = year_of_day(np.array([f["day"] for f in sim["funnel"]], dtype=np.int64)) if sim["funnel"] else np.zeros(0)
    res["funnel"] = {}
    for y in (2020,) + EVAL_YEARS:
        fs = [f for f, yy in zip(sim["funnel"], fy) if yy == y]
        res["funnel"][str(y)] = {"days": len(fs), "used": sum(f["used"] for f in fs),
                                 "sweep": sum(f["sweep"] != 0 for f in fs), "break": sum(f["break"] for f in fs),
                                 "order": sum(f["order"] for f in fs), "fill": sum(f["fill"] for f in fs),
                                 "trades": int((year == y).sum())}
    res["skipped"] = {}
    for f in sim["funnel"]:
        if f["skip"]:
            res["skipped"][f["skip"]] = res["skipped"].get(f["skip"], 0) + 1
    return res


def verdict(res: dict) -> str:
    py = [res["per_year"][str(y)] for y in EVAL_YEARS]
    pos = all(v["trades"] > 0 and v["mean_r"] > 0 for v in py)
    res["checks"] = {"positive_each_year": pos,
                     "boot_lower_positive": bool(np.isfinite(res["boot_lower_r"]) and res["boot_lower_r"] > 0),
                     "flip_p": res["p_flip"] < P_PASS,
                     "min_50_trades_each_year": all(v["trades"] >= MIN_TRADES_PER_YEAR for v in py)}
    if all(res["checks"].values()):
        return "F6_PASS"
    return "F6_WEAK" if pos and res["p_flip"] < P_WEAK else "F6_STOP"


def run_instrument(bars: Bars, week_check: dict | None, commission_rate: float, n_perm: int = N_PERM) -> dict:
    t0 = time.time()
    offsets = day_offsets(bars, week_check)
    sim = simulate(bars, offsets, commission_rate)
    res = evaluate(sim, n_perm)
    res["verdict_rule"] = verdict(res)
    res["offsets_used"] = {str(k): int((offsets == k).sum()) for k in np.unique(offsets)}
    return {"sim": sim, "res": res, "seconds": time.time() - t0}


# ----------------------------------------------------------------------------- charts

def svg_trade(bars: Bars, tr: dict, title: str) -> str:
    """M1 candles from 30 min before the 9 AM candle to the exit (at most 10 h after the 9 AM
    candle), drawn like the video: 9 AM lines, sweep, MSS, entry, SL and TP."""
    nine = (tr["t_entry"] // MIN_PER_DAY) * MIN_PER_DAY + NINE + 60 * tr["offset_h"]
    lo_t = nine - 30
    hi_t = min(max(tr["exit_t"] + 10, tr["t_entry"] + 60), nine + 600)
    i0, i1 = np.searchsorted(bars.t, lo_t), np.searchsorted(bars.t, hi_t)
    t, o, h, l, c = bars.t[i0:i1], bars.o[i0:i1], bars.h[i0:i1], bars.l[i0:i1], bars.c[i0:i1]
    W, H, pad = 1100, 460, 50
    if len(t) == 0:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="60"><text x="8" y="30">no bars</text></svg>'
    lv = [tr["H9"], tr["L9"], tr["entry"], tr["stop"], tr["tp"]]
    pmin, pmax = min(float(l.min()), *lv), max(float(h.max()), *lv)
    span = (pmax - pmin) or 1.0

    def x(m):
        return pad + (m - lo_t) / max(hi_t - lo_t, 1) * (W - 2 * pad - 60)

    def y(p):
        return pad + (pmax - p) / span * (H - 2 * pad)
    cw = max(0.8, (W - 2 * pad - 60) / max(hi_t - lo_t, 1) * 0.7)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="11">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           f'<text x="{pad}" y="20" font-size="12" fill="#111">{_esc(title)}</text>',
           f'<rect x="{x(nine):.1f}" y="{pad}" width="{x(nine + 60) - x(nine):.1f}" height="{H - 2 * pad}" fill="#eef2ff"/>',
           f'<rect x="{x(nine + 60):.1f}" y="{pad}" width="{x(nine + 120) - x(nine + 60):.1f}" height="{H - 2 * pad}" fill="#fff7e6"/>']
    for i in range(len(t)):
        xm = x(t[i] + 0.5)
        col = "#1a7f37" if c[i] >= o[i] else "#111111"
        out.append(f'<line x1="{xm:.1f}" y1="{y(h[i]):.1f}" x2="{xm:.1f}" y2="{y(l[i]):.1f}" stroke="{col}"/>')
        top, bot = y(max(o[i], c[i])), y(min(o[i], c[i]))
        out.append(f'<rect x="{xm - cw / 2:.1f}" y="{top:.1f}" width="{cw:.1f}" height="{max(bot - top, 0.8):.1f}" fill="{col}"/>')
    x_end = W - pad - 60
    for p, col, lab, dash in ((tr["H9"], "#1f4fd1", "9AM high", ""), (tr["L9"], "#1f4fd1", "9AM low", ""),
                              (tr["entry"], "#111111", "MSS / entry", "5 3"), (tr["stop"], "#cf222e", "SL", "3 3"),
                              (tr["tp"], "#1a7f37", f"TP ({tr['tp_type']})", "3 3")):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<line x1="{pad}" y1="{y(p):.1f}" x2="{x_end:.1f}" y2="{y(p):.1f}" stroke="{col}"{da}/>')
        out.append(f'<text x="{x_end + 4:.1f}" y="{y(p) + 4:.1f}" fill="{col}">{lab} {p:.2f}</text>')
    for key, col, lab in (("sweep_t", "#c026d3", "sweep"), ("t_entry", "#1f6feb", "fill"), ("exit_t", "#d97706", "exit")):
        m = tr[key]
        if lo_t <= m <= hi_t:
            out.append(f'<line x1="{x(m):.1f}" y1="{pad}" x2="{x(m):.1f}" y2="{H - pad}" stroke="{col}" stroke-dasharray="2 3"/>')
            out.append(f'<text x="{x(m) + 2:.1f}" y="{pad - 4}" fill="{col}">{lab}</text>')
    for m in range(lo_t - lo_t % 30 + 30, hi_t, 30):
        ny = (m - 60 * tr["offset_h"]) % MIN_PER_DAY
        out.append(f'<text x="{x(m) - 14:.1f}" y="{H - pad + 16}" fill="#555">{ny // 60:02d}:{ny % 60:02d}</text>')
    out.append(f'<text x="{pad}" y="{H - 8}" fill="#555">time axis: New York</text>')
    out.append("</svg>")
    return "\n".join(out)


# ----------------------------------------------------------------------------- report

def _f(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def write_report(runs: dict, out_dir: Path, week_checks: dict, meta: dict, tests_summary: str = "") -> dict:
    """``runs`` = {"nas": run or None, "gold": run or None} (``run_instrument`` outputs plus "bars")."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng([SEED, 6])
    charts = {}
    for key, run in runs.items():
        if run is None:
            continue
        bars, tr = run["bars"], run["sim"]["trades"]
        idx = [i for i, t in enumerate(tr) if int(year_of_day(np.int64(t["day"]))) in EVAL_YEARS]
        pick = sorted(rng.choice(idx, size=min(N_CHARTS, len(idx)), replace=False).tolist()) if idx else []
        cdir = out_dir / "charts" / key
        charts[key] = []
        for n_ex, i in enumerate(pick):
            t = dict(tr[i])
            t["sweep_t"] = int(bars.t[t["sweep_bar"]])
            title = (f"{key.upper()} {'LONG' if t['side'] > 0 else 'SHORT'} | fill {_fmt_t(t['t_entry'])} (broker) -> "
                     f"{_fmt_t(t['exit_t'])} {REASONS[t['reason']]} | {t['r']:+.2f} R | risk {t['risk']:.2f}")
            cdir.mkdir(parents=True, exist_ok=True)
            fn = cdir / f"ex_{n_ex + 1:02d}.svg"
            fn.write_text(svg_trade(bars, t, title), encoding="utf-8")
            charts[key].append({"file": str(fn.relative_to(out_dir)).replace("\\", "/"), "r": float(t["r"])})
    nas = runs.get("nas")
    summary = {
        "phase": "F6", "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "verdict": nas["res"]["verdict_rule"] if nas else None, "eval_years": list(EVAL_YEARS), "n_perm": N_PERM,
        "meta": meta, "week_checks": week_checks,
        "instruments": {k: {**r["res"], "seconds": r["seconds"], "trade_list": r["sim"]["trades"]}
                        for k, r in runs.items() if r is not None},
        "charts": charts,
    }
    (out_dir / "report.json").write_text(json.dumps(_jsonable(summary), indent=1), encoding="utf-8")
    (out_dir / "report.md").write_text(_markdown(summary, tests_summary), encoding="utf-8")
    with open(out_dir / "trials_ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at_utc": summary["generated_at_utc"], "phase": "F6", "verdict": summary["verdict"],
                            "configurations": 1, "descriptive": ["XAUUSD"], "n_perm": N_PERM}) + "\n")
    return summary


def _markdown(s: dict, tests_summary: str) -> str:
    L = ["# Edge Discovery Lab — Phase F6 report (New York 9 AM candle sweep + MSS)", "",
         f"**Verdict (Nasdaq CFD): `{s['verdict']}`** · XAUUSD is descriptive only", "",
         f"Generated {s['generated_at_utc']} · one fixed configuration per instrument · "
         f"{s['n_perm']} direction-flip permutations", "", "## Data and time", ""]
    for k, v in s["meta"].items():
        L.append(f"- {k}: {v}")
    for k, wc in s["week_checks"].items():
        offs = {}
        for w in wc.values():
            offs[w["offset_h"]] = offs.get(w["offset_h"], 0) + 1
        L.append(f"- cash-open check on {k}: weeks per offset {dict(sorted(offs.items()))}")
    for key, r in s["instruments"].items():
        role = "decides the verdict" if key == "nas" else "descriptive only"
        L += ["", f"## {key.upper()} ({role}) — rule result `{r['verdict_rule']}`", "",
              "| Year | Days | Used | Sweep | Break | Order | Fill | Trades | Win % | Mean R |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for y, fu in r["funnel"].items():
            py = r["per_year"][y]
            L.append(f"| {y} | {fu['days']} | {fu['used']} | {fu['sweep']} | {fu['break']} | {fu['order']} | {fu['fill']} | "
                     f"{fu['trades']} | {_f(100 * py['win_rate'], 1) if py['trades'] else '—'} | {_f(py['mean_r'])} |")
        L += ["", f"- 2021–2022: {r['trades']} trades, win {_f(100 * r['win_rate'], 1) if r['trades'] else '—'}%, "
                  f"avg win {_f(r['avg_win_r'], 2)} R, avg loss {_f(r['avg_loss_r'], 2)} R, mean {_f(r['mean_r'])} R",
              f"- bootstrap lower 95% {_f(r['boot_lower_r'])} R · flip p {_f(r['p_flip'])} · max drawdown {_f(r['max_dd_r'], 1)} R",
              f"- checks: {r.get('checks')}", f"- skipped days: {r['skipped']}"]
        if "splits" in r:
            for name, parts in r["splits"].items():
                L.append(f"- {name}: " + "; ".join(f"{k}: {v['trades']} trades, {_f(v['mean_r'])} R" for k, v in parts.items()))
            L.append(f"- exits {r['exit_reasons']} · median hold {_f(r['hold_min_median'], 0)} min · overnight "
                     f"{_f(100 * r['overnight_share'], 1)}% · same-bar SL {_f(100 * r['conflict_share'], 1)}% · "
                     f"mean {_f(r['mean_usd_lot'], 2)} USD/lot · unfinished {r['unfinished']}")
        ch = s["charts"].get(key, [])
        if ch:
            L.append("- charts: " + ", ".join(f"[{i + 1}]({c['file']})" for i, c in enumerate(ch)))
    nas = s["instruments"].get("nas")
    L += ["", "## Completion record", "", "```", "F6 — COMPLETE", f"Date: {s['generated_at_utc'][:10]}",
          f"Tests: {tests_summary or '...'}", f"Result: {s['verdict']}"]
    for key, r in s["instruments"].items():
        L.append(f"  {key:>4}: trades {r['trades']:>4}  mean {_f(r['mean_r'])} R  2021 {_f(r['per_year']['2021']['mean_r'])}"
                 f"  2022 {_f(r['per_year']['2022']['mean_r'])}  boot_low {_f(r['boot_lower_r'])}  p {_f(r['p_flip'])}")
    if nas is None:
        L.append("  (no Nasdaq data)")
    L += ["```", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Edge Discovery Lab F6 run")
    ap.add_argument("--nas", default="../data/f6")
    ap.add_argument("--gold", default="../data")
    ap.add_argument("--out", default="../research/f6")
    ap.add_argument("--tests-summary", default="")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if (out / "report.json").exists():
        print("REFUSED: research/f6/report.json exists; F6 runs once.", flush=True)
        return 2
    if NAS_COMMISSION_RATE is None:
        print("REFUSED: NAS_COMMISSION_RATE is not set (owner confirms it before Step C).", flush=True)
        return 2
    df, spec, man_n = load_f6(Path(a.nas))
    nas_bars = weekday_bars(df, spec)
    wc_nas = cash_open_check(nas_bars)
    dg, spec_g, man_g = load_f1(Path(a.gold), F1_YEARS)
    gold_bars = weekday_bars(dg, spec_g)
    wc_gold = cash_open_check(gold_bars)
    runs = {"nas": run_instrument(nas_bars, wc_nas, NAS_COMMISSION_RATE),
            "gold": run_instrument(gold_bars, wc_nas, GOLD_COMMISSION_RATE)}
    runs["nas"]["bars"], runs["gold"]["bars"] = nas_bars, gold_bars
    meta = {"nas symbol": spec.symbol, "nas rows": len(df), "nas commission rate": NAS_COMMISSION_RATE,
            "nas files": {f["file"]: f["sha256"] for f in man_n.get("files", [])},
            "gold rows": len(dg), "gold files": {f["file"]: f["sha256"] for f in man_g.get("files", [])},
            "range": f"{F1_START_DATE} .. 2022-12-31"}
    write_report(runs, out, {"nas": wc_nas, "gold (diagnostic)": wc_gold}, meta, a.tests_summary)
    print(f"verdict {runs['nas']['res']['verdict_rule']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
