"""Loading the exported M1 data and building the bar arrays used everywhere.

Files (roadmap Section 1): ``data/xauusd_m1_<YYYY>.csv.gz`` with columns
``time,open,high,low,close,tick_volume,spread_pts`` and ``data/manifest.json``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import F1_FIRST_FORBIDDEN_YEAR, F1_YEARS, MIN_PER_DAY

COLUMNS = ["time", "open", "high", "low", "close", "tick_volume", "spread_pts"]
_EPOCH_YEAR_DAYS = np.datetime64("1970-01-01", "D")


class DataDisciplineError(RuntimeError):
    """Raised when F1 code would touch data outside 2019-2022."""


@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str = "XAUUSD"
    digits: int = 2
    point: float = 0.01
    contract_size: float = 100.0


# ----------------------------------------------------------------------------- files

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def year_file(data_dir: Path, year: int) -> Path:
    return Path(data_dir) / f"xauusd_m1_{year}.csv.gz"


def read_manifest(data_dir: Path) -> dict:
    return json.loads((Path(data_dir) / "manifest.json").read_text(encoding="utf-8"))


def spec_from_manifest(manifest: dict) -> InstrumentSpec:
    return InstrumentSpec(
        symbol=str(manifest.get("symbol", "XAUUSD")),
        digits=int(manifest["digits"]),
        point=float(manifest["point"]),
        contract_size=float(manifest.get("contract_size", 100.0)),
    )


def check_years_allowed(years) -> None:
    bad = [y for y in years if int(y) not in F1_YEARS]
    if bad:
        raise DataDisciplineError(
            f"F1 may only use {F1_YEARS[0]}-{F1_YEARS[-1]}; refused years {bad}")


def verify_manifest(data_dir: Path, years, manifest: dict | None = None) -> list[str]:
    """Check SHA-256 and row counts against the manifest. Returns problems (empty = ok)."""
    manifest = manifest if manifest is not None else read_manifest(data_dir)
    by_year = {int(f["year"]): f for f in manifest.get("files", [])}
    problems = []
    for f in manifest.get("files", []):
        if int(f["year"]) >= F1_FIRST_FORBIDDEN_YEAR:
            problems.append(f"manifest lists forbidden year {f['year']}")
    for y in years:
        entry = by_year.get(int(y))
        path = year_file(data_dir, y)
        if entry is None:
            problems.append(f"{y}: not in manifest")
            continue
        if not path.exists():
            problems.append(f"{y}: file {path.name} missing")
            continue
        digest = sha256_file(path)
        if digest.lower() != str(entry["sha256"]).lower():
            problems.append(f"{y}: sha256 mismatch ({digest} != {entry['sha256']})")
    return problems


def read_year_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, compression="infer")
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    df = df[COLUMNS].copy()
    df["time"] = pd.to_datetime(df["time"], format="ISO8601")
    return df


def load_f1(data_dir: Path, years=F1_YEARS, verify: bool = True):
    """Load the F1 years. Returns (DataFrame, InstrumentSpec, manifest)."""
    check_years_allowed(years)
    data_dir = Path(data_dir)
    manifest = read_manifest(data_dir)
    if verify:
        problems = verify_manifest(data_dir, years, manifest)
        if problems:
            raise ValueError("manifest check failed: " + "; ".join(problems))
    frames = []
    by_year = {int(f["year"]): f for f in manifest.get("files", [])}
    for y in years:
        df = read_year_csv(year_file(data_dir, y))
        if verify and int(by_year[int(y)]["rows"]) != len(df):
            raise ValueError(f"{y}: row count {len(df)} != manifest {by_year[int(y)]['rows']}")
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    assert_no_forbidden_rows(df)
    return df, spec_from_manifest(manifest), manifest


def assert_no_forbidden_rows(df: pd.DataFrame) -> None:
    if len(df) and int(pd.DatetimeIndex(df["time"]).year.max()) >= F1_FIRST_FORBIDDEN_YEAR:
        raise DataDisciplineError("data contains bars dated 2023 or later; F1 must not see them")


# ----------------------------------------------------------------------------- bars

def to_minutes(times) -> np.ndarray:
    """datetime-like -> int64 minutes since 1970-01-01 (broker time, naive)."""
    arr = np.asarray(pd.DatetimeIndex(times).values).astype("datetime64[m]")
    return arr.astype(np.int64)


def minutes_to_datetime(m) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(np.asarray(m, dtype=np.int64).astype("datetime64[m]"))


def day_to_date(day_id: int) -> str:
    return str(_EPOCH_YEAR_DAYS + np.timedelta64(int(day_id), "D"))


def weekday_of_day(day_id) -> np.ndarray:
    """Monday = 0 ... Sunday = 6 (1970-01-01 was a Thursday)."""
    return (np.asarray(day_id) + 3) % 7


def year_of_day(day_id) -> np.ndarray:
    d = np.asarray(day_id, dtype=np.int64).astype("datetime64[D]")
    return d.astype("datetime64[Y]").astype(np.int64) + 1970


def clean_m1(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Sort by time and drop duplicate timestamps (keep first). Returns (df, n_dropped)."""
    df = df.sort_values("time", kind="mergesort")
    dup = df["time"].duplicated(keep="first")
    return df.loc[~dup].reset_index(drop=True), int(dup.sum())


@dataclass
class Bars:
    """Arrays for M1, M5 and daily bars. Built once from a clean M1 frame."""

    # M1
    t: np.ndarray            # open time, minutes
    tc: np.ndarray           # close time = t + 1
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    tv: np.ndarray
    spread_pts: np.ndarray
    day: np.ndarray          # day id of each M1 bar
    # M5 (clock aligned: key = open time floored to 5 minutes)
    k5: np.ndarray
    tc5: np.ndarray          # close time = key + 5
    o5: np.ndarray
    h5: np.ndarray
    l5: np.ndarray
    c5: np.ndarray
    tv5: np.ndarray
    first5: np.ndarray       # first M1 index inside the M5 bar
    last5: np.ndarray        # last M1 index inside the M5 bar
    day5: np.ndarray
    # days (trading days = calendar dates that have at least one bar)
    days: np.ndarray
    d_first: np.ndarray      # first M1 index of the day
    d_last: np.ndarray       # last M1 index of the day
    d_open: np.ndarray
    d_high: np.ndarray
    d_low: np.ndarray
    d_close: np.ndarray
    spec: InstrumentSpec

    @property
    def n_days(self) -> int:
        return len(self.days)

    def day_row(self, day_ids) -> np.ndarray:
        """Row index of each day id inside ``days`` (-1 when absent)."""
        day_ids = np.asarray(day_ids)
        pos = np.searchsorted(self.days, day_ids)
        pos = np.clip(pos, 0, len(self.days) - 1)
        return np.where(self.days[pos] == day_ids, pos, -1)

    def asof_index(self, tau) -> np.ndarray:
        """Index of the last M1 bar with close time <= tau (-1 if none)."""
        return np.searchsorted(self.tc, np.asarray(tau), side="right") - 1


def build_bars(df: pd.DataFrame, spec: InstrumentSpec | None = None) -> Bars:
    df, _ = clean_m1(df)
    t = to_minutes(df["time"])
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    tv = df["tick_volume"].to_numpy(float)
    sp = df["spread_pts"].to_numpy(float)
    day = t // MIN_PER_DAY

    k = t - t % 5
    starts = np.flatnonzero(np.r_[True, k[1:] != k[:-1]])
    ends = np.r_[starts[1:], len(t)] - 1
    k5 = k[starts]
    o5 = o[starts]
    h5 = np.maximum.reduceat(h, starts)
    l5 = np.minimum.reduceat(l, starts)
    c5 = c[ends]
    tv5 = np.add.reduceat(tv, starts)

    dstarts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    dends = np.r_[dstarts[1:], len(t)] - 1
    return Bars(
        t=t, tc=t + 1, o=o, h=h, l=l, c=c, tv=tv, spread_pts=sp, day=day,
        k5=k5, tc5=k5 + 5, o5=o5, h5=h5, l5=l5, c5=c5, tv5=tv5,
        first5=starts, last5=ends, day5=k5 // MIN_PER_DAY,
        days=day[dstarts], d_first=dstarts, d_last=dends,
        d_open=o[dstarts], d_high=np.maximum.reduceat(h, dstarts),
        d_low=np.minimum.reduceat(l, dstarts), d_close=c[dends],
        spec=spec or InstrumentSpec(),
    )


def wilder_atr(high, low, close, period: int) -> np.ndarray:
    """Wilder ATR over a bar series; NaN until ``period`` true ranges exist.

    TR_0 = H_0 - L_0; TR_i = max(H-L, |H-C_prev|, |L-C_prev|).
    ATR_{period-1} = mean(TR_0..TR_{period-1}); ATR_i = (ATR_{i-1}(period-1) + TR_i)/period.
    """
    high = np.asarray(high, float)
    low = np.asarray(low, float)
    close = np.asarray(close, float)
    n = len(high)
    tr = high - low
    if n > 1:
        pc = close[:-1]
        tr[1:] = np.maximum.reduce([high[1:] - low[1:], np.abs(high[1:] - pc), np.abs(low[1:] - pc)])
    atr = np.full(n, np.nan)
    if n < period:
        return atr
    a = tr[:period].mean()
    atr[period - 1] = a
    # the recursion is inherently sequential; plain Python over ~300k M5 bars is fast enough
    alpha = 1.0 / period
    trl = tr.tolist()
    out = atr.tolist()
    for i in range(period, n):
        a = a + (trl[i] - a) * alpha
        out[i] = a
    return np.asarray(out)
