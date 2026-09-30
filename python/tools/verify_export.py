"""Verify the F1 export (Step B) with the Python standard library only.

Runs on the owner's laptop (no numpy/pandas needed)::

    python python/tools/verify_export.py data

Checks, for every file in data/manifest.json:
  * only years 2020-2022 are listed and present (2020 starts 2020-07-01); no data/*_2023+ file exists;
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

ALLOWED = {2020, 2021, 2022}
F1_START = "2020-07-01"   # owner decision 2026-09-30: full FundedNext M1 history starts mid-June 2020
HEADER = ["time", "open", "high", "low", "close", "tick_volume", "spread_pts"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_file(path: Path, entry: dict) -> list[str]:
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
                if t < F1_START:
                    errs.append(f"{path.name}: row {rows} time {t} before the F1 start {F1_START}")
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
    man_path = data_dir / "manifest.json"
    if not man_path.exists():
        return [f"{man_path} missing"]
    man = json.loads(man_path.read_text(encoding="utf-8"))
    print(f"manifest: {man.get('symbol')} on {man.get('server')}, build {man.get('terminal_build')}, "
          f"digits {man.get('digits')}, point {man.get('point')}, contract {man.get('contract_size')}")
    years = [int(f["year"]) for f in man.get("files", [])]
    if set(years) != ALLOWED:
        errs.append(f"manifest years {sorted(years)} != 2020-2022")
    for p in data_dir.glob("*.csv*"):
        m = re.search(r"(\d{4})\.csv", p.name)
        if m and int(m.group(1)) not in ALLOWED:
            errs.append(f"FORBIDDEN FILE {p.name}: F1 must not export {m.group(1)} - delete it, do not commit")
    for entry in man.get("files", []):
        if int(entry["year"]) not in ALLOWED:
            errs.append(f"manifest lists forbidden year {entry['year']}")
            continue
        path = data_dir / entry["file"]
        if not path.exists():
            errs.append(f"{entry['file']} missing")
            continue
        errs += check_file(path, entry)
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
