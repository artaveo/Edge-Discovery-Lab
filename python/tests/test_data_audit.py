"""Data loading, the 2020-07-01..2022 guard, the manifest check and the audit (roadmap Sections 0.3, 1)."""
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


def _write_export(tmp_path, frames: dict, phase=None):
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
    if phase:
        man["phase"] = phase
    (tmp_path / "manifest.json").write_text(json.dumps(man))
    return tmp_path


@pytest.fixture()
def export(tmp_path):
    df = make_m1(years=(2020, 2021, 2022), days_per_year=3, seed=2)
    frames = {y: df[df["time"].dt.year == y].reset_index(drop=True) for y in (2020, 2021, 2022)}
    return _write_export(tmp_path, frames), df


def test_load_roundtrip_and_manifest(export):
    data_dir, df = export
    got, spec, man = load_f1(data_dir)
    assert len(got) == len(df) and spec.point == 0.01 and spec.digits == 2
    assert np.allclose(got["close"], df["close"].round(2))
    assert (got["time"].to_numpy() == df["time"].to_numpy()).all()
    assert verify_manifest(data_dir, (2020, 2021, 2022)) == []
    assert got["time"].min() >= pd.Timestamp("2020-07-01")
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
        check_years_allowed([2019])
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
    ok = flat_day("2021-01-11")
    small_gap = flat_day("2021-01-12")
    small_gap = small_gap[~small_gap["time"].between("2021-01-12 10:00", "2021-01-12 10:09")]   # 10 missing
    big_gap = flat_day("2021-01-13")
    big_gap = big_gap[~big_gap["time"].between("2021-01-13 13:00", "2021-01-13 13:30")]       # 31 missing
    edge_gap = flat_day("2021-01-14")
    edge_gap = edge_gap[~edge_gap["time"].between("2021-01-14 13:00", "2021-01-14 13:29")]    # 30 missing
    dup = flat_day("2021-01-15")
    dup = pd.concat([dup, dup.iloc[[100, 101]]], ignore_index=True)
    dup.loc[5, "spread_pts"] = 0
    dup.loc[6, "spread_pts"] = -3
    sat = flat_day("2021-01-16", start="10:00", end="10:30")
    rep = audit_m1(pd.concat([ok, small_gap, big_gap, edge_gap, dup, sat], ignore_index=True), DEFAULT)
    days = {r["date"]: r for r in rep["days"]}
    assert days["2021-01-11"]["gaps_gt5"] == [] and not days["2021-01-11"]["quarantined"]
    assert days["2021-01-12"]["gaps_gt5"] == [{"after": "09:59", "missing_min": 10}]
    assert not days["2021-01-12"]["quarantined"]
    assert days["2021-01-13"]["quarantined"] and days["2021-01-13"]["max_gap_min"] == 31
    assert not days["2021-01-14"]["quarantined"] and days["2021-01-14"]["max_gap_min"] == 30
    assert days["2021-01-15"]["duplicate_timestamps"] == 4 and rep["duplicate_timestamps_dropped"] == 2
    assert days["2021-01-15"]["zero_spread_bars"] == 1 and days["2021-01-15"]["negative_spread_bars"] == 1
    assert days["2021-01-16"]["weekend"] and not days["2021-01-16"]["quarantined"]
    assert rep["quarantined_dates"] == ["2021-01-13"]
    assert len(rep["excluded_days"]) == 2                  # the quarantined day and Saturday
    assert days["2021-01-12"]["bars"] == 1376 - 10          # 01:00..23:55 = 1376 bars
    assert rep["per_year"]["2021"]["quarantined"] == 1


def test_bars_before_2020_07_01_are_refused(tmp_path):
    early = flat_day("2020-06-30", start="01:00", end="01:09")
    frames = {2020: pd.concat([early, flat_day("2020-07-01", start="01:00", end="01:09")], ignore_index=True)}
    _write_export(tmp_path, frames)
    with pytest.raises(DataDisciplineError):
        load_f1(tmp_path, years=(2020,), verify=False)
    assert verify_export.verify(tmp_path)


# ----------------------------------------------------------------------------- F2 export check

def _f2_export(root):
    d = root / "data" / "f2"
    d.mkdir(parents=True)
    df = make_m1(years=(2023, 2024), days_per_year=3, seed=4)
    frames = {y: df[df["time"].dt.year == y].reset_index(drop=True) for y in (2023, 2024)}
    return _write_export(d, frames, phase="F2")


def test_f2_export_verifies(tmp_path):
    d = _f2_export(tmp_path)
    assert verify_export.verify(d) == []


def test_f2_refuses_2025_and_wrong_phase(tmp_path):
    d = _f2_export(tmp_path)
    # a 2025 file anywhere under data/ is refused
    (tmp_path / "data" / "xauusd_m1_2025.csv.gz").write_bytes(b"")
    assert any("FORBIDDEN" in e and "2025" in e for e in verify_export.verify(d))
    (tmp_path / "data" / "xauusd_m1_2025.csv.gz").unlink()
    # a 2025 bar hidden in the 2024 file is refused
    d2 = tmp_path / "x" / "f2"
    d2.mkdir(parents=True)
    frames = {2024: pd.concat([flat_day("2024-12-31", start="01:00", end="01:09"),
                               flat_day("2025-01-02", start="01:00", end="01:09")], ignore_index=True)}
    _write_export(d2, frames, phase="F2")
    assert any("outside 2024" in e for e in verify_export.verify(d2))
    # F1 years in an F2 folder, or an F2 manifest outside f2/, are refused
    d3 = tmp_path / "y" / "f2"
    d3.mkdir(parents=True)
    _write_export(d3, {2022: flat_day("2022-12-30", start="01:00", end="01:09")}, phase="F2")
    assert verify_export.verify(d3)
    d4 = tmp_path / "z"
    d4.mkdir()
    _write_export(d4, {2023: flat_day("2023-01-03", start="01:00", end="01:09")}, phase="F2")
    assert any("phase" in e for e in verify_export.verify(d4))


def test_f1_loader_still_refuses_f2_years(tmp_path):
    d = _f2_export(tmp_path)
    with pytest.raises(DataDisciplineError):
        load_f1(d, years=(2023, 2024))
