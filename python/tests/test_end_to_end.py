"""End-to-end: the machine finds a planted pattern and rejects noise (roadmap Section 8).

Synthetic 2019-2022 (120 weekdays per year, 06:00-22:00 sessions) with XAUUSD-like
cost: spread 25-28 points (0.25-0.28 USD) plus commission, about 0.27 ATR60 per trade.

* planted: after r60 > 2 ATR the next 60 min drift +0.6 ATR (mirror image below
  -2 ATR). The roadmap's example size (0.3 ATR) is about the same as the synthetic
  cost and so not an edge *net of cost*; 0.6 ATR is. -> must reach F1_PASS.
* random walk with the same costs -> must reach F1_STOP.

The whole pre-registered pipeline runs (M1-M3 x 4 horizons x 3 folds, B1 with a day
block shuffle, bootstrap, Holm); only the number of permutation runs is reduced to 20
to keep the test fast (p = 0/20 is still resolvable below the Holm threshold).
"""
import json
import os

import numpy as np
import pytest

from edgelab.config import DEFAULT
from edgelab.data import InstrumentSpec
from edgelab.report import prepare, run_f1, write_report
from synth import make_m1

CFG = DEFAULT.with_(n_perm=20)
JOBS = min(4, os.cpu_count() or 1)
SYNTH = dict(days_per_year=120, sigma=0.3, spread_pts=25)


@pytest.fixture(scope="module")
def planted():
    df = make_m1(planted=True, trigger_atr=2.0, drift_atr=0.6, seed=1, **SYNTH)
    prep = prepare(df, InstrumentSpec(), CFG)
    return prep, run_f1(prep, CFG, jobs=JOBS)


@pytest.fixture(scope="module")
def noise():
    df = make_m1(planted=False, seed=1, **SYNTH)
    prep = prepare(df, InstrumentSpec(), CFG)
    return prep, run_f1(prep, CFG, jobs=JOBS)


def _table(res):
    return "\n".join(f"{r['family']} {r['horizon']}: n={r['trades']} mean={r['mean_usd']:.4f} "
                     f"low={r['boot_lower_usd']:.4f} p={r['p_perm']:.3f} holm={r['p_holm']:.3f} "
                     f"pass={r.get('passes')}" for r in res["rows"])


def test_planted_edge_reaches_pass(planted):
    prep, res = planted
    assert res["verdict"] == "F1_PASS", _table(res)
    passing = [r for r in res["rows"] if r["passes"]]
    # the planted horizon is found, and by more than one model family
    assert any(r["horizon"] == "H60" for r in passing), _table(res)
    assert len({r["family"] for r in passing}) >= 2, _table(res)
    for r in passing:
        assert r["p_holm"] < 0.05 and r["boot_lower_usd"] > 0
        assert all(v["mean_usd"] > 0 for v in r["per_year"].values())
    # the readable M1 rules point at the planted feature: large |r60| -> trade with it
    m1 = res["real"][("M1", "H60")]["fold_rules"]
    r60 = [r for rules in m1.values() for r in rules if r.conds[0].feature == "r60"]
    assert r60, "M1 H60 did not use r60"
    assert all((r.direction == 1 and r.conds[0].lo > 0) or (r.direction == -1 and r.conds[0].hi < 0)
               for r in r60)


def test_random_walk_reaches_stop(noise):
    prep, res = noise
    assert res["verdict"] == "F1_STOP", _table(res)
    assert not any(r["passes"] for r in res["rows"])


def test_baseline_b0_is_the_cost_floor(noise):
    _, res = noise
    for b in res["b0"]:
        assert b["trades"] > 0 and b["mean_usd"] < 0          # always long / short lose the cost


def test_null_runs_are_deterministic(noise):
    prep, res = noise
    from edgelab.models import oof_mean, run_walkforward
    again = oof_mean(run_walkforward(prep.ds, CFG, perm_run=3, keep_rules=False))
    for k, v in again.items():
        assert np.array_equal(res["null"][k][3], v, equal_nan=True)


def test_report_files(planted, tmp_path):
    prep, res = planted
    s = write_report(prep, res, tmp_path, CFG, manifest={"files": [{"file": "x.csv.gz", "sha256": "ab" * 32}]},
                     tests_summary="synthetic")
    md = (tmp_path / "report.md").read_text()
    js = json.loads((tmp_path / "report.json").read_text())
    assert "F1_PASS" in md and js["verdict"] == "F1_PASS" and js["n_configurations"] == 12
    assert js["config_fingerprint"] == CFG.fingerprint()
    assert "F1 — COMPLETE" in md
    # chart snapshots: up to 20 examples per rule of every passing configuration
    assert s["charts"]
    for name, items in s["charts"].items():
        for it in items:
            assert 1 <= len(it["files"]) <= CFG.examples_per_rule
            for f in it["files"]:
                svg = (tmp_path / f).read_text()
                assert svg.startswith("<svg") and "</svg>" in svg
    ledger = (tmp_path / "trials_ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 1 and json.loads(ledger[0])["verdict"] == "F1_PASS"
