"""Holm and bootstrap: determinism and known small cases; the verdict rule; bin
activation and the model families on tiny cases (roadmap Section 8)."""
import numpy as np
import pytest

from edgelab.config import DEFAULT
from edgelab.models import (Cond, Rule, assign_bins, bin_interval, fit_m1, fit_m2, fit_m3, make_edges,
                            rules_direction)
from edgelab.stats import (boot_weights, day_block_bootstrap, holm, lower_bound_batch, nan_quantile_columns,
                           permutation_pvalue, verdict)


# ----------------------------------------------------------------------------- Holm

def test_holm_known_case():
    adj, rej = holm([0.01, 0.04, 0.03, 0.005], 0.05)
    # sorted 0.005, 0.01, 0.03, 0.04 -> 4*0.005=0.02, 3*0.01=0.03, 2*0.03=0.06, max(1*0.04, 0.06)=0.06
    assert adj == pytest.approx([0.03, 0.06, 0.06, 0.02])
    assert rej.tolist() == [True, False, False, True]


def test_holm_twelve_configs_and_bounds():
    p = [0.0] + [0.5] * 11
    adj, rej = holm(p, 0.05)
    assert adj[0] == 0.0 and rej.tolist() == [True] + [False] * 11
    # with 12 configurations the smallest p must be < 0.05/12 to be rejected
    adj, rej = holm([0.004] + [0.9] * 11, 0.05)
    assert adj[0] == pytest.approx(0.048) and rej[0]
    adj, rej = holm([0.005] + [0.9] * 11, 0.05)
    assert adj[0] == pytest.approx(0.06) and not rej[0]
    adj, _ = holm([0.9, 0.95, 0.99], 0.05)
    assert (adj <= 1.0).all()


def test_holm_is_deterministic_with_ties():
    p = [0.01, 0.01, 0.02, 0.5]
    a1, r1 = holm(p)
    a2, r2 = holm(list(p))
    assert np.array_equal(a1, a2) and np.array_equal(r1, r2)
    assert a1 == pytest.approx([0.04, 0.04, 0.04, 0.5])


# ----------------------------------------------------------------------------- bootstrap

def test_bootstrap_deterministic_for_seed():
    rng = np.random.default_rng(0)
    v = rng.normal(0.1, 1, 500)
    d = rng.integers(0, 60, 500)
    a = day_block_bootstrap(v, d, 10000, 20260930)
    b = day_block_bootstrap(v, d, 10000, 20260930)
    c = day_block_bootstrap(v, d, 10000, 1)
    assert a == b
    assert a["lower"] != c["lower"]
    assert a["mean"] == pytest.approx(v.mean())
    assert a["lower"] < a["mean"] < a["upper"]


def test_bootstrap_constant_values():
    r = day_block_bootstrap(np.full(50, 0.7), np.repeat(np.arange(10), 5), 2000, 1)
    assert r["lower"] == pytest.approx(0.7) and r["upper"] == pytest.approx(0.7)


def test_bootstrap_two_days_known_distribution():
    # two days with one value each: resampled means are 0, 0.5, 1 with prob 1/4, 1/2, 1/4
    r = day_block_bootstrap([0.0, 1.0], [1, 2], 10000, 20260930)
    assert r["lower"] == 0.0 and r["upper"] == 1.0 and r["days"] == 2


def test_bootstrap_resamples_whole_days():
    # day A: many +1 rows, day B: one -1 row. Row-level resampling would almost never give
    # a mean below 0.9; day blocks give -1 whenever only day B is drawn (prob 1/4).
    v = np.r_[np.ones(99), -1.0]
    d = np.r_[np.zeros(99), 1]
    r = day_block_bootstrap(v, d, 10000, 20260930, alpha=0.05)
    assert r["lower"] == -1.0
    # row order does not matter, only the day labels do
    perm = np.random.default_rng(2).permutation(100)
    assert day_block_bootstrap(v[perm], d[perm], 10000, 20260930)["lower"] == -1.0


def test_batch_lower_bound_matches_direct_computation():
    rng = np.random.default_rng(4)
    nd, K = 30, 5
    S = rng.normal(size=(nd, K))
    N = rng.integers(0, 4, size=(nd, K)).astype(float)
    W = boot_weights(nd, 500, np.random.default_rng(7))
    assert W.shape == (500, nd) and (W.sum(axis=1) == nd).all()
    got = lower_bound_batch(S, N, W, 0.05)
    with np.errstate(invalid="ignore", divide="ignore"):
        bm = (W @ S) / (W @ N)
    bm[~np.isfinite(bm)] = np.nan
    assert got == pytest.approx(np.nanquantile(bm, 0.05, axis=0))
    a = rng.normal(size=(200, 7))
    a[rng.random(a.shape) < 0.2] = np.nan
    assert nan_quantile_columns(a, 0.05) == pytest.approx(np.nanquantile(a, 0.05, axis=0))


def test_permutation_pvalue():
    assert permutation_pvalue(1.0, [0, 1, 2, 0.5]) == 0.5
    assert permutation_pvalue(3.0, [0, 1, 2, 0.5]) == 0.0
    assert permutation_pvalue(float("nan"), [0, 1]) == 1.0
    # a shuffled run without trades (NaN) scores 0
    assert permutation_pvalue(0.1, [np.nan, np.nan, 0.2, -0.3]) == 0.25
    assert permutation_pvalue(-0.1, [np.nan, 0.2]) == 1.0


# ----------------------------------------------------------------------------- verdict

def _row(mean, p, holm_p, lower, years=(0.1, 0.1, 0.1)):
    return {"mean_usd": mean, "p_perm": p, "p_holm": holm_p, "boot_lower_usd": lower,
            "per_year": {str(y): {"trades": 10, "mean_usd": v} for y, v in zip((2020, 2021, 2022), years)}}


def test_verdict_rules():
    ty = (2020, 2021, 2022)
    assert verdict([_row(0.2, 0.0, 0.0, 0.05)], ty) == "F1_PASS"
    assert verdict([_row(0.2, 0.0, 0.0, 0.05, (0.1, -0.1, 0.3))], ty) == "F1_WEAK"   # one year negative
    assert verdict([_row(0.2, 0.0, 0.0, -0.01)], ty) == "F1_WEAK"                    # bootstrap bound
    assert verdict([_row(0.2, 0.01, 0.12, 0.05)], ty) == "F1_WEAK"                   # fails Holm
    assert verdict([_row(0.2, 0.2, 1.0, 0.05)], ty) == "F1_STOP"
    assert verdict([_row(-0.1, 0.0, 0.0, -0.2)], ty) == "F1_STOP"                    # negative mean
    rows = [_row(-0.1, 0.9, 1, -1), _row(0.3, 0.0, 0.0, 0.1)]
    assert verdict(rows, ty) == "F1_PASS" and rows[1]["passes"] and not rows[0]["passes"]
    no_trades = _row(0.2, 0.0, 0.0, 0.05)
    no_trades["per_year"]["2021"] = {"trades": 0, "mean_usd": float("nan")}
    assert verdict([no_trades], ty) == "F1_WEAK"


# ----------------------------------------------------------------------------- models on tiny cases

def test_bins_and_intervals():
    x = np.arange(100, dtype=float)
    e = make_edges(x, 10)
    assert len(e) == 9
    b = assign_bins(x, e)
    assert np.bincount(b).tolist() == [10] * 10
    lo, hi = bin_interval(e, 3)
    assert ((x >= lo) & (x < hi)).sum() == 10
    # discrete feature: one bin per value
    w = np.array([0, 1, 2, 3, 4] * 20, dtype=float)
    e = make_edges(w, 10)
    assert e.tolist() == [0.5, 1.5, 2.5, 3.5]
    assert np.bincount(assign_bins(w, e)).tolist() == [20] * 5


def _planted_bins(n_days=120, per_day=40, seed=0):
    rng = np.random.default_rng(seed)
    n = n_days * per_day
    day = np.repeat(np.arange(n_days), per_day)
    X = {"a": rng.normal(size=n), "b": rng.normal(size=n), "c": rng.uniform(size=n)}
    # the top decile of a drifts up by 1; the move is centred so that no other bin has an
    # edge (unconditional mean ~0: every non-planted bin loses the cost on average)
    move = rng.normal(0, 1, n) + np.where(X["a"] > 1.28, 1.0, -0.1 / 0.9)
    cost = 0.1
    return X, move - cost, -move - cost, day


def test_m1_finds_planted_bin_only():
    X, yl, ys, day = _planted_bins()
    rules = fit_m1(X, yl, ys, day, "H60", DEFAULT, 1)
    assert len(rules) >= 1
    top = [r for r in rules if r.conds[0].feature == "a" and r.direction == 1]
    assert top and all(r.conds[0].lo > 1.0 for r in top)
    assert all(r.conds[0].feature == "a" for r in rules)
    assert all(r.train["lower_usd"] > 0 and r.train["mean_usd"] > 0 for r in rules)
    # deterministic
    again = fit_m1(X, yl, ys, day, "H60", DEFAULT, 1)
    assert [r.text() for r in again] == [r.text() for r in rules]


def test_m1_rejects_noise():
    rng = np.random.default_rng(1)
    n = 120 * 40
    day = np.repeat(np.arange(120), 40)
    X = {f"f{i}": rng.normal(size=n) for i in range(5)}
    move = rng.normal(0, 1, n)
    rules = fit_m1(X, move - 0.2, -move - 0.2, day, "H60", DEFAULT, 1)
    assert rules == []


def test_m2_cell_support_rules():
    X, yl, ys, day = _planted_bins()
    rules = fit_m2(X, yl, ys, day, "H60", DEFAULT, 1)
    assert rules and all(r.train["n"] >= 200 and r.train["days"] >= 50 for r in rules)
    assert all(any(c.feature == "a" and c.lo > 0.5 for c in r.conds) for r in rules)
    strict = fit_m2(X, yl, ys, day, "H60", DEFAULT.with_(m2_min_days=500), 1)
    assert strict == []


def test_m3_tree_rules_are_readable_and_match_tree():
    X, yl, ys, day = _planted_bins()
    rules = fit_m3(X, yl, ys, day, "H60", DEFAULT, 1)
    assert rules and all(r.family == "M3" for r in rules)
    assert all(r.train["n"] >= DEFAULT.m3_min_leaf for r in rules)
    longs = [r for r in rules if r.direction == 1]
    assert any(any(c.feature == "a" and np.isfinite(c.lo) and c.lo > 0.8 for c in r.conds) for r in longs)
    for r in rules:
        assert r.text().startswith("if ") and ("LONG" in r.text() or "SHORT" in r.text())
        assert len(r.conds) <= DEFAULT.m3_max_depth


def test_family_trading_rule_conflicts_and_union():
    X = {"x": np.array([0.0, 1.0, 2.0, 3.0])}
    r_long = Rule("M1", "H60", 1, [Cond("x", 1.0, 3.0)])      # x in [1, 3)
    r_short = Rule("M1", "H60", -1, [Cond("x", 2.0, np.inf)])  # x >= 2
    d, masks = rules_direction([r_long, r_short], X, 4)
    assert d.tolist() == [0, 1, 0, -1]                          # x=2 is a conflict -> no trade
    assert masks[0].tolist() == [False, True, True, False]
