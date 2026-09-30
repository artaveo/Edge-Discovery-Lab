"""F3 end-to-end (roadmap Section 12.7): the planted "+2R then reverse" pattern is found with a
take-profit exit and not with a time exit; a random walk gives F3_STOP; the reality check on the
maximum is deterministic and bounded; one position at a time holds; the report is written.

Synthetic data: ``synth.make_m1_f3`` (2020-07 .. 2022, 120 weekdays per year, 06:00-22:00,
XAUUSD-like costs). The planted pattern starts on a tick-volume spike and moves 4 x ATR in the
direction of that M5 bar within 10 minutes, then all the way back within 30 minutes, so a
time exit (EOD) sees about zero. The whole pre-registered pipeline runs (M1-M3, 2 folds,
activation rules, one position at a time, day-block permutations with the maximum statistic,
bootstrap, verdict); only the exit grid is reduced and 40 permutations are used, to keep the
tests fast. The take-profit grid is checked on seeds 1-3 when the test was written (all
F3_PASS; the noise runs all F3_STOP); the test uses seed 1.
"""
import json
import os

import numpy as np
import pytest

from edgelab import f3
from edgelab.config import DEFAULT, FAMILIES
from edgelab.data import InstrumentSpec, year_of_day
from edgelab.exits import EXIT_GRID, ExitRule, TIME_EXIT, simulate
from edgelab.stats import max_drawdown, max_stat_pvalue, null_max
from synth import make_m1_f3

CFG = DEFAULT.with_(n_perm=40)
JOBS = min(4, os.cpu_count() or 1)
PLANT = dict(days_per_year=120, seed=1, up_atr=4.0, up_min=10, back_min=30, trigger_prob=0.10)
TP_EXITS = [ExitRule("sltp", 1.0, 1.0), ExitRule("sltp", 1.0, 2.0), ExitRule("sltp", 0.5, 3.0), ExitRule("be", 1.0, 2.0)]


def _table(res):
    return "\n".join(f"{r['family']} {r['exit']}: n={r['trades']} mean={r['mean_r']:.3f} low={r['boot_lower_r']:.3f} "
                     f"p={r['p_rc']:.3f} {r['checks']}" for r in res["rows"])


@pytest.fixture(scope="module")
def planted_df():
    return make_m1_f3(planted=True, **PLANT)


@pytest.fixture(scope="module")
def planted_tp(planted_df):
    p3 = f3.prepare_f3(planted_df, InstrumentSpec(), CFG, TP_EXITS)
    return p3, f3.run_f3(p3, CFG, jobs=JOBS, check_fingerprint=False)


@pytest.fixture(scope="module")
def noise_tp():
    p3 = f3.prepare_f3(make_m1_f3(planted=False, days_per_year=120, seed=1), InstrumentSpec(), CFG, TP_EXITS)
    return p3, f3.run_f3(p3, CFG, jobs=JOBS, check_fingerprint=False)


def test_planted_pattern_passes_with_a_take_profit_exit(planted_tp):
    p3, res = planted_tp
    assert res["verdict"] == "F3_PASS", _table(res)
    passing = [r for r in res["rows"] if r["passes"]]
    assert passing and all(("TP" in r["exit"]) for r in passing)
    for r in passing:
        assert all(r["per_year"][y]["mean_r"] > 0 and r["per_year"][y]["trades"] >= 100 for y in ("2021", "2022"))
        assert r["boot_lower_r"] > 0 and r["p_rc"] < 0.05
        assert all(r["per_year"][y]["mean_r"] > max(r["b0"]["long"][y], r["b0"]["short"][y]) for y in ("2021", "2022"))


def test_planted_pattern_fails_with_the_time_exit(planted_df):
    p3 = f3.prepare_f3(planted_df, InstrumentSpec(), CFG, [TIME_EXIT])
    res = f3.run_f3(p3, CFG, jobs=JOBS, check_fingerprint=False)
    assert res["verdict"] != "F3_PASS", _table(res)
    assert not any(r["passes"] for r in res["rows"])


def test_random_walk_reaches_stop(noise_tp):
    _, res = noise_tp
    assert res["verdict"] == "F3_STOP", _table(res)


def test_one_position_at_a_time_in_the_pipeline(planted_tp):
    p3, res = planted_tp
    for fam in FAMILIES:
        for n in p3.names:
            tr = f3.config_trades(p3.ds, res["real"][(fam, n)], n)
            k = np.flatnonzero(tr["take"])
            if len(k) < 2:
                continue
            order = k[np.argsort(tr["t"][k], kind="mergesort")]
            assert (tr["t"][order][1:] >= tr["exit_t"][order][:-1]).all()     # no overlap
            assert tr["take"].sum() <= len(tr["take"])
    row = next(r for r in res["rows"] if r["passes"])
    assert row["trades"] < row["all_moments"]["trades"]                        # signals were skipped


def test_reality_check_is_deterministic_and_bounded(planted_tp):
    p3, res = planted_tp
    cfg = DEFAULT.with_(n_perm=3)
    a = f3.run_null(p3, cfg, jobs=1)
    b = f3.run_null(p3, cfg, jobs=min(2, JOBS))
    assert np.array_equal(a, b, equal_nan=True) and a.shape == (3, len(FAMILIES) * len(TP_EXITS))
    assert np.array_equal(a, res["null"][:3], equal_nan=True)                  # same seeds as the full run
    best = null_max(res["null"])
    for i, r in enumerate(res["rows"]):
        assert 0.0 <= r["p_rc"] <= 1.0
        own = np.nan_to_num(res["null"][:, i], nan=0.0)
        if np.isfinite(r["mean_r"]):
            # the maximum statistic is never less conservative than the configuration's own null
            assert r["p_rc"] >= float(np.mean(own >= r["mean_r"]))
            assert r["p_rc"] == float(np.mean(best >= r["mean_r"]))
        else:
            assert r["p_rc"] == 1.0


def test_max_statistic_small_cases():
    null = np.array([[0.1, np.nan, -0.2], [np.nan, np.nan, np.nan], [0.3, 0.2, 0.0]])
    assert null_max(null).tolist() == [0.1, 0.0, 0.3]
    assert max_stat_pvalue(0.2, null_max(null)) == pytest.approx(1 / 3)
    assert max_stat_pvalue(0.35, null_max(null)) == 0.0
    assert max_stat_pvalue(-1.0, null_max(null)) == 1.0
    assert max_stat_pvalue(float("nan"), null_max(null)) == 1.0
    assert max_drawdown([1, -2, 1, -3, 5]) == pytest.approx(4.0)
    assert max_drawdown([1, 2, 3]) == 0.0


def test_report_files(planted_tp, tmp_path):
    p3, res = planted_tp
    s = f3.write_report(p3, res, tmp_path, CFG, manifest={"files": [{"file": "x.csv.gz", "sha256": "ab" * 32}]},
                        tests_summary="synthetic")
    md = (tmp_path / "report.md").read_text()
    js = json.loads((tmp_path / "report.json").read_text())
    assert "F3_PASS" in md and js["verdict"] == "F3_PASS" and "F3 — COMPLETE" in md
    assert js["n_configurations"] == len(FAMILIES) * len(TP_EXITS)
    assert s["charts"]
    for items in s["charts"].values():
        assert 1 <= len(items) <= f3.N_EXAMPLES
        for it in items:
            svg = (tmp_path / it["file"]).read_text()
            assert svg.startswith("<svg") and "</svg>" in svg
    assert len((tmp_path / "trials_ledger.jsonl").read_text().strip().splitlines()) == 1
    assert f3.main(["--out", str(tmp_path), "--data", str(tmp_path)]) == 2     # runs once


def test_full_grid_is_84_configurations_and_simulates(planted_df):
    """The pre-registered grid on a short slice: 28 exits x 2 sides simulate, 84 configurations
    run end to end (2 permutations only)."""
    small = planted_df[planted_df["time"] < "2021-03-01"]                     # 2020-07 .. 2021-02
    p3 = f3.prepare_f3(small, InstrumentSpec(), DEFAULT, EXIT_GRID)
    assert len(p3.names) == 28
    for e in EXIT_GRID:
        for side in ("long", "short"):
            r, u = p3.ds.y[f"{side}_{e.name}"], p3.ds.y[f"usd_{side}_{e.name}"]
            ok = np.isfinite(r)
            assert ok.mean() > 0.9
            assert (np.sign(r[ok]) == np.sign(u[ok])).all()
            assert set(np.unique(p3.ds.y[f"reason_{side}_{e.name}"][ok])) <= {0, 1, 2, 3, 4}
            if e.kind in ("sltp", "sl", "be"):
                # a loss can never be much worse than the stop (gaps aside, which are rare here)
                assert np.quantile(r[ok], 0.01) > -1.5
    cfg = DEFAULT.with_(n_perm=2, folds=(((2020,), 2021),))
    res = f3.run_f3(p3, cfg, jobs=JOBS, check_fingerprint=False)
    assert len(res["rows"]) == 84 and res["null"].shape == (2, 84)
    assert res["verdict"] in ("F3_PASS", "F3_WEAK", "F3_STOP")


def test_f1_config_is_unchanged():
    assert DEFAULT.fingerprint() == f3.F1_FINGERPRINT
    with pytest.raises(RuntimeError):
        f3.run_f3(None, DEFAULT.with_(n_perm=1))
