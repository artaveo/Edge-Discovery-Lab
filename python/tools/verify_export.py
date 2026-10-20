"""Verify an export (F1 or F2 Step B) with the Python standard library only.

Runs on the owner's laptop (no numpy/pandas needed)::

    python python/tools/verify_export.py data        # F1: 2020-07-01 .. 2022
    python python/tools/verify_export.py data/f2     # F2: 2023 .. 2024 (never 2025+)

The phase is F2 when the folder is named ``f2`` or the manifest says ``"phase": "F2"``
(both must agree), otherwise F1.

Checks, for every file in the manifest:
  * only the phase's years are listed and present (F1: 2020-2022 from 2020-07-01;
    F2: 2023-2024); no file of a forbidden year exists (for F2: no 2025+ file anywhere under data/);
  * SHA-256 of the .gz matches the manifest; the gzip stream decompresses (CRC ok);
  * the header is time,open,high,low,close,tick_volume,spread_pts;
  * row count, first and last bar match the manifest;
  * every bar lies inside its file's year, times strictly increase, high >= max(open, close),
    low <= min(open, close), spread_pts >= 0.
Exit code 0 = OK, 1 = problems found.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
import sys
import zlib
from pathlib import Path

PHASES = {
    # owner decision 2026-09-30: full FundedNext M1 history starts mid-June 2020
    "F1": {"years": {2020, 2021, 2022}, "start": "2020-07-01"},
    # roadmap Section 11.1: F2 = 2023-2024 only; 2025 is the locked final test
    "F2": {"years": {2023, 2024}, "start": "2023-01-01"},
}
ALLOWED = PHASES["F1"]["years"]
F1_START = PHASES["F1"]["start"]
HEADER = ["time", "open", "high", "low", "close", "tick_volume", "spread_pts"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_file(path: Path, entry: dict, start: str = F1_START) -> list[str]:
    errs = []
    year = int(entry["year"])
    if sha256(path).lower() != str(entry["sha256"]).lower():
        errs.append(f"{path.name}: SHA-256 differs from manifest")
    try:
        with gzip.open(path, "rb") as g:
            text = io.TextIOWrapper(g, encoding="utf-8", newline="")
            rd = csv.reader(text)
            header = next(rd)
            if header != HEADER:
                errs.append(f"{path.name}: header {header}")
            rows = 0
            prev = None
            first = last = None
            for rec in rd:
                rows += 1
                t = rec[0]
                if first is None:
                    first = t
                last = t
                if not t.startswith(f"{year}-"):
                    errs.append(f"{path.name}: row {rows} time {t} outside {year}")
                    break
                if t < start:
                    errs.append(f"{path.name}: row {rows} time {t} before the phase start {start}")
                    break
                if prev is not None and t <= prev:
                    errs.append(f"{path.name}: row {rows} time {t} not after {prev}")
                    break
                prev = t
                try:
                    o, h, l, c = (float(x) for x in rec[1:5])
                    int(rec[5])
                    sp = int(rec[6])
                except (ValueError, IndexError):
                    errs.append(f"{path.name}: row {rows} malformed {rec}")
                    break
                if h < max(o, c) or l > min(o, c) or sp < 0:
                    errs.append(f"{path.name}: row {rows} inconsistent OHLC/spread {rec}")
                    break
    except (OSError, EOFError, zlib.error, csv.Error, UnicodeDecodeError) as e:
        return errs + [f"{path.name}: gzip/csv error {e}"]
    if rows != int(entry["rows"]):
        errs.append(f"{path.name}: {rows} rows, manifest says {entry['rows']}")
    if first != entry.get("first_bar") or last != entry.get("last_bar"):
        errs.append(f"{path.name}: first/last {first}/{last} vs manifest {entry.get('first_bar')}/{entry.get('last_bar')}")
    print(f"  {path.name}: {rows} rows, {first} .. {last}" + ("" if errs else "  OK"))
    return errs


def verify(data_dir: Path) -> list[str]:
    errs = []
    data_dir = Path(data_dir)
    man_path = data_dir / "manifest.json"
    if not man_path.exists():
        return [f"{man_path} missing"]
    man = json.loads(man_path.read_text(encoding="utf-8"))
    by_dir = "F2" if data_dir.name.lower() == "f2" else "F1"
    phase = str(man.get("phase", "F1")).upper()
    if phase != by_dir:
        errs.append(f"manifest phase {phase} does not match folder {data_dir.name} ({by_dir})")
    if phase not in PHASES:
        return errs + [f"unknown phase {phase}"]
    allowed, start = PHASES[phase]["years"], PHASES[phase]["start"]
    print(f"phase {phase}; manifest: {man.get('symbol')} on {man.get('server')}, build {man.get('terminal_build')}, "
          f"digits {man.get('digits')}, point {man.get('point')}, contract {man.get('contract_size')}")
    years = [int(f["year"]) for f in man.get("files", [])]
    if set(years) != allowed:
        errs.append(f"manifest years {sorted(years)} != {min(allowed)}-{max(allowed)}")
    for p in data_dir.glob("*.csv*"):
        m = re.search(r"(\d{4})\.csv", p.name)
        if m and int(m.group(1)) not in allowed:
            errs.append(f"FORBIDDEN FILE {p.name}: {phase} must not export {m.group(1)} - delete it, do not commit")
    if phase == "F2":
        # 2025 is the locked final test: no 2025+ file may exist anywhere under data/
        for p in data_dir.parent.rglob("*.csv*"):
            m = re.search(r"(\d{4})\.csv", p.name)
            if m and int(m.group(1)) >= 2025:
                errs.append(f"FORBIDDEN FILE {p}: 2025 and later are locked - delete it, do not commit")
    for entry in man.get("files", []):
        if int(entry["year"]) not in allowed:
            errs.append(f"manifest lists forbidden year {entry['year']}")
            continue
        path = data_dir / entry["file"]
        if not path.exists():
            errs.append(f"{entry['file']} missing")
            continue
        errs += check_file(path, entry, start)
    return errs


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    data_dir = Path(argv[0] if argv else "data")
    errs = verify(data_dir)
    if errs:
        print("PROBLEMS:")
        for e in errs:
            print("  - " + e)
        return 1
    print("EXPORT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
