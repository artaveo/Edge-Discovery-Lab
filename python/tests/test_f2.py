"""F2 one-shot evaluation (roadmap Section 11.5, Step C): written and run on synthetic data
before any 2023-2024 data is loaded.

* planted H2 edge (after a "medium" previous-day range the day drifts up, after a "large"
  one it drifts down, by the pre-registered thresholds) -> F2_PASS with H2 passing;
* random walk with the same XAUUSD-like costs -> F2_FAIL;
* the frozen-file SHA-256 check, the 2025 guard, the manifest phase check, the one-shot guard,
  and the pass-rule logic on small hand-made pools.
"""
import json
import shutil

import numpy as np
import pandas as pd
import pytest

from edgelab import f2
from edgelab.data import DataDisciplineError, InstrumentSpec
from synth import flat_day
from test_data_audit import _write_export

LO, HI = json.loads((f2.PREREG / "h2_range_rule.json").read_text())["thresholds"].values()


def make_days(planted: bool, drift_usd=4.0, seed=7, years=(2022, 2023, 2024), session=(60, 23 * 60),
              sigma=0.25, vol_sd=0.35, spread_pts=25, open_spread_pts=80, open_wide_min=7):
    """M1 bars day by day. Each day has its own volatility, so daily ranges vary. With
    ``planted`` the whole day drifts +drift_usd when the previous-day range ratio (as in
    features.pd_range_rel: previous range / median of the 20 ranges before today) is
    "medium" and -drift_usd when it is "large"."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(f"{years[0]}-01-01", f"{years[-1]}-12-31")
    s0, s1 = session
    n = s1 - s0
    price, ranges, frames = 1800.0, [], []
    for d in days:
        sig = sigma * np.exp(rng.normal(0.0, vol_sd))
        drift = 0.0
        if planted and len(ranges) >= 10:
            ratio = ranges[-1] / np.median(ranges[-20:])
            if LO < ratio <= HI:
                drift = drift_usd / n
            elif ratio > HI:
                drift = -drift_usd / n
        steps = rng.normal(drift, sig, size=n)
        close = price + np.cumsum(steps)
        opn = np.r_[price, close[:-1]]
        wick = np.abs(rng.normal(0.0, 0.35 * sig, size=(n, 2)))
        high = np.maximum(opn, close) + wick[:, 0]
        low = np.minimum(opn, close) - wick[:, 1]
        sp = spread_pts + rng.integers(0, 4, size=n)
        sp[:open_wide_min] = open_spread_pts
        frames.append(pd.DataFrame({
            "time": d + pd.to_timedelta(s0 + np.arange(n), unit="min"),
            "open": np.round(opn, 2), "high": np.round(high, 2), "low": np.round(low, 2),
            "close": np.round(close, 2), "tick_volume": rng.poisson(60, size=n) + 1, "spread_pts": sp}))
        ranges.append(high.max() - low.min())
        price = close[-1]
    df = pd.concat(frames, ignore_index=True)
    df["high"] = df[["open", "high", "low", "close"]].max(axis=1)
    df["low"] = df[["open", "high", "low", "close"]].min(axis=1)
    return df


def _table(res):
    return "\n".join(f"{r['hypothesis']}: n={r['trades']} mean={r['mean_usd']:.3f} low={r['boot_lower_usd']:.3f} "
                     f"p={r['p_boot']:.4f} holm={r['p_holm']:.4f} checks={r['checks']}" for r in res["results"])


@pytest.fixture(scope="module")
def planted():
    return f2.run(make_days(planted=True), InstrumentSpec())


@pytest.fixture(scope="module")
def noise():
    return f2.run(make_days(planted=False), InstrumentSpec())


def test_planted_h2_edge_reaches_pass(planted):
    assert planted["verdict"] == "F2_PASS", _table(planted)
    h2 = planted["results"][1]
    assert h2["hypothesis"] == "H2" and h2["passes"], _table(planted)
    # one trade per day, only on medium (long) / large (short) days, none on small days
    pool = planted["pools"]["H2"]
    tr = pool["dir"] != 0
    assert len(np.unique(pool["day"][tr])) == tr.sum()
    assert 0.1 < h2["per_year"]["2023"]["long_share"] < 0.6
    assert (pool["dir"] == 0).sum() > 0


def test_random_walk_reaches_fail(noise):
    assert noise["verdict"] == "F2_FAIL", _table(noise)
    assert not any(r["passes"] for r in noise["results"])


def test_only_2023_2024_are_scored_and_h1_trades_every_eligible_moment(noise):
    for name in ("H1", "H2"):
        yrs = set(pd.DatetimeIndex(pd.to_datetime(noise["pools"][name]["t"], unit="m")).year)
        assert yrs == {2023, 2024}
    h1 = noise["pools"]["H1"]
    assert (h1["dir"] != 0).all()                     # the tree's leaves cover every moment
    b = noise["results"][0]["per_year"]["2023"]
    # always long + always short lose the round-trip cost
    assert b["b0_long_usd"] + b["b0_short_usd"] < 0


def test_report_files_and_charts(planted, tmp_path):
    s = f2.write_report(planted, tmp_path, {"files": [{"file": "x.csv.gz", "sha256": "ab" * 32}]},
                        tests_summary="synthetic")
    md = (tmp_path / "report.md").read_text()
    assert "F2_PASS" in md and "F2 — COMPLETE" in md
    assert json.loads((tmp_path / "report.json").read_text())["verdict"] == "F2_PASS"
    for name in ("H1", "H2"):
        assert len(s["charts"][name]) == f2.N_EXAMPLES
        for it in s["charts"][name]:
            svg = (tmp_path / it["file"]).read_text()
            assert svg.startswith("<svg") and "</svg>" in svg
    assert len((tmp_path / "trials_ledger.jsonl").read_text().strip().splitlines()) == 1


def test_one_shot_guard(tmp_path):
    (tmp_path / "report.json").write_text("{}")
    assert f2.main(["--out", str(tmp_path), "--f1-data", str(tmp_path), "--f2-data", str(tmp_path)]) == 2


def test_frozen_files_are_checked(tmp_path):
    f2.check_prereg()
    d = tmp_path / "prereg"
    shutil.copytree(f2.PREREG, d)
    j = json.loads((d / "h2_range_rule.json").read_text())
    j["thresholds"]["medium_max"] = 0.9
    (d / "h2_range_rule.json").write_text(json.dumps(j))
    with pytest.raises(RuntimeError):
        f2.check_prereg(d)
    rules, cuts = f2.load_hypotheses()
    assert len(rules) == 7 and cuts == (LO, HI)


def _dirs(tmp_path, f2_frames, phase="F2"):
    f1 = tmp_path / "data"
    f1.mkdir()
    _write_export(f1, {2022: flat_day("2022-12-30", start="01:00", end="01:09")})
    d2 = f1 / "f2"
    d2.mkdir()
    _write_export(d2, f2_frames, phase=phase)
    return f1, d2


def _ok_frames():
    return {2023: flat_day("2023-01-03", start="01:00", end="01:09"),
            2024: flat_day("2024-01-02", start="01:00", end="01:09")}


def test_load_f2_reads_2022_history_and_f2(tmp_path):
    f1, d2 = _dirs(tmp_path, _ok_frames())
    df, spec, man = f2.load_f2(f1, d2)
    assert sorted(set(pd.DatetimeIndex(df["time"]).year)) == [2022, 2023, 2024] and len(df) == 30


def test_load_f2_refuses_2025(tmp_path):
    fr = _ok_frames()
    fr[2024] = pd.concat([fr[2024], flat_day("2025-01-02", start="01:00", end="01:09")], ignore_index=True)
    f1, d2 = _dirs(tmp_path, fr)
    with pytest.raises(DataDisciplineError):
        f2.load_f2(f1, d2)


def test_load_f2_refuses_a_2025_file_and_a_missing_phase(tmp_path):
    f1, d2 = _dirs(tmp_path, _ok_frames())
    (f1 / "xauusd_m1_2025.csv.gz").write_bytes(b"")
    with pytest.raises(DataDisciplineError):
        f2.load_f2(f1, d2)
    t2 = tmp_path / "b"
    t2.mkdir()
    f1b, d2b = _dirs(t2, _ok_frames(), phase=None)
    with pytest.raises(DataDisciplineError):
        f2.load_f2(f1b, d2b)


def _pool(dirs, longs, shorts, days):
    n = len(dirs)
    day0 = int((pd.Timestamp("2023-03-01") - pd.Timestamp("1970-01-01")).days)
    day = np.array([day0 + d if d < 1000 else day0 + 365 + (d - 1000) for d in days])
    return {"day": day, "t": day * 1440 + 600, "dir": np.array(dirs), "exit_t": day * 1440 + 1290,
            "long": np.array(longs, float), "short": np.array(shorts, float),
            "long_atr": np.array(longs, float), "short_atr": np.array(shorts, float)}


def test_pass_rule_logic():
    rng = np.random.default_rng(0)
    n = 200
    days = list(range(n // 2)) + list(range(1000, 1000 + n // 2))     # half 2023, half 2024
    mv = rng.normal(0, 1, n)
    good_dir = np.where(mv > 0, 1, -1)                                 # a perfect oracle
    longs, shorts = mv - 0.1, -mv - 0.1
    good = f2.evaluate(_pool(good_dir, longs, shorts, days), "H1")
    assert all(good["checks"].values())
    # "always long" can never beat B0 always long (not strictly greater)
    al = f2.evaluate(_pool(np.ones(n, int), longs + 1, shorts - 1, days), "H2")
    assert al["checks"]["positive_each_year"] and not al["checks"]["beats_b0_each_year"]
    assert f2.verdict([good, al]) == "F2_PASS" and good["passes"] and not al["passes"]
    # no trades in one year -> fails rule 1
    d = good_dir.copy()
    d[n // 2:] = 0
    one = f2.evaluate(_pool(d, longs, shorts, days), "H1")
    assert not one["checks"]["positive_each_year"]
    # Holm over two: p 0.03 alone would pass unadjusted, but with the other at 0.04 both fail
    a = {"p_boot": 0.03, "checks": {"x": True}}
    b = {"p_boot": 0.04, "checks": {"x": True}}
    assert f2.verdict([a, b]) == "F2_FAIL" and a["p_holm"] == pytest.approx(0.06)
    c = {"p_boot": 0.02, "checks": {"x": True}}
    assert f2.verdict([c, b]) == "F2_PASS" and c["passes"] and b["passes"]
