"""Walk-forward folds, the pre-registered model families M1-M3, the trading rule and
the B1 day-block permutation (roadmap Section 5).

Pre-registered details not spelled out in the roadmap (frozen here, before data):

* The activation / fitting target is the net result in USD/oz (``primary_unit``).
* Bin edges are train-year quantiles of the rows used for that horizon. A feature
  with <= q distinct train values gets one bin per value (edges at midpoints).
  Bin b is the interval [edge_{b-1}, edge_b).
* Trading rule: a test moment trades long if at least one active rule of the family
  says long and none says short, short in the mirror case, and not at all on a
  conflict. One trade per moment, family and horizon; overlapping trades from
  different moments are counted independently.
* Moments with any missing feature (warm-up) are not in the dataset at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
from sklearn.tree import DecisionTreeRegressor

from .config import DEFAULT, F1Config, FAMILIES, horizon_name
from .data import year_of_day
from .stats import boot_weights, lower_bound_batch

SLOTS = 288


# ----------------------------------------------------------------------------- folds

def year_start_day(year: int) -> int:
    return int((np.datetime64(f"{year}-01-01", "D") - np.datetime64("1970-01-01", "D")).astype(np.int64))


def fold_masks(day: np.ndarray, train_years, test_year: int, cfg: F1Config = DEFAULT):
    """Train / test row masks for one expanding-window fold with a day embargo.

    Train rows: dated in ``train_years`` and strictly before
    ``test_start - embargo_days`` (so with a 1-day embargo Dec 31 is dropped).
    Test rows: dated in ``test_year``."""
    day = np.asarray(day)
    year = year_of_day(day)
    test_start = year_start_day(test_year)
    train = np.isin(year, list(train_years)) & (day < test_start - cfg.embargo_days)
    train &= year < test_year
    test = year == test_year
    return train, test


# ----------------------------------------------------------------------------- rules

@dataclass
class Cond:
    feature: str
    lo: float = -np.inf
    hi: float = np.inf
    lo_closed: bool = True
    hi_closed: bool = False

    def mask(self, X: dict) -> np.ndarray:
        x = X[self.feature]
        m = (x >= self.lo) if self.lo_closed else (x > self.lo)
        m &= (x <= self.hi) if self.hi_closed else (x < self.hi)
        return m

    def text(self) -> str:
        parts = []
        if np.isfinite(self.lo):
            parts.append(f"{self.lo:.4g} {'<=' if self.lo_closed else '<'} ")
        parts.append(self.feature)
        if np.isfinite(self.hi):
            parts.append(f" {'<=' if self.hi_closed else '<'} {self.hi:.4g}")
        return "".join(parts)

    def as_dict(self) -> dict:
        return {"feature": self.feature, "lo": _num(self.lo), "hi": _num(self.hi),
                "lo_closed": self.lo_closed, "hi_closed": self.hi_closed}


def _num(x):
    return None if not np.isfinite(x) else float(x)


@dataclass
class Rule:
    family: str
    horizon: str
    direction: int                 # +1 long, -1 short
    conds: list
    train: dict = field(default_factory=dict)
    rid: str = ""

    def mask(self, X: dict) -> np.ndarray:
        m = np.ones(len(next(iter(X.values()))), dtype=bool)
        for c in self.conds:
            m &= c.mask(X)
        return m

    def text(self) -> str:
        side = "LONG" if self.direction > 0 else "SHORT"
        cond = " and ".join(c.text() for c in self.conds) or "always"
        return f"if {cond} then {side} {self.horizon}"

    def as_dict(self) -> dict:
        return {"id": self.rid, "family": self.family, "horizon": self.horizon,
                "direction": "long" if self.direction > 0 else "short",
                "text": self.text(), "conditions": [c.as_dict() for c in self.conds],
                "train": self.train}


def rules_direction(rules: list, X: dict, n: int):
    """Family trading rule: direction per row (+1/-1/0) and, per rule, its firing mask."""
    long_any = np.zeros(n, dtype=bool)
    short_any = np.zeros(n, dtype=bool)
    masks = []
    for r in rules:
        m = r.mask(X)
        masks.append(m)
        if r.direction > 0:
            long_any |= m
        else:
            short_any |= m
    d = np.where(long_any & ~short_any, 1, np.where(short_any & ~long_any, -1, 0))
    return d, masks


# ----------------------------------------------------------------------------- binning

def make_edges(x: np.ndarray, q: int) -> np.ndarray:
    x = x[np.isfinite(x)]
    u = np.unique(x)
    if len(u) <= 1:
        return np.zeros(0)
    if len(u) <= q:
        return (u[:-1] + u[1:]) / 2.0
    e = np.unique(np.quantile(x, np.arange(1, q) / q))
    return e


def assign_bins(x: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.searchsorted(edges, x, side="right")


def bin_interval(edges: np.ndarray, b: int):
    lo = edges[b - 1] if b > 0 else -np.inf
    hi = edges[b] if b < len(edges) else np.inf
    return lo, hi


# ----------------------------------------------------------------------------- activation

class _Activation:
    """Collects candidate cells and activates them with the day-block bootstrap."""

    def __init__(self, train_day: np.ndarray, cfg: F1Config, seed):
        self.ud, self.dinv = np.unique(train_day, return_inverse=True)
        self.nd = len(self.ud)
        self.cfg = cfg
        self.seed = seed
        self.cand = []            # (meta, S column, N column)

    def offer(self, cell, ncell, y_long, y_short, meta_fn, min_n=0, min_days=0):
        key = self.dinv * ncell + cell
        size = self.nd * ncell
        Nmat = None
        n = np.bincount(cell, minlength=ncell)
        for direction, y in ((1, y_long), (-1, y_short)):
            tot = np.bincount(cell, weights=y, minlength=ncell)
            ok = (n > 0) & (n >= min_n)
            ok[ok] = tot[ok] > 0
            if not ok.any():
                continue
            if Nmat is None:
                Nmat = np.bincount(key, minlength=size).reshape(self.nd, ncell).astype(float)
                ndays = (Nmat > 0).sum(axis=0)
            ok &= ndays >= min_days
            if not ok.any():
                continue
            Smat = np.bincount(key, weights=y, minlength=size).reshape(self.nd, ncell)
            for c in np.flatnonzero(ok):
                self.cand.append((meta_fn(int(c), direction),
                                  {"n": int(n[c]), "days": int(ndays[c]), "mean_usd": float(tot[c] / n[c])},
                                  Smat[:, c], Nmat[:, c]))

    def activate(self):
        if not self.cand:
            return []
        S = np.stack([c[2] for c in self.cand], axis=1)
        N = np.stack([c[3] for c in self.cand], axis=1)
        W = boot_weights(self.nd, self.cfg.activation_boot, np.random.default_rng(self.seed))
        lower = lower_bound_batch(S, N, W, self.cfg.activation_alpha)
        out = []
        for (meta, st, _, _), lb in zip(self.cand, lower):
            if np.isfinite(lb) and lb > 0:
                st = dict(st, lower_usd=float(lb))
                out.append((meta, st))
        return out


def fit_m1(X: dict, y_long, y_short, day, hname: str, cfg: F1Config, seed) -> list:
    act = _Activation(day, cfg, seed)
    edges_by_f = {}
    for f in X:
        edges = make_edges(X[f], cfg.m1_bins)
        edges_by_f[f] = edges
        b = assign_bins(X[f], edges)

        def meta(c, direction, f=f, edges=edges):
            lo, hi = bin_interval(edges, c)
            return Rule("M1", hname, direction, [Cond(f, lo, hi)])
        act.offer(b, len(edges) + 1, y_long, y_short, meta)
    rules = []
    for rule, st in act.activate():
        rule.train = st
        rules.append(rule)
    return rules


def fit_m2(X: dict, y_long, y_short, day, hname: str, cfg: F1Config, seed) -> list:
    act = _Activation(day, cfg, seed)
    feats = list(X)
    edges = {f: make_edges(X[f], cfg.m2_bins) for f in feats}
    bins = {f: assign_bins(X[f], edges[f]) for f in feats}
    for fa, fb in combinations(feats, 2):
        nb = len(edges[fb]) + 1
        cell = bins[fa] * nb + bins[fb]
        ncell = (len(edges[fa]) + 1) * nb

        def meta(c, direction, fa=fa, fb=fb, nb=nb):
            la, ha = bin_interval(edges[fa], c // nb)
            lb, hb = bin_interval(edges[fb], c % nb)
            return Rule("M2", hname, direction, [Cond(fa, la, ha), Cond(fb, lb, hb)])
        act.offer(cell, ncell, y_long, y_short, meta, cfg.m2_min_moments, cfg.m2_min_days)
    rules = []
    for rule, st in act.activate():
        rule.train = st
        rules.append(rule)
    return rules


def _tree_leaf_conds(tree, feats):
    t = tree.tree_
    out = {}

    def walk(node, conds):
        if t.children_left[node] == -1:
            out[node] = conds
            return
        f = feats[t.feature[node]]
        thr = float(t.threshold[node])
        walk(t.children_left[node], conds + [Cond(f, -np.inf, thr, True, True)])
        walk(t.children_right[node], conds + [Cond(f, thr, np.inf, False, False)])
    walk(0, [])
    return out


def fit_m3(X: dict, y_long, y_short, day, hname: str, cfg: F1Config, seed) -> list:
    feats = list(X)
    A = np.column_stack([X[f] for f in feats])
    if len(A) < cfg.m3_min_leaf:
        return []
    tree = DecisionTreeRegressor(max_depth=cfg.m3_max_depth, min_samples_leaf=cfg.m3_min_leaf,
                                 random_state=0)
    tree.fit(A, y_long)
    leaf = tree.apply(A)
    paths = _tree_leaf_conds(tree, feats)
    rules = []
    for node, conds in paths.items():
        m = leaf == node
        n = int(m.sum())
        if n == 0:
            continue
        ml, ms = float(y_long[m].mean()), float(y_short[m].mean())
        st = {"n": n, "days": int(len(np.unique(day[m]))), "leaf": int(node),
              "mean_long_usd": ml, "mean_short_usd": ms}
        if ml > 0:
            rules.append(Rule("M3", hname, 1, conds, st))
        elif ms > 0:
            rules.append(Rule("M3", hname, -1, conds, st))
    return rules


FITTERS = {"M1": fit_m1, "M2": fit_m2, "M3": fit_m3}


# ----------------------------------------------------------------------------- permutation

def day_block_permutation(day: np.ndarray, slot: np.ndarray, mask: np.ndarray, rng: np.random.Generator):
    """B1 shuffle: every day inside ``mask`` receives the targets of one other day of the
    mask, slot by slot (time of day is kept). Returns (source row per row or -1, mapping
    {day: source day})."""
    day = np.asarray(day, dtype=np.int64)
    slot = np.asarray(slot, dtype=np.int64)
    idx = np.flatnonzero(mask)
    src = np.full(len(day), -1, dtype=np.int64)
    if len(idx) == 0:
        return src, {}
    ud = np.unique(day[idx])
    perm = rng.permutation(len(ud))
    mapping = dict(zip(ud.tolist(), ud[perm].tolist()))
    keys = day[idx] * SLOTS + slot[idx]
    order = np.argsort(keys, kind="mergesort")
    skeys = keys[order]
    src_day = ud[perm][np.searchsorted(ud, day[idx])]
    want = src_day * SLOTS + slot[idx]
    pos = np.clip(np.searchsorted(skeys, want), 0, len(skeys) - 1)
    hit = skeys[pos] == want
    src[idx] = np.where(hit, idx[order][pos], -1)
    return src, mapping


# ----------------------------------------------------------------------------- walk-forward

@dataclass
class Dataset:
    """Arrays of the modelling dataset (rows = decision moments with complete features)."""
    X: dict                  # feature name -> float array
    day: np.ndarray
    slot: np.ndarray
    t: np.ndarray            # decision time, minutes
    y: dict                  # "long_H60" etc. -> float array (NaN = invalid)

    @property
    def n(self) -> int:
        return len(self.day)


def target_keys(cfg: F1Config = DEFAULT):
    keys = []
    for h in cfg.horizons:
        hn = horizon_name(h)
        keys += [f"long_{hn}", f"short_{hn}", f"long_atr_{hn}", f"short_atr_{hn}"]
    return keys


def permuted_targets(ds: Dataset, train_mask: np.ndarray, rng, cfg: F1Config = DEFAULT, keys=None) -> dict:
    src, _ = day_block_permutation(ds.day, ds.slot, train_mask, rng)
    y = {}
    for k in (target_keys(cfg) if keys is None else keys):
        v = ds.y[k].copy()
        idx = np.flatnonzero(train_mask)
        s = src[idx]
        v[idx] = np.where(s >= 0, ds.y[k][np.clip(s, 0, None)], np.nan)
        y[k] = v
    return y


def run_walkforward(ds: Dataset, cfg: F1Config = DEFAULT, perm_run: int | None = None,
                    keep_rules: bool = True, targets=None) -> dict:
    """Run M1-M3 for every fold and horizon.

    ``perm_run=None`` is the real run; an integer k runs the B1 null with the train
    targets day-block shuffled (seed derived from ``cfg.seed`` and k).

    Returns {(family, horizon): {"rows", "dir", "net_usd", "net_atr", "fold_rules"}}
    where rows index the dataset (out-of-fold test trades).

    ``targets`` (F3): target names to use instead of the F1 horizons; the dataset must hold
    ``long_<name>`` / ``short_<name>``. Without it, F1 behaviour is unchanged."""
    names = [horizon_name(h) for h in cfg.horizons] if targets is None else list(targets)
    perm_keys = None if targets is None else [f"{s}_{n}" for n in names for s in ("long", "short")]
    out = {(fam, hn): {"rows": [], "dir": [], "net_usd": [], "net_atr": [],
                       "fold_rules": {}, "rule_hits": []}
           for fam in FAMILIES for hn in names}
    for fi, (train_years, test_year) in enumerate(cfg.folds):
        tr, te = fold_masks(ds.day, train_years, test_year, cfg)
        if perm_run is None:
            ytr = ds.y
        else:
            rng = np.random.default_rng([cfg.seed, 1, int(perm_run), fi])
            ytr = permuted_targets(ds, tr, rng, cfg, keys=perm_keys)
        for hi, hn in enumerate(names):
            yl, ys = ytr[f"long_{hn}"], ytr[f"short_{hn}"]
            m_tr = tr & np.isfinite(yl) & np.isfinite(ys)
            m_te = te & np.isfinite(ds.y[f"long_{hn}"])
            Xtr = {f: v[m_tr] for f, v in ds.X.items()}
            Xte = {f: v[m_te] for f, v in ds.X.items()}
            rows_te = np.flatnonzero(m_te)
            for fam in FAMILIES:
                seed = [cfg.seed, 2, -1 if perm_run is None else int(perm_run), fi, hi, FAMILIES.index(fam)]
                seed = [s % (2 ** 32) for s in seed]
                rules = FITTERS[fam](Xtr, yl[m_tr], ys[m_tr], ds.day[m_tr], hn, cfg, seed)
                for k, r in enumerate(rules):
                    r.rid = f"{fam}-{hn}-{test_year}-{k:03d}"
                d, masks = rules_direction(rules, Xte, len(rows_te))
                take = d != 0
                rows = rows_te[take]
                dd = d[take]
                o = out[(fam, hn)]
                o["rows"].append(rows)
                o["dir"].append(dd)
                o["net_usd"].append(np.where(dd > 0, ds.y[f"long_{hn}"][rows], ds.y[f"short_{hn}"][rows]))
                if f"long_atr_{hn}" in ds.y:
                    o["net_atr"].append(np.where(dd > 0, ds.y[f"long_atr_{hn}"][rows], ds.y[f"short_atr_{hn}"][rows]))
                else:
                    o["net_atr"].append(o["net_usd"][-1])
                if keep_rules:
                    o["fold_rules"][test_year] = rules
                    # trades (indices into the concatenated out-of-fold trades) each rule fired on
                    offset = sum(len(x) for x in o["rows"][:-1])
                    for r, m in zip(rules, masks):
                        o["rule_hits"].append((r, offset + np.flatnonzero(m[take] & (r.direction == dd))))
    for o in out.values():
        for k in ("rows", "dir", "net_usd", "net_atr"):
            o[k] = np.concatenate(o[k]) if o[k] else np.zeros(0)
    return out


def oof_mean(res: dict) -> dict:
    """Mean net USD per out-of-fold trade per configuration (NaN when there is no trade;
    the p-value scores such a run as 0, see ``stats.permutation_pvalue``)."""
    return {k: (float(v["net_usd"].mean()) if len(v["net_usd"]) else float("nan")) for k, v in res.items()}
