"""Data loading, the 2019-2022 guard, the manifest check and the audit (roadmap Sections 0.3, 1)."""
import gzip
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

from edgelab.audit import audit_m1
from edgelab.config import DEFAULT
from edgelab.data import DataDisciplineError, check_years_allowed, load_f1, verify_manifest
from synth import flat_day, make_m1

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import verify_export  # noqa: E402


def _write_export(tmp_path, frames: dict):
    """Write frames {year: df} like EL_ExportM1 does; returns the data dir."""
    files = []
    for y, df in frames.items():
        name = f"xauusd_m1_{y}.csv.gz"
        out = df.copy()
        out["time"] = out["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        for c in ("open", "high", "low", "close"):
            out[c] = out[c].map(lambda v: f"{v:.2f}")
        raw = out.to_csv(index=False, lineterminator="\n").encode()
        path = tmp_path / name
        path.write_bytes(gzip.compress(raw, mtime=0))
        files.append({"file": name, "year": y, "rows": len(df), "first_bar": out["time"].iloc[0],
                      "last_bar": out["time"].iloc[-1],
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    man = {"schema": "edgelab.export.v1", "symbol": "XAUUSD", "server": "FundedNext-Server 2",
           "terminal_build": 1, "digits": 2, "point": 0.01, "contract_size": 100.0, "files": files}
    (tmp_path / "manifest.json").write_text(json.dumps(man))
    return tmp_path


@pytest.fixture()
def export(tmp_path):
    df = make_m1(years=(2019, 2020, 2021, 2022), days_per_year=3, seed=2)
    frames = {y: df[df["time"].dt.year == y].reset_index(drop=True) for y in (2019, 2020, 2021, 2022)}
    return _write_export(tmp_path, frames), df


def test_load_roundtrip_and_manifest(export):
    data_dir, df = export
    got, spec, man = load_f1(data_dir)
    assert len(got) == len(df) and spec.point == 0.01 and spec.digits == 2
    assert np.allclose(got["close"], df["close"].round(2))
    assert (got["time"].to_numpy() == df["time"].to_numpy()).all()
    assert verify_manifest(data_dir, (2019, 2020, 2021, 2022)) == []
    assert verify_export.verify(data_dir) == []


def test_manifest_tamper_is_detected(export):
    data_dir, _ = export
    p = data_dir / "xauusd_m1_2020.csv.gz"
    b = bytearray(p.read_bytes())
    b[-10] ^= 0xFF
    p.write_bytes(bytes(b))
    assert any("sha256" in e for e in verify_manifest(data_dir, (2020,)))
    with pytest.raises(ValueError):
        load_f1(data_dir)
    assert verify_export.verify(data_dir)


def test_years_after_2022_are_refused(export, tmp_path):
    data_dir, _ = export
    with pytest.raises(DataDisciplineError):
        check_years_allowed([2019, 2023])
    with pytest.raises(DataDisciplineError):
        load_f1(data_dir, years=(2022, 2023))
    # a file that sneaks a 2023 bar into the 2022 file is refused as well
    late = flat_day("2023-01-02", start="01:00", end="01:09")
    frames = {2022: pd.concat([flat_day("2022-12-30", start="01:00", end="01:09"), late], ignore_index=True)}
    d2 = tmp_path / "bad"
    d2.mkdir()
    _write_export(d2, frames)
    with pytest.raises(DataDisciplineError):
        load_f1(d2, years=(2022,), verify=False)
    errs = verify_export.verify(d2)
    assert any("outside 2022" in e for e in errs)
    # and a forbidden year file in the folder is reported
    (d2 / "xauusd_m1_2023.csv.gz").write_bytes(b"")
    assert any("FORBIDDEN" in e for e in verify_export.verify(d2))


def test_audit_gaps_quarantine_duplicates_spreads_weekend():
    ok = flat_day("2019-01-07")
    small_gap = flat_day("2019-01-08")
    small_gap = small_gap[~small_gap["time"].between("2019-01-08 10:00", "2019-01-08 10:09")]   # 10 missing
    big_gap = flat_day("2019-01-09")
    big_gap = big_gap[~big_gap["time"].between("2019-01-09 13:00", "2019-01-09 13:30")]       # 31 missing
    edge_gap = flat_day("2019-01-10")
    edge_gap = edge_gap[~edge_gap["time"].between("2019-01-10 13:00", "2019-01-10 13:29")]    # 30 missing
    dup = flat_day("2019-01-11")
    dup = pd.concat([dup, dup.iloc[[100, 101]]], ignore_index=True)
    dup.loc[5, "spread_pts"] = 0
    dup.loc[6, "spread_pts"] = -3
    sat = flat_day("2019-01-12", start="10:00", end="10:30")
    rep = audit_m1(pd.concat([ok, small_gap, big_gap, edge_gap, dup, sat], ignore_index=True), DEFAULT)
    days = {r["date"]: r for r in rep["days"]}
    assert days["2019-01-07"]["gaps_gt5"] == [] and not days["2019-01-07"]["quarantined"]
    assert days["2019-01-08"]["gaps_gt5"] == [{"after": "09:59", "missing_min": 10}]
    assert not days["2019-01-08"]["quarantined"]
    assert days["2019-01-09"]["quarantined"] and days["2019-01-09"]["max_gap_min"] == 31
    assert not days["2019-01-10"]["quarantined"] and days["2019-01-10"]["max_gap_min"] == 30
    assert days["2019-01-11"]["duplicate_timestamps"] == 4 and rep["duplicate_timestamps_dropped"] == 2
    assert days["2019-01-11"]["zero_spread_bars"] == 1 and days["2019-01-11"]["negative_spread_bars"] == 1
    assert days["2019-01-12"]["weekend"] and not days["2019-01-12"]["quarantined"]
    assert rep["quarantined_dates"] == ["2019-01-09"]
    assert len(rep["excluded_days"]) == 2                  # the quarantined day and Saturday
    assert days["2019-01-08"]["bars"] == 1376 - 10          # 01:00..23:55 = 1376 bars
    assert rep["per_year"]["2019"]["quarantined"] == 1
