"""Phase F3: path-dependent exits on M1 bars (EdgeLab_Roadmap.md Section 12.2-12.4).

Entry is as in F1: at the close of the decision moment's last M1 bar ``i0``. A long enters at
Ask = Bid_close + spread(i0) and exits at Bid; a short enters at Bid_close(i0) and exits at
Ask = Bid + that bar's spread. ``A = ATR60(t)`` (Wilder 14 on M5, price units), the stop
distance is ``S = s * A``.

The path is every M1 bar after ``i0`` up to and including the EOD bar (the last M1 close
<= 21:30, as in F1). On each bar:

* long:  stop/trailing/breakeven trigger on Bid low <= stop, TP on Bid high >= TP;
* short: stop triggers on Ask high = Bid high + spread >= stop, TP on Ask low = Bid low +
  spread <= TP (that bar's spread);
* a stop and a TP touched in the same bar -> the stop counts (pessimistic);
* a stop fills at the stop price, or at the bar open if the bar opened beyond it (gap),
  whichever is worse; a TP fills at the TP price; EOD fills at the Bid close (long) / Ask
  close (short) of the EOD bar.

Net result = fill - entry (in the trade's direction) - commission (2 x 0.000016 x Bid_close(i0)).
R = net / (S + spread(i0) + commission).

Pre-registered details not spelled out in Section 12 (frozen here, before any F3 run):

* All levels are measured from the entry price (long: the Ask; short: the Bid).
  Long SL = entry - S, TP = entry + k*S; short SL = entry + S, TP = entry - k*S.
* Trailing stop: before bar c the stop is max(entry - S, H_{c-1} - t*A) for a long, where
  H_{c-1} = the highest Bid close from the entry bar i0 to bar c-1 (the short mirrors it with
  the lowest Ask close + t*A). It is updated after each M1 close and so never loosens.
* Breakeven: activated by the first bar whose Bid high (long) / Ask low (short) reaches
  entry +/- 1 x S; from the next bar on, the stop is entry + commission (long) /
  entry - commission (short), i.e. a net result of 0 before a gap. A stop hit in the
  activation bar itself is the original stop.
* The EOD bar also checks the stop and the TP; if nothing triggers, the trade is closed at the
  EOD bar's close.
* A moment whose day has no bar after i0 up to 21:30 has no valid target (NaN), as in F1.
* The "TIME" exit (EOD only, no stop, no TP) is **not** part of the 28-rule grid; it exists
  for the tests (Section 12.7: the time exit must fail on the planted +2R-then-reverse
  pattern). Its R unit is 1 x ATR60 + entry cost.
* One position at a time: trades are visited in entry-time order and a trade is taken only
  when its entry time is >= the exit time (close of the exit bar) of the last taken trade.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import DEFAULT, F1Config
from .data import Bars
from .targets import exit_time

REASONS = {0: "EOD", 1: "SL", 2: "TP", 3: "TRAIL", 4: "BE"}


@dataclass(frozen=True)
class ExitRule:
    kind: str            # "sltp", "sl", "trail", "be", "time"
    s: float = 0.0       # stop distance in ATR60 units
    k: float = 0.0       # TP distance in units of S
    t: float = 0.0       # trailing distance in ATR60 units

    @property
    def name(self) -> str:
        if self.kind == "sltp":
            return f"SL{self.s:g}_TP{self.k:g}"
        if self.kind == "sl":
            return f"SL{self.s:g}"
        if self.kind == "trail":
            return f"TR{self.s:g}x{self.t:g}"
        if self.kind == "be":
            return f"BE{self.s:g}_TP{self.k:g}"
        return "TIME"

    def text(self) -> str:
        if self.kind == "sltp":
            return f"SL {self.s:g} ATR, TP {self.k:g} x SL, else EOD"
        if self.kind == "sl":
            return f"SL {self.s:g} ATR, no TP, else EOD"
        if self.kind == "trail":
            return f"initial SL {self.s:g} ATR, trailing {self.t:g} ATR behind the best close, else EOD"
        if self.kind == "be":
            return f"SL {self.s:g} ATR -> breakeven after +1 x SL, TP {self.k:g} x SL, else EOD"
        return "EOD only (no stop, no TP)"


EXIT_GRID = tuple(
    [ExitRule("sltp", s, k) for s in (0.5, 1.0, 1.5, 2.0) for k in (1.0, 1.5, 2.0, 3.0)]
    + [ExitRule("sl", s) for s in (0.5, 1.0, 1.5, 2.0)]
    + [ExitRule("trail", s, 0.0, t) for s in (1.0, 2.0) for t in (1.0, 2.0)]
    + [ExitRule("be", s, k) for s in (1.0, 2.0) for k in (2.0, 3.0)]
)
assert len(EXIT_GRID) == 28 and len({e.name for e in EXIT_GRID}) == 28
TIME_EXIT = ExitRule("time")


# ----------------------------------------------------------------------------- helpers

def _first_le(cm: np.ndarray, level) -> np.ndarray:
    """First column where a running minimum is <= level (N if never)."""
    return (cm > np.asarray(level, float).reshape(-1, 1)).sum(axis=1)


def _first_ge(cm: np.ndarray, level) -> np.ndarray:
    """First column where a running maximum is >= level (N if never)."""
    return (cm < np.asarray(level, float).reshape(-1, 1)).sum(axis=1)


def _first_true(b: np.ndarray) -> np.ndarray:
    n = b.shape[1]
    return np.where(b.any(axis=1), b.argmax(axis=1), n)


def _take(M: np.ndarray, col: np.ndarray) -> np.ndarray:
    c = np.clip(col, 0, M.shape[1] - 1)
    return M[np.arange(M.shape[0]), c]


# ----------------------------------------------------------------------------- simulation

def simulate(bars: Bars, moments: np.ndarray, atr5: np.ndarray, cfg: F1Config = DEFAULT,
             exits=EXIT_GRID) -> dict:
    """Simulate every exit rule for long and short at every moment.

    Returns {(exit name, side): {"net_usd", "r", "exit_t", "reason", "conflict"}} with arrays
    aligned to ``moments`` (NaN / -1 where the moment has no valid path)."""
    j = np.asarray(moments, dtype=np.int64)
    n = len(j)
    pt = bars.spec.point
    i0 = bars.last5[j]
    iE = bars.asof_index(exit_time(bars, j, "EOD", cfg))
    A = np.asarray(atr5, float)[j]
    p0 = bars.c[i0]
    sp0 = bars.spread_pts[i0] * pt
    comm = 2.0 * cfg.commission_rate * p0
    valid = (iE > i0) & np.isfinite(A) & (A > 0)
    out = {}
    for e in exits:
        for side in ("long", "short"):
            out[(e.name, side)] = {"net_usd": np.full(n, np.nan), "r": np.full(n, np.nan),
                                   "exit_t": np.full(n, -1, dtype=np.int64),
                                   "reason": np.full(n, -1, dtype=np.int64),
                                   "conflict": np.zeros(n, dtype=bool)}
    day = bars.day5[j]
    idx_all = np.flatnonzero(valid)
    if len(idx_all) == 0:
        return out
    # group valid moments by day (moments of a day share one M1 path window)
    dv = day[idx_all]
    starts = np.flatnonzero(np.r_[True, dv[1:] != dv[:-1]])
    ends = np.r_[starts[1:], len(idx_all)]
    for a, b in zip(starts, ends):
        rows = idx_all[a:b]
        _simulate_block(bars, rows, i0[rows], iE[rows], A[rows], p0[rows], sp0[rows], comm[rows],
                        exits, out)
    return out


def _simulate_block(bars, rows, i0, iE, A, p0, sp0, comm, exits, out):
    lo, hi = int(i0.min()) + 1, int(iE.max())
    cols = np.arange(lo, hi + 1)
    N = len(cols)
    pt = bars.spec.point
    inwin = (cols[None, :] > i0[:, None]) & (cols[None, :] <= iE[:, None])
    eodc = iE - lo
    o, h, l, c = bars.o[cols], bars.h[cols], bars.l[cols], bars.c[cols]
    spb = bars.spread_pts[cols] * pt
    tc = bars.tc[cols]
    Ac = A[:, None]
    cA = comm / A
    spA = sp0 / A
    for side in ("long", "short"):
        if side == "long":
            E = (p0 + sp0)[:, None]
            adv, fav, cl, op = l[None] - E, h[None] - E, c[None] - E, o[None] - E
        else:
            E = p0[:, None]
            adv, fav = E - (h + spb)[None], E - (l + spb)[None]
            cl, op = E - (c + spb)[None], E - (o + spb)[None]
        adv, fav, cl, op = adv / Ac, fav / Ac, cl / Ac, op / Ac       # profit, in ATR units
        adv_m = np.where(inwin, adv, np.inf)
        cm_adv = np.minimum.accumulate(adv_m, axis=1)
        cm_fav = np.maximum.accumulate(np.where(inwin, fav, -np.inf), axis=1)
        eod_fill = _take(cl, eodc)
        eod_t = tc[np.clip(eodc, 0, N - 1)]
        for e in exits:
            fill = eod_fill.copy()
            ecol = eodc.copy()
            reason = np.zeros(len(rows), dtype=np.int64)
            conflict = np.zeros(len(rows), dtype=bool)
            if e.kind in ("sltp", "sl", "be"):
                sl = _first_le(cm_adv, -e.s)
                stop_col, stop_lvl, stop_reason = sl, np.full(len(rows), -e.s), np.ones(len(rows), dtype=np.int64)
                if e.kind == "be":
                    act = _first_ge(cm_fav, e.s)
                    after = cols[None, :] - lo > act[:, None]              # bars after the activation bar
                    cm_be = np.minimum.accumulate(np.where(inwin & after, adv, np.inf), axis=1)
                    be = _first_le(cm_be, cA)
                    use_be = sl > act                                      # original stop not hit up to activation
                    stop_col = np.where(use_be, be, sl)
                    stop_lvl = np.where(use_be, cA, -e.s)
                    stop_reason = np.where(use_be, 4, 1)
                tp = _first_ge(cm_fav, e.k * e.s) if e.kind in ("sltp", "be") else np.full(len(rows), N)
                hit_stop = (stop_col < N) & (stop_col <= tp)
                hit_tp = (tp < N) & ~hit_stop
                conflict = (stop_col < N) & (stop_col == tp)
                sfill = np.minimum(stop_lvl, _take(op, stop_col))
                fill = np.where(hit_stop, sfill, np.where(hit_tp, e.k * e.s, fill))
                ecol = np.where(hit_stop, stop_col, np.where(hit_tp, tp, ecol))
                reason = np.where(hit_stop, stop_reason, np.where(hit_tp, 2, 0))
            elif e.kind == "trail":
                cmx = np.maximum.accumulate(np.where(inwin, cl, -np.inf), axis=1)
                hprev = np.concatenate([np.full((len(rows), 1), -np.inf), cmx[:, :-1]], axis=1)
                hprev = np.maximum(hprev, -spA[:, None])                   # entry bar close (Bid for a long, Ask for a short)
                stop = np.maximum(-e.s, hprev - e.t)
                trig = inwin & (adv <= stop)
                tcol = _first_true(trig)
                hit = tcol < N
                sfill = np.minimum(_take(stop, tcol), _take(op, tcol))
                fill = np.where(hit, sfill, fill)
                ecol = np.where(hit, tcol, ecol)
                reason = np.where(hit, 3, 0)
            net_a = fill - cA
            o_ = out[(e.name, side)]
            o_["net_usd"][rows] = net_a * A
            o_["r"][rows] = net_a / ((e.s if e.s > 0 else 1.0) + spA + cA)     # TIME: 1 ATR as the unit
            o_["exit_t"][rows] = np.where(ecol < N, tc[np.clip(ecol, 0, N - 1)], eod_t)
            o_["reason"][rows] = reason
            o_["conflict"][rows] = conflict


# ----------------------------------------------------------------------------- one position at a time

def one_at_a_time(t_entry: np.ndarray, t_exit: np.ndarray) -> np.ndarray:
    """Boolean mask of the trades taken when only one position may be open.

    Trades are visited in entry-time order (ties: input order); a trade is taken when its
    entry time is >= the exit time of the last taken trade."""
    t_entry = np.asarray(t_entry, dtype=np.int64)
    t_exit = np.asarray(t_exit, dtype=np.int64)
    order = np.argsort(t_entry, kind="mergesort")
    take = np.zeros(len(t_entry), dtype=bool)
    busy_until = np.iinfo(np.int64).min
    te, tx = t_entry[order].tolist(), t_exit[order].tolist()
    for pos, (a, b) in enumerate(zip(te, tx)):
        if a >= busy_until:
            take[order[pos]] = True
            busy_until = b
    return take
