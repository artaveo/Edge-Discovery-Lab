"""Phase F5: the previous New York close level (EdgeLab_Roadmap.md Section 13).

Usage (F5 Step B, from ``python/``), once::

    python -m edgelab.nyclose --data ../data --out ../research/f5

One event type only: price reaching L(d) = the Bid close of the last M1 bar of the previous
broker trading day (= the New York 17:00 close). Every entry variant x exit x signal timeframe
is a fixed rule (no model): 14 entries x 12 exits x 2 TF = 336 configurations, all counted.

F1 pieces used unchanged: data 2020-07 .. 2022 (``load_f1``), audit/quarantine, weekday bars,
ResumeTime and the 21:30 window, the commission formula, the F1 config (fingerprint checked).
Path resolution follows Section 12.3 (as ``exits.py``): M1 bars, the stop wins a same-bar
conflict, short triggers on Ask, stops gap-fill at the worse open, EOD = last M1 close <= 21:30.
``exits.py`` works on ATR-multiple levels for many moments at once; F5 needs explicit price
levels (structural stops, a TP solved net of cost), so ``path_exit`` implements the same rules
for one trade (cross-checked against ``exits.simulate`` in the tests).

Pre-registered details not spelled out in Section 13 (frozen here, before any F5 run):

Level and day
* L(d) = last M1 Bid close of the previous trading day (weekends are not trading days). A day
  needs a previous day, must not be quarantined and must have a bar at or before 21:30 after
  ResumeTime. The first day of the data has no level.
* Approach side of an event with break distance D: the side of L of the most recent signal-bar
  close *before the event bar* that lies outside the band (L - D, L + D) (for D = 0: any close
  != L), using all bars of the day. If there is none, the side of the day's first M1 open. If
  that equals L, the bar has no side and no event. "Down" = price above L (support test).
  For R1 (touch on M1) the side is taken from the last signal bar completed at or before the
  touch bar's open.

Timeframes and ATR
* Signal bars are clock-aligned M5 / M15 bars built from the M1 Bid bars.
* ATRtf = Wilder ATR(14) of the continuous signal-bar series, taken at the last signal bar that
  closed at or before the event bar's open (R1: the touch bar's open). For BR and F, the event
  is the break: they use the break's ATRtf (for D, the stop and the re-arm) throughout.

Entries (down approach; the up approach mirrors every rule)
* Touch of L on a bar: Bid low + that bar's spread <= L (the price a buy limit at L needs);
  up approach: Bid high >= L.
* R1: buy limit at L, filled on the first M1 bar after ResumeTime whose open is before 21:00
  and which touches L; the fill price is exactly L.
* R2: the first signal bar that touched L and closes above L -> buy at its close (Ask =
  Bid close + spread of its last M1 bar).
* B(d): the first signal bar that closes below L - D -> sell at its close (Bid).
* BR(d): after a B(d) break bar, a sell limit at L is live on the M1 bars from the break bar's
  close to the close of the 12th signal bar after it; it fills on the first M1 bar with
  Bid high >= L, at L.
* F(d): after a B(d) break bar, the first of the next 12 signal bars that closes above L -> buy
  at its close.
* Entries: signal-bar closes and limit-fill bar opens must be before 21:00 and after ResumeTime.

Several events per day (Section 13.4)
* Per configuration (variant x exit x TF): an event is accepted when (1) the configuration has
  no open position and no live BR/F window, and (2) since the previous accepted event some
  signal bar has closed at least 0.5 x ATRtf (of that previous event) away from L. The event
  bar must open at or after both moments. The test number is the index of the accepted event
  within the day for that configuration (1, 2, 3, 4+).
* An accepted B/BR/F break whose BR retest or F signal does not come within 12 bars is an event
  without a trade (it still needs the re-arm before the next one).

Exits (12)
* Stop: s x ATRtf from the entry price (s in 0.5, 1, 2) or structural:
  R1 = the fill M1 bar's Bid low; R2 = the rejection bar's Bid low; B/BR = the break bar's Ask
  high (Bid high + spread); F = the lowest Bid low from the break bar to the F bar (long;
  mirrored for short entries: the high + spread). A structural stop closer than 0.1 x ATRtf to
  the entry (or on the wrong side) is widened to 0.1 x ATRtf.
* R unit = |entry - stop| + commission (the loss at the stop). TP = entry +/- (k x R unit +
  commission), so a TP fill nets exactly +k R. A stop fill nets -1 R (worse on a gap).
  Commission = 2 x 0.000016 x entry price.
* Limit entries: the fill bar is checked for the stop when the stop level is known before the
  fill (ATR stops, BR's structural stop), never for the TP; the R1 structural stop is defined
  by the fill bar and is live from the next bar. Close entries start the path on the next M1 bar.

Statistics
* Warm-up 2020-07..12 is reported but not used; 2021 and 2022 are the evaluation years.
* Reality check: 200 permutations; in each, every evaluation day is flipped with probability
  1/2 (default_rng(20260930), one coin per day shared by all configurations). A flipped trade
  is the opposite side at the same entry moment (limit entries at L, close entries at the
  opposite side's price), with the same stop distance and the same k, evaluated on the same
  path. The accepted events stay as they are. A configuration without trades scores 0.
* Bootstrap: day-block over 2021-2022 trades, 10,000 reps, seed 20260930, lower 5% quantile.
* The run refuses to start when ``<out>/report.json`` exists; every run goes to the ledger.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .audit import audit_m1, write_audit  # noqa: F401  (write_audit kept for symmetry with F1)
from .config import DEFAULT, F1Config, MIN_PER_DAY, hm
from .data import Bars, InstrumentSpec, build_bars, clean_m1, load_f1, to_minutes, weekday_of_day, wilder_atr, year_of_day
from .report import _fmt_t, svg_chart
from .stats import day_block_bootstrap, max_drawdown, max_stat_pvalue, null_max
from .window import resume_times

F1_FINGERPRINT = "7e945e717983b088"
TFS = (5, 15)
D_MULTS = (0.0, 0.25, 0.5, 1.0)
STOPS = (0.5, 1.0, 2.0, "S")
KS = (1, 2, 3)
WINDOW_BARS = 12
REARM_ATR = 0.5
ENTRY_CUTOFF = hm(21, 0)
STRUCT_FLOOR_ATR = 0.1
MIN_TRADES_PER_YEAR = 50
EVAL_YEARS = (2021, 2022)
N_PERM = 200
P_PASS, P_WEAK = 0.05, 0.10
REASONS = {0: "EOD", 1: "SL", 2: "TP"}


def _dname(d: float) -> str:
    return f"{d:g}"


VARIANTS = tuple([("R1", None), ("R2", None)] + [("B", d) for d in D_MULTS] + [("BR", d) for d in D_MULTS]
                 + [("F", d) for d in D_MULTS])
EXITS = tuple((s, k) for s in STOPS for k in KS)


def variant_name(v) -> str:
    fam, d = v
    return fam if d is None else f"{fam}({_dname(d)})"


def exit_name(e) -> str:
    s, k = e
    return f"S{'struct' if s == 'S' else f'{s:g}'}_k{k}"


def config_name(tf, v, e) -> str:
    return f"M{tf}_{variant_name(v)}_{exit_name(e)}"


assert len(VARIANTS) == 14 and len(EXITS) == 12


# ----------------------------------------------------------------------------- data

@dataclass
class TF:
    """Signal bars of one timeframe (clock aligned, built from M1)."""
    minutes: int
    k: np.ndarray        # open time
    tc: np.ndarray       # close time
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    first: np.ndarray    # first M1 index
    last: np.ndarray     # last M1 index
    day: np.ndarray
    atr: np.ndarray      # Wilder ATR(14) at the bar (includes the bar)
    ask_low: np.ndarray  # min over M1 of Bid low + spread
    ask_high: np.ndarray  # max over M1 of Bid high + spread


def build_tf(bars: Bars, minutes: int, cfg: F1Config = DEFAULT) -> TF:
    t = bars.t
    key = t - t % minutes
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    ends = np.r_[starts[1:], len(t)] - 1
    sp = bars.spread_pts * bars.spec.point
    h = np.maximum.reduceat(bars.h, starts)
    l = np.minimum.reduceat(bars.l, starts)
    c = bars.c[ends]
    return TF(minutes=minutes, k=key[starts], tc=key[starts] + minutes, o=bars.o[starts], h=h, l=l, c=c,
              first=starts, last=ends, day=key[starts] // MIN_PER_DAY,
              atr=wilder_atr(h, l, c, cfg.atr_period),
              ask_low=np.minimum.reduceat(bars.l + sp, starts), ask_high=np.maximum.reduceat(bars.h + sp, starts))


@dataclass
class Prep5:
    bars: Bars
    audit: dict
    resume: object
    tfs: dict
    levels: np.ndarray      # per day row, NaN when the day has no level / is not used
    cfg: F1Config = field(default=DEFAULT)


def prepare_f5(df_raw: pd.DataFrame, spec: InstrumentSpec, cfg: F1Config = DEFAULT) -> Prep5:
    audit = audit_m1(df_raw, cfg)
    df, _ = clean_m1(df_raw)
    wd = weekday_of_day(to_minutes(df["time"]) // MIN_PER_DAY)
    df = df.loc[wd < 5].reset_index(drop=True)
    bars = build_bars(df, spec)
    resume = resume_times(bars, cfg)
    excluded = set(int(x) for x in audit["excluded_days"])
    levels = np.full(bars.n_days, np.nan)
    for r in range(1, bars.n_days):
        if int(bars.days[r]) not in excluded:
            levels[r] = bars.d_close[r - 1]
    return Prep5(bars=bars, audit=audit, resume=resume, tfs={m: build_tf(bars, m, cfg) for m in TFS},
                 levels=levels, cfg=cfg)


# ----------------------------------------------------------------------------- one trade on the M1 path

def path_exit(bars: Bars, side: int, entry: float, stop: float, tp: float, i_start: int, i_eod: int,
              fill_bar: int = -1, stop_in_fill_bar: bool = False):
    """Resolve one trade on M1 bars i_start..i_eod (Section 12.3 rules).

    side +1 long (exits at Bid), -1 short (exits at Ask). ``fill_bar`` (limit entries) is the
    bar of the fill: it is checked for the stop only when ``stop_in_fill_bar``, never for the TP,
    and its open cannot gap the stop. Returns (exit price, exit bar index, reason, conflict)."""
    lo = fill_bar if fill_bar >= 0 else i_start
    idx = np.arange(lo, i_eod + 1)
    if len(idx) == 0:
        return np.nan, -1, -1, False
    sp = bars.spread_pts[idx] * bars.spec.point
    o, h, l, c = bars.o[idx], bars.h[idx], bars.l[idx], bars.c[idx]
    if side > 0:
        hs, ht, gap = l <= stop, h >= tp, o <= stop
        opx = o
    else:
        hs, ht, gap = h + sp >= stop, l + sp <= tp, o + sp >= stop
        opx = o + sp
    if fill_bar >= 0:
        hs[0] = hs[0] and stop_in_fill_bar
        ht[0] = False
        gap[0] = False
    n = len(idx)
    si = int(np.argmax(hs)) if hs.any() else n
    ti = int(np.argmax(ht)) if ht.any() else n
    if si < n and si <= ti:
        px = (min(stop, opx[si]) if side > 0 else max(stop, opx[si])) if gap[si] else stop
        return px, int(idx[si]), 1, si == ti
    if ti < n:
        return tp, int(idx[ti]), 2, False
    px = c[-1] if side > 0 else c[-1] + sp[-1]
    return px, int(idx[-1]), 0, False


@dataclass
class Setup:
    """An entry: everything the exits need."""
    side: int               # +1 long / -1 short
    entry: float            # execution price
    flip_entry: float       # execution price of the opposite side at the same moment
    i_start: int            # first M1 bar of the path
    fill_bar: int           # limit fill bar (-1 for close entries)
    t_entry: int            # entry time (close time of the entry bar / fill bar close)
    A: float                # ATRtf
    struct: float           # structural stop price (Bid low for a long, Ask high for a short)
    struct_known: bool      # structural stop known before a limit fill (BR)
    approach: int           # +1 down (price above L), -1 up


def trade_result(bars: Bars, st: Setup, exit_rule, i_eod: int, commission_rate: float, flip: bool = False):
    s, k = exit_rule
    side = -st.side if flip else st.side
    entry = st.flip_entry if flip else st.entry
    if s == "S":
        dist = (st.entry - st.struct) * st.side
        dist = max(dist, STRUCT_FLOOR_ATR * st.A)
        in_fill = st.struct_known
    else:
        dist = s * st.A
        in_fill = True
    comm = 2.0 * commission_rate * entry
    unit = dist + comm
    stop = entry - side * dist
    tp = entry + side * (k * unit + comm)
    px, ib, reason, conflict = path_exit(bars, side, entry, stop, tp, st.i_start, i_eod,
                                         st.fill_bar, in_fill and st.fill_bar >= 0)
    if ib < 0:
        return None
    net = (px - entry) * side - comm
    return {"r": net / unit, "usd": net, "exit_i": ib, "exit_t": int(bars.tc[ib]), "reason": reason,
            "conflict": bool(conflict)}


# ----------------------------------------------------------------------------- events of one day

def _side_before(C: np.ndarray, L: float, D: np.ndarray, first_open: float) -> np.ndarray:
    """For each bar j: side of the latest close before j outside the band (L-D_j, L+D_j)."""
    n = len(C)
    dist = C - L
    out = np.abs(dist)[None, :] > D[:, None]                 # [j, j'] close j' outside band of j
    out &= np.tri(n, n, -1, dtype=bool)                      # only j' < j
    has = out.any(axis=1)
    last = np.where(has, n - 1 - np.argmax(out[:, ::-1], axis=1), 0)
    s0 = float(np.sign(first_open - L))
    return np.where(has, np.sign(dist[last]), s0)


@dataclass
class DayCtx:
    row: int
    L: float
    rt: int                  # ResumeTime (absolute minutes, M1 close)
    i_eod: int               # EOD M1 bar
    j0: int                  # first signal bar of the day (index in TF arrays)
    j1: int                  # last + 1


def day_contexts(p: Prep5, tf: TF) -> list:
    bars, cfg = p.bars, p.cfg
    out = []
    jstarts = np.searchsorted(tf.day, bars.days, side="left")
    jends = np.searchsorted(tf.day, bars.days, side="right")
    for r in range(bars.n_days):
        L = p.levels[r]
        if not np.isfinite(L):
            continue
        d = int(bars.days[r])
        i_eod = int(bars.asof_index(d * MIN_PER_DAY + cfg.window_end))
        rt = int(p.resume.abs[r])
        if i_eod < bars.d_first[r] or bars.tc[i_eod] <= rt:
            continue
        out.append(DayCtx(row=r, L=float(L), rt=rt, i_eod=i_eod, j0=int(jstarts[r]), j1=int(jends[r])))
    return out


def candidates(p: Prep5, tf: TF, ctx: DayCtx, variant) -> list:
    """Candidate events of one variant on one day, in time order, ignoring the re-arm rule.
    Each is a dict with the event bar open time ``t0``, the event time ``t_ev`` and a
    ``resolve`` payload used by :func:`resolve_setup`."""
    bars, cfg = p.bars, p.cfg
    fam, dm = variant
    L = ctx.L
    js = np.arange(ctx.j0, ctx.j1)
    if len(js) == 0:
        return []
    C = tf.c[js]
    Aprev = np.r_[tf.atr[js[0] - 1] if js[0] > 0 else np.nan, tf.atr[js[:-1]]]    # ATR before bar j
    first_open = bars.o[bars.d_first[ctx.row]]
    day0 = int(bars.days[ctx.row]) * MIN_PER_DAY
    ok_bar = (tf.tc[js] > ctx.rt) & (tf.tc[js] - day0 < ENTRY_CUTOFF) & np.isfinite(Aprev)
    out = []
    if fam == "R1":
        side_after = _side_before(np.r_[C, np.nan], L, np.zeros(len(C) + 1), first_open)   # side after bar j = before j+1
        i_lo, i_hi = int(bars.d_first[ctx.row]), int(bars.d_last[ctx.row])
        ii = np.arange(i_lo, i_hi + 1)
        ii = ii[(bars.t[ii] >= ctx.rt) & (bars.t[ii] - day0 < ENTRY_CUTOFF)]
        if len(ii) == 0:
            return []
        # last signal bar of the day closed at or before the M1 bar's open
        jpos = np.searchsorted(tf.tc[js], bars.t[ii], side="right") - 1
        side = np.where(jpos >= 0, side_after[np.clip(jpos + 1, 0, len(C))], np.sign(first_open - L))
        gidx = np.where(jpos >= 0, js[np.clip(jpos, 0, None)], js[0] - 1)
        A = np.where(gidx >= 0, tf.atr[np.clip(gidx, 0, None)], np.nan)
        sp = bars.spread_pts[ii] * bars.spec.point
        touch = ((side > 0) & (bars.l[ii] + sp <= L)) | ((side < 0) & (bars.h[ii] >= L))
        for q in np.flatnonzero(touch & np.isfinite(A)):
            i = int(ii[q])
            out.append({"t0": int(bars.t[i]), "t_ev": int(bars.tc[i]), "approach": int(side[q]), "A": float(A[q]),
                        "kind": "R1", "i": i})
        return out
    D = (dm or 0.0) * Aprev
    side = _side_before(C, L, np.nan_to_num(D, nan=np.inf), first_open)
    if fam == "R2":
        hit = ((side > 0) & (tf.ask_low[js] <= L) & (C > L)) | ((side < 0) & (tf.h[js] >= L) & (C < L))
        for q in np.flatnonzero(hit & ok_bar):
            out.append({"t0": int(tf.k[js[q]]), "t_ev": int(tf.tc[js[q]]), "approach": int(side[q]),
                        "A": float(Aprev[q]), "kind": "R2", "j": int(js[q])})
        return out
    brk = ((side > 0) & (C < L - D)) | ((side < 0) & (C > L + D))
    for q in np.flatnonzero(brk & ok_bar):
        out.append({"t0": int(tf.k[js[q]]), "t_ev": int(tf.tc[js[q]]), "approach": int(side[q]),
                    "A": float(Aprev[q]), "kind": fam, "j": int(js[q]), "q": int(q)})
    return out


def resolve_setup(p: Prep5, tf: TF, ctx: DayCtx, ev: dict):
    """Turn an accepted event into a Setup (or None when BR/F do not trigger).
    Returns (setup or None, busy_until) where busy_until is the end of a BR/F window."""
    bars = p.bars
    pt = bars.spec.point
    L, a, A = ctx.L, ev["approach"], ev["A"]
    day0 = int(bars.days[ctx.row]) * MIN_PER_DAY
    kind = ev["kind"]
    if kind == "R1":
        i = ev["i"]
        side = a                                    # down approach -> long
        struct = bars.l[i] if side > 0 else bars.h[i] + bars.spread_pts[i] * pt
        return Setup(side, L, L, i + 1, i, int(bars.tc[i]), A, struct, False, a), ev["t_ev"]
    j = ev["j"]
    spj = bars.spread_pts[tf.last[j]] * pt
    if kind in ("R2", "B"):
        side = a if kind == "R2" else -a
        entry = tf.c[j] + spj if side > 0 else tf.c[j]
        flip = tf.c[j] if side > 0 else tf.c[j] + spj
        if kind == "R2":
            struct = tf.l[j] if side > 0 else tf.ask_high[j]
        else:
            struct = tf.ask_high[j] if side < 0 else tf.l[j]
        return Setup(side, entry, flip, int(tf.last[j]) + 1, -1, int(tf.tc[j]), A, struct, False, a), ev["t_ev"]
    # BR / F: follow the break for up to 12 signal bars of the same day
    jmax = min(j + WINDOW_BARS, ctx.j1 - 1)
    window_end = int(tf.tc[jmax])
    if kind == "F":
        side = a                                    # down break (a=+1) failed -> long
        for jj in range(j + 1, jmax + 1):
            if tf.tc[jj] - day0 >= ENTRY_CUTOFF:
                break
            back = tf.c[jj] > L if a > 0 else tf.c[jj] < L
            if back:
                spjj = bars.spread_pts[tf.last[jj]] * pt
                entry = tf.c[jj] + spjj if side > 0 else tf.c[jj]
                flip = tf.c[jj] if side > 0 else tf.c[jj] + spjj
                struct = (tf.l[j:jj + 1].min() if side > 0 else tf.ask_high[j:jj + 1].max())
                return Setup(side, entry, flip, int(tf.last[jj]) + 1, -1, int(tf.tc[jj]), A, struct, False, a), int(tf.tc[jj])
        return None, window_end
    # BR: limit at L on the M1 bars after the break bar up to the end of bar j+12
    side = -a                                       # down break -> sell the retest
    struct = tf.ask_high[j] if side < 0 else tf.l[j]
    i_lo, i_hi = int(tf.last[j]) + 1, int(tf.last[jmax])
    for i in range(i_lo, i_hi + 1):
        if bars.t[i] - day0 >= ENTRY_CUTOFF:
            break
        sp = bars.spread_pts[i] * pt
        fill = bars.h[i] >= L if side < 0 else bars.l[i] + sp <= L
        if fill:
            return Setup(side, L, L, i + 1, i, int(bars.tc[i]), A, struct, True, a), int(bars.tc[i])
    return None, window_end


def rearm_time(tf: TF, ctx: DayCtx, t_ev: int, A: float) -> float:
    js = np.arange(ctx.j0, ctx.j1)
    m = (tf.tc[js] > t_ev) & (np.abs(tf.c[js] - ctx.L) >= REARM_ATR * A)
    return float(tf.tc[js[np.argmax(m)]]) if m.any() else np.inf


# ----------------------------------------------------------------------------- all trades

def simulate_all(p: Prep5, tfs=TFS, variants=VARIANTS, exits=EXITS, progress=None) -> dict:
    """{config name: list of trade dicts} for every configuration (real and flipped results)."""
    cfg = p.cfg
    out = {}
    for tfm in tfs:
        tf = p.tfs[tfm]
        ctxs = day_contexts(p, tf)
        for v in variants:
            names = {e: config_name(tfm, v, e) for e in exits}
            for e in exits:
                out[names[e]] = []
            for ctx in ctxs:
                cands = candidates(p, tf, ctx, v)
                if not cands:
                    continue
                cache = {}
                for e in exits:
                    ready, n_ev = -np.inf, 0
                    for ci, ev in enumerate(cands):
                        if ev["t0"] < ready:
                            continue
                        n_ev += 1
                        if ci not in cache:
                            cache[ci] = resolve_setup(p, tf, ctx, ev)
                        st, busy = cache[ci]
                        rearm = rearm_time(tf, ctx, ev["t_ev"], ev["A"])
                        exit_t = busy
                        if st is not None:
                            res = trade_result(p.bars, st, e, ctx.i_eod, cfg.commission_rate)
                            flp = trade_result(p.bars, st, e, ctx.i_eod, cfg.commission_rate, flip=True)
                            if res is not None and flp is not None:
                                exit_t = max(busy, res["exit_t"])
                                out[names[e]].append({
                                    "day": int(p.bars.days[ctx.row]), "t_entry": st.t_entry, "side": st.side,
                                    "approach": st.approach, "test_no": n_ev, "r": res["r"], "usd": res["usd"],
                                    "exit_t": res["exit_t"], "reason": res["reason"], "conflict": res["conflict"],
                                    "r_flip": flp["r"], "A": st.A, "entry": st.entry})
                        ready = max(exit_t, rearm)
            if progress:
                progress(tfm, variant_name(v))
    return out


def trade_arrays(trades: dict) -> dict:
    cols = ("day", "t_entry", "side", "approach", "test_no", "r", "usd", "exit_t", "reason", "conflict", "r_flip", "A", "entry")
    arr = {}
    for name, tl in trades.items():
        a = {c: np.array([t[c] for t in tl]) for c in cols}
        if not tl:
            a = {c: np.zeros(0) for c in cols}
        a["year"] = year_of_day(a["day"].astype(np.int64)) if len(tl) else np.zeros(0, dtype=np.int64)
        arr[name] = a
    return arr


# ----------------------------------------------------------------------------- statistics

def flip_null(arr: dict, names: list, n_perm: int = N_PERM, seed: int = 20260930, years=EVAL_YEARS) -> np.ndarray:
    """(n_perm, configurations) pooled mean net R over the evaluation years when every day's
    trades are flipped together with probability 1/2 (one coin per day, shared by all
    configurations)."""
    days_all = np.unique(np.concatenate([arr[n]["day"][np.isin(arr[n]["year"], years)] for n in names] + [np.zeros(0)]))
    rng = np.random.default_rng(seed)
    out = np.full((n_perm, len(names)), np.nan)
    sel = []
    for n in names:
        a = arr[n]
        m = np.isin(a["year"], years)
        sel.append((np.searchsorted(days_all, a["day"][m]), a["r"][m], a["r_flip"][m]))
    for k in range(n_perm):
        coin = rng.random(len(days_all)) < 0.5
        for ci, (di, r, rf) in enumerate(sel):
            if len(r):
                out[k, ci] = float(np.where(coin[di], rf, r).mean())
    return out


def _summ(r: np.ndarray) -> dict:
    if len(r) == 0:
        return {"trades": 0, "mean_r": float("nan"), "win_rate": float("nan"), "avg_win_r": float("nan"),
                "avg_loss_r": float("nan")}
    w, lo = r[r > 0], r[r <= 0]
    return {"trades": int(len(r)), "mean_r": float(r.mean()), "win_rate": float(np.mean(r > 0)),
            "avg_win_r": float(w.mean()) if len(w) else float("nan"),
            "avg_loss_r": float(lo.mean()) if len(lo) else float("nan")}


def _bucket(t_entry: np.ndarray, day: np.ndarray, cfg: F1Config) -> np.ndarray:
    mod = t_entry - day * MIN_PER_DAY
    return np.searchsorted(np.asarray(cfg.hour_buckets), mod, side="right") - 1


def results_table(arr: dict, names: list, null: np.ndarray, cfg: F1Config = DEFAULT) -> list:
    best = null_max(null)
    rows = []
    for ci, n in enumerate(names):
        a = arr[n]
        m = np.isin(a["year"], EVAL_YEARS)
        r = a["r"][m]
        tf, var, ex = n.split("_", 2)
        row = {"config": n, "tf": tf, "variant": var, "exit": ex, **_summ(r)}
        row["per_year"] = {str(y): _summ(a["r"][a["year"] == y]) for y in (2020,) + EVAL_YEARS}
        row["boot_lower_r"] = day_block_bootstrap(r, a["day"][m], cfg.final_boot, cfg.seed, cfg.alpha)["lower"] if len(r) else float("nan")
        row["p_rc"] = max_stat_pvalue(row["mean_r"], best)
        row["max_dd_r"] = max_drawdown(r[np.argsort(a["t_entry"][m], kind="mergesort")]) if len(r) else 0.0
        row["conflict_share"] = float(a["conflict"][m].mean()) if m.any() else float("nan")
        row["mean_usd"] = float(a["usd"][m].mean()) if m.any() else float("nan")
        split = {}
        if m.any():
            ap = a["approach"][m]
            split["approach"] = {"down (support)": _summ(r[ap > 0]), "up (resistance)": _summ(r[ap < 0])}
            tn = np.minimum(a["test_no"][m], 4)
            split["test_no"] = {("4+" if t == 4 else str(t)): _summ(r[tn == t]) for t in (1, 2, 3, 4)}
            b = _bucket(a["t_entry"][m].astype(np.int64), a["day"][m].astype(np.int64), cfg)
            labels = ["00-08", "08-10", "10-13", "13-16:30", "16:30-18", "18-21:30"]
            split["session"] = {labels[i]: _summ(r[b == i]) for i in range(len(labels))}
        row["splits"] = split
        rows.append(row)
    return rows


def verdict(rows: list) -> str:
    weak = False
    for r in rows:
        py = [r["per_year"][str(y)] for y in EVAL_YEARS]
        pos = all(v["trades"] > 0 and v["mean_r"] > 0 for v in py)
        r["checks"] = {"positive_each_year": pos,
                       "boot_lower_positive": bool(np.isfinite(r["boot_lower_r"]) and r["boot_lower_r"] > 0),
                       "reality_check_p": r["p_rc"] < P_PASS,
                       "min_50_trades_each_year": all(v["trades"] >= MIN_TRADES_PER_YEAR for v in py)}
        r["passes"] = all(r["checks"].values())
        r["weak"] = (not r["passes"]) and pos and r["p_rc"] < P_WEAK
        weak |= r["weak"]
    if any(r["passes"] for r in rows):
        return "F5_PASS"
    return "F5_WEAK" if weak else "F5_STOP"


def heatmaps(rows: list) -> dict:
    """{tf: {variant: 4x3 list (stops x k) of pooled mean net R}}"""
    by = {(r["tf"], r["variant"], r["exit"]): r["mean_r"] for r in rows}
    out = {}
    for tfm in TFS:
        tf = f"M{tfm}"
        out[tf] = {}
        for v in VARIANTS:
            vn = variant_name(v)
            if not any((tf, vn, exit_name(e)) in by for e in EXITS):
                continue
            out[tf][vn] = [[by.get((tf, vn, exit_name((s, k))), float("nan")) for k in KS] for s in STOPS]
    return out


def run_f5(p: Prep5, n_perm: int = N_PERM, tfs=TFS, variants=VARIANTS, exits=EXITS, progress=None,
           check_fingerprint: bool = True) -> dict:
    if check_fingerprint and p.cfg.fingerprint() != F1_FINGERPRINT:
        raise RuntimeError("F5 must use the frozen F1 config")
    t0 = time.time()
    trades = simulate_all(p, tfs, variants, exits, progress)
    arr = trade_arrays(trades)
    names = [config_name(tf, v, e) for tf in tfs for v in variants for e in exits]
    null = flip_null(arr, names, n_perm)
    rows = results_table(arr, names, null, p.cfg)
    v = verdict(rows)
    return {"verdict": v, "rows": rows, "arr": arr, "names": names, "null": null, "heatmaps": heatmaps(rows),
            "seconds": time.time() - t0}


# ----------------------------------------------------------------------------- report

def _f(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def svg_heatmap(tf: str, maps: dict) -> str:
    """Small multiples: one 4x3 grid per variant, colour = pooled mean net R (red < 0 < green)."""
    names = list(maps)
    cols = 7
    cw, ch, pad = 40, 22, 30
    pw, ph = 3 * cw + 60, 4 * ch + 50
    rows_n = (len(names) + cols - 1) // cols
    W, H = cols * pw + pad, rows_n * ph + 60
    vals = np.array([v for n in names for row in maps[n] for v in row], float)
    vmax = max(0.25, float(np.nanmax(np.abs(vals)))) if np.isfinite(vals).any() else 1.0
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="10">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           f'<text x="{pad}" y="20" font-size="13" fill="#111">{tf}: pooled mean net R 2021–2022 (rows = stop, columns = k)'
           f' · colour scale ±{vmax:.2f} R</text>']
    for idx, n in enumerate(names):
        x0 = pad + (idx % cols) * pw
        y0 = 40 + (idx // cols) * ph
        out.append(f'<text x="{x0}" y="{y0 + 10}" font-size="11" fill="#111">{n}</text>')
        for ki, k in enumerate(KS):
            out.append(f'<text x="{x0 + 50 + ki * cw + 12}" y="{y0 + 24}" fill="#555">k{k}</text>')
        for si, s in enumerate(STOPS):
            lab = "struct" if s == "S" else f"{s:g}ATR"
            yy = y0 + 28 + si * ch
            out.append(f'<text x="{x0}" y="{yy + 15}" fill="#555">{lab}</text>')
            for ki in range(len(KS)):
                v = maps[n][si][ki]
                if np.isfinite(v):
                    a = min(1.0, abs(v) / vmax)
                    col = f"rgba(26,127,55,{a:.2f})" if v > 0 else f"rgba(207,34,46,{a:.2f})"
                    txt = f"{v:+.2f}"
                else:
                    col, txt = "#eeeeee", "—"
                xx = x0 + 50 + ki * cw
                out.append(f'<rect x="{xx}" y="{yy}" width="{cw - 2}" height="{ch - 2}" fill="{col}" stroke="#ccc"/>')
                out.append(f'<text x="{xx + 4}" y="{yy + 14}" fill="#111">{txt}</text>')
    out.append("</svg>")
    return "\n".join(out)


def write_report(p: Prep5, res: dict, out_dir: Path, manifest: dict | None = None, tests_summary: str = "") -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    hm_files = {}
    for tf, maps in res["heatmaps"].items():
        fn = out_dir / f"heatmap_{tf}.svg"
        fn.write_text(svg_heatmap(tf, maps), encoding="utf-8")
        hm_files[tf] = fn.name
    charts = {}
    rng = np.random.default_rng([p.cfg.seed, 7])
    for row in res["rows"]:
        if not row.get("passes"):
            continue
        a = res["arr"][row["config"]]
        idx = np.flatnonzero(np.isin(a["year"], EVAL_YEARS))
        pick = np.sort(rng.choice(idx, size=min(10, len(idx)), replace=False))
        cdir = out_dir / "charts" / row["config"]
        cdir.mkdir(parents=True, exist_ok=True)
        charts[row["config"]] = []
        for n_ex, i in enumerate(pick):
            t, te = int(a["t_entry"][i]), int(a["exit_t"][i])
            title = (f"{row['config']} {'LONG' if a['side'][i] > 0 else 'SHORT'} | {_fmt_t(t)} -> {_fmt_t(te)} "
                     f"{REASONS.get(int(a['reason'][i]), '?')} | {a['r'][i]:+.2f} R")
            fn = cdir / f"ex_{n_ex + 1:02d}.svg"
            fn.write_text(svg_chart(p.bars, t, te, title, max(240, te - t + 30)), encoding="utf-8")
            charts[row["config"]].append({"file": str(fn.relative_to(out_dir)), "r": float(a["r"][i])})
    au = p.audit
    summary = {
        "phase": "F5", "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "verdict": res["verdict"], "config_fingerprint": p.cfg.fingerprint(), "n_configurations": len(res["rows"]),
        "n_perm": int(res["null"].shape[0]), "eval_years": list(EVAL_YEARS),
        "data": {"rows_raw": au["rows_raw"], "days": au["n_days"], "quarantined_days": au["n_quarantined"],
                 "days_with_level": int(np.isfinite(p.levels).sum()),
                 "manifest_sha256": {f["file"]: f["sha256"] for f in (manifest or {}).get("files", [])}},
        "configurations": res["rows"], "heatmaps": res["heatmaps"], "heatmap_files": hm_files,
        "null_best": null_max(res["null"]).tolist(), "charts": charts, "runtime_seconds": res.get("seconds"),
    }
    (out_dir / "report.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "report.md").write_text(_markdown(summary, tests_summary), encoding="utf-8")
    with open(out_dir / "trials_ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at_utc": summary["generated_at_utc"], "phase": "F5", "verdict": res["verdict"],
                            "fingerprint": summary["config_fingerprint"], "configurations": len(res["rows"]),
                            "n_perm": summary["n_perm"]}) + "\n")
    return summary


def _markdown(s: dict, tests_summary: str) -> str:
    nb = np.asarray(s["null_best"], float)
    L = ["# Edge Discovery Lab — Phase F5 report (previous New York close level)", "",
         f"**Verdict: `{s['verdict']}`**", "",
         f"Generated {s['generated_at_utc']} · F1 config fingerprint `{s['config_fingerprint']}` · "
         f"{s['n_configurations']} configurations · {s['n_perm']} direction-flip permutations (reality check on the maximum)",
         "", "## Data", "",
         f"- M1 rows {s['data']['rows_raw']}; days {s['data']['days']}; quarantined {s['data']['quarantined_days']}; "
         f"days with a level {s['data']['days_with_level']}"]
    for fn, h in s["data"]["manifest_sha256"].items():
        L.append(f"- `{fn}` SHA-256 `{h}`")
    if len(nb):
        L += ["", f"Best configuration under direction flips (mean net R 2021–2022): median {_f(float(np.median(nb)))}, "
              f"90% {_f(float(np.quantile(nb, 0.9)))}, 95% {_f(float(np.quantile(nb, 0.95)))}."]
    L += ["", "## Heatmaps: pooled mean net R 2021–2022 (rows = stop, columns = k)", ""]
    for tf, maps in s["heatmaps"].items():
        L.append(f"### {tf} — ![{tf}]({s['heatmap_files'][tf]})")
        L.append("")
        L.append("| Variant | Stop | k1 | k2 | k3 |")
        L.append("|---|---|---|---|---|")
        for vn, grid in maps.items():
            for si, st in enumerate(STOPS):
                lab = "struct" if st == "S" else f"{st:g} ATR"
                L.append(f"| {vn if si == 0 else ''} | {lab} | " + " | ".join(_f(x, 3) for x in grid[si]) + " |")
        L.append("")
    top = sorted(s["configurations"], key=lambda r: -(r["mean_r"] if np.isfinite(r["mean_r"]) else -9))
    L += ["## Best 20 configurations by pooled mean net R", "",
          "| Config | Trades 2021 / 2022 | Win % | Avg win R | Avg loss R | Mean R 2021 | Mean R 2022 | Mean R | Boot low R | p (RC) | Max DD R | Same-bar % | Result |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in top[:20]:
        py = r["per_year"]
        res = "PASS" if r.get("passes") else ("weak" if r.get("weak") else "")
        L.append(f"| `{r['config']}` | {py['2021']['trades']} / {py['2022']['trades']} | "
                 f"{_f(100 * r['win_rate'], 1) if r['trades'] else '—'} | {_f(r['avg_win_r'], 2)} | {_f(r['avg_loss_r'], 2)} | "
                 f"{_f(py['2021']['mean_r'])} | {_f(py['2022']['mean_r'])} | {_f(r['mean_r'])} | {_f(r['boot_lower_r'])} | "
                 f"{_f(r['p_rc'])} | {_f(r['max_dd_r'], 1)} | {_f(100 * r['conflict_share'], 1)} | {res} |")
    L += ["", "## Splits of the best 5 (descriptive)", ""]
    for r in top[:5]:
        L.append(f"### `{r['config']}`")
        for split, parts in r["splits"].items():
            L.append(f"- {split}: " + "; ".join(f"{k}: {v['trades']} trades, {_f(v['mean_r'])} R" for k, v in parts.items()))
        L.append("")
    L += ["## All configurations", "",
          "| Config | Trades 2020 / 2021 / 2022 | Win % | Mean R 2021 | Mean R 2022 | Mean R | Boot low R | p (RC) | Result |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in s["configurations"]:
        py = r["per_year"]
        res = "PASS" if r.get("passes") else ("weak" if r.get("weak") else "")
        L.append(f"| `{r['config']}` | {py['2020']['trades']} / {py['2021']['trades']} / {py['2022']['trades']} | "
                 f"{_f(100 * r['win_rate'], 1) if r['trades'] else '—'} | {_f(py['2021']['mean_r'])} | {_f(py['2022']['mean_r'])} | "
                 f"{_f(r['mean_r'])} | {_f(r['boot_lower_r'])} | {_f(r['p_rc'])} | {res} |")
    if s["charts"]:
        L += ["", "## Chart snapshots (passing configurations)", ""]
        for name, items in s["charts"].items():
            L.append(f"- `{name}`: " + ", ".join(f"[{i + 1}]({it['file']})" for i, it in enumerate(items)))
    L += ["", "## Completion record", "", "```", "F5 — COMPLETE", f"Date: {s['generated_at_utc'][:10]}",
          f"Data: rows {s['data']['rows_raw']}, days {s['data']['days']}, quarantined {s['data']['quarantined_days']}",
          f"Tests: {tests_summary or '...'}", f"Result: {s['verdict']}"]
    for r in top[:10]:
        L.append(f"  {r['config']:>28}: trades {r['trades']:>5}  mean {_f(r['mean_r'])} R  2021 {_f(r['per_year']['2021']['mean_r'])}"
                 f"  2022 {_f(r['per_year']['2022']['mean_r'])}  boot_low {_f(r['boot_lower_r'])}  p {_f(r['p_rc'])}")
    L += ["```", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Edge Discovery Lab F5 run")
    ap.add_argument("--data", default="../data")
    ap.add_argument("--out", default="../research/f5")
    ap.add_argument("--tests-summary", default="")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if (out / "report.json").exists():
        print("REFUSED: research/f5/report.json exists; F5 runs once.", flush=True)
        return 2
    df, spec, manifest = load_f1(Path(a.data), DEFAULT.years)
    p = prepare_f5(df, spec, DEFAULT)
    print(f"days with a level {int(np.isfinite(p.levels).sum())}", flush=True)
    res = run_f5(p, progress=lambda tf, v: print(f"  M{tf} {v} done", flush=True))
    write_report(p, res, out, manifest, a.tests_summary)
    print(f"verdict {res['verdict']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
