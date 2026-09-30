"""Statistics: day-block bootstrap, permutation p-values, Holm-Bonferroni, verdict
(roadmap Sections 5.2, 5.3 and 6)."""
from __future__ import annotations

import numpy as np

from .config import DEFAULT, F1Config


# ----------------------------------------------------------------------------- bootstrap

def day_sums(values: np.ndarray, days: np.ndarray):
    """Per-day sum and count. Returns (unique days, sums, counts)."""
    values = np.asarray(values, float)
    ud, inv = np.unique(np.asarray(days), return_inverse=True)
    return ud, np.bincount(inv, weights=values, minlength=len(ud)), np.bincount(inv, minlength=len(ud)).astype(float)


def boot_weights(n_days: int, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    """(n_boot, n_days) matrix: how often each day is drawn in each resample
    (n_days draws with replacement)."""
    idx = rng.integers(0, n_days, size=(n_boot, n_days))
    flat = idx + (np.arange(n_boot) * n_days)[:, None]
    return np.bincount(flat.ravel(), minlength=n_boot * n_days).reshape(n_boot, n_days).astype(float)


def boot_means_from_weights(W: np.ndarray, S: np.ndarray, N: np.ndarray) -> np.ndarray:
    """Bootstrap means (n_boot, K) of K candidates given per-day sums S and counts N (n_days, K).
    A resample in which a candidate has no observation gives NaN."""
    num = W @ S
    den = W @ N
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)


def lower_bound_batch(S: np.ndarray, N: np.ndarray, W: np.ndarray, alpha: float) -> np.ndarray:
    """One-sided lower (1 - alpha) day-block bootstrap bound of the mean, per candidate."""
    if S.shape[1] == 0:
        return np.zeros(0)
    bm = boot_means_from_weights(W, S, N)
    return nan_quantile_columns(bm, alpha)


def nan_quantile_columns(a: np.ndarray, q: float) -> np.ndarray:
    """Column-wise quantile ignoring NaN (linear interpolation, as numpy's default).
    Same result as ``np.nanquantile(a, q, axis=0)``, much faster for many columns."""
    s = np.sort(a, axis=0)                      # NaN sort last
    k = np.isfinite(a).sum(axis=0)
    out = np.full(a.shape[1], np.nan)
    ok = k > 0
    pos = q * (k[ok] - 1)
    lo = np.floor(pos).astype(np.int64)
    hi = np.minimum(lo + 1, k[ok] - 1)
    cols = np.flatnonzero(ok)
    frac = pos - lo
    out[ok] = s[lo, cols] + (s[hi, cols] - s[lo, cols]) * frac
    return out


def day_block_bootstrap(values, days, n_boot: int, seed, alpha: float = 0.05) -> dict:
    """Day-block bootstrap of the mean of ``values`` (all rows of a day move together).

    Returns mean, the one-sided lower (1-alpha) bound, the upper (1-alpha) bound and
    the number of days. Deterministic for a given seed."""
    values = np.asarray(values, float)
    if len(values) == 0:
        return {"mean": float("nan"), "lower": float("nan"), "upper": float("nan"), "days": 0, "n": 0}
    ud, s, c = day_sums(values, days)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ud), size=(n_boot, len(ud)))
    bm = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    return {
        "mean": float(values.mean()),
        "lower": float(np.quantile(bm, alpha)),
        "upper": float(np.quantile(bm, 1 - alpha)),
        "days": int(len(ud)),
        "n": int(len(values)),
    }


# ----------------------------------------------------------------------------- permutation

def permutation_pvalue(real: float, null) -> float:
    """Share of null runs with a statistic >= the real one (roadmap Section 6).

    A null run without trades (NaN) scores 0. A real statistic that is NaN (no trades)
    gets p = 1."""
    null = np.nan_to_num(np.asarray(null, float), nan=0.0)
    if not np.isfinite(real) or len(null) == 0:
        return 1.0
    return float(np.mean(null >= real))


def holm(pvals, alpha: float = 0.05):
    """Holm-Bonferroni step-down. Returns (adjusted p-values, reject flags) in input order."""
    p = np.asarray(pvals, float)
    m = len(p)
    order = np.argsort(p, kind="mergesort")
    adj_sorted = np.minimum(1.0, np.maximum.accumulate((m - np.arange(m)) * p[order]))
    adj = np.empty(m)
    adj[order] = adj_sorted
    return adj, adj < alpha


# ----------------------------------------------------------------------------- verdict

def config_flags(row: dict, test_years, cfg: F1Config = DEFAULT) -> dict:
    """PASS/WEAK conditions for one configuration row of the results table."""
    mean = row.get("mean_usd", float("nan"))
    per_year = row.get("per_year", {})
    each_year = all(
        per_year.get(str(y), {}).get("trades", 0) > 0 and per_year[str(y)]["mean_usd"] > 0
        for y in test_years)
    pos = bool(np.isfinite(mean) and mean > 0)
    return {
        "positive_mean": pos,
        "p_raw_ok": bool(row.get("p_perm", 1.0) < cfg.alpha),
        "p_holm_ok": bool(row.get("p_holm", 1.0) < cfg.alpha),
        "boot_lower_ok": bool(np.isfinite(row.get("boot_lower_usd", np.nan)) and row["boot_lower_usd"] > 0),
        "each_year_positive": bool(each_year),
    }


def verdict(rows: list[dict], test_years, cfg: F1Config = DEFAULT) -> str:
    passed = weak = False
    for r in rows:
        fl = config_flags(r, test_years, cfg)
        r["flags"] = fl
        r["passes"] = fl["p_holm_ok"] and fl["boot_lower_ok"] and fl["positive_mean"] and fl["each_year_positive"]
        passed |= r["passes"]
        weak |= fl["positive_mean"] and fl["p_raw_ok"]
    if passed:
        return "F1_PASS"
    if weak:
        return "F1_WEAK"
    return "F1_STOP"


# ----------------------------------------------------------------------------- F3: reality check on the maximum

def null_max(null_means: np.ndarray) -> np.ndarray:
    """Per permutation run, the best out-of-fold mean over all configurations
    (roadmap Section 12.5). ``null_means`` is (runs, configurations); a configuration
    without trades in a run scores 0, as in F1."""
    a = np.nan_to_num(np.asarray(null_means, float), nan=0.0)
    if a.ndim != 2 or a.shape[1] == 0:
        return np.zeros(a.shape[0] if a.ndim else 0)
    return a.max(axis=1)


def max_stat_pvalue(real: float, null_best) -> float:
    """Share of permutation runs whose best configuration is >= the real mean (a NaN real
    mean, i.e. no trades, gets p = 1)."""
    null_best = np.asarray(null_best, float)
    if not np.isfinite(real) or len(null_best) == 0:
        return 1.0
    return float(np.mean(null_best >= real))


def max_drawdown(values) -> float:
    """Largest peak-to-trough fall of the cumulative sum (starting from 0), >= 0."""
    c = np.cumsum(np.r_[0.0, np.asarray(values, float)])
    return float(np.max(np.maximum.accumulate(c) - c))
