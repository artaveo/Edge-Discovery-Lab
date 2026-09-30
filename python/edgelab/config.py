"""Pre-registered parameters of Phase F1 (EdgeLab_Roadmap.md, Sections 1-6).

Every number that decides the F1 verdict lives here. Changing any default after
results have been seen is a new, counted trial (roadmap Section 0.3); the
fingerprint of the config is written into every report and the trial ledger.

Time convention used throughout the package
-------------------------------------------
* Broker server time only, stored as integer minutes since 1970-01-01 (naive).
* An M1 bar with open time T *closes* at T + 1. A decision moment t is the
  close time of an M5 bar; "bars completed at or before t" are the M1 bars with
  close time <= t, i.e. open time <= t - 1.
* A trading day is the calendar date of the bar open time.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace

SEED = 20260930

# Data discipline (Section 0.3): F1 may only ever touch 2020-07-01 .. 2022-12-31.
# Owner decision 2026-09-30 (roadmap Update Log "Data range changed"): FundedNext has no
# real XAUUSD M1 history before mid-June 2020, so 2019 and 2020-01..06 are not used.
F1_YEARS = (2020, 2021, 2022)
F1_START_DATE = "2020-07-01"
F1_FIRST_FORBIDDEN_YEAR = 2023

MIN_PER_DAY = 1440


def hm(h: int, m: int = 0) -> int:
    """Minute of day for hh:mm."""
    return h * 60 + m


@dataclass(frozen=True)
class F1Config:
    # --- data / audit (Section 1)
    years: tuple = F1_YEARS
    start_date: str = F1_START_DATE
    gap_report_min: int = 5          # a gap = missing M1 bars between two bars of a day
    gap_quarantine_min: int = 30     # gap > this inside the day's session -> quarantined day

    # --- window (Section 2)
    window_end: int = hm(21, 30)     # decision moments and exits: t + H <= 21:30
    resume_deadline: int = hm(16, 30)
    resume_ref_start: int = hm(10, 0)   # previous day's [10:00, 21:30) median spread
    resume_ref_end: int = hm(21, 30)
    resume_spread_mult: float = 1.5
    resume_n_bars: int = 5
    asia_end: int = hm(8, 0)

    # --- targets (Section 3)
    horizons: tuple = (30, 60, 120, "EOD")
    commission_rate: float = 0.000016   # FundedNext metals, per side, x price, per ounce

    # --- features (Section 4)
    atr_period: int = 14
    hist_days: int = 20              # "20-day" reference statistics
    hist_min_days: int = 10          # fewer valid days -> NaN (moment dropped as warm-up)
    hour_buckets: tuple = (hm(0), hm(8), hm(10), hm(13), hm(16, 30), hm(18), hm(21, 30))

    # --- walk-forward (Section 5)
    # train 2020-07..2020-12 -> test 2021; train 2020-07..2021-12 -> test 2022
    folds: tuple = (((2020,), 2021), ((2020, 2021), 2022))
    embargo_days: int = 1
    m1_bins: int = 10
    m2_bins: int = 5
    m2_min_moments: int = 200
    m2_min_days: int = 50
    m3_max_depth: int = 3
    m3_min_leaf: int = 500
    activation_boot: int = 1000      # day-block bootstrap reps for bin/cell activation
    activation_alpha: float = 0.05   # one-sided lower 95% bound
    n_perm: int = 200                # B1 permutation runs

    # --- statistics (Section 6)
    final_boot: int = 10000
    alpha: float = 0.05
    seed: int = SEED
    primary_unit: str = "usd"        # verdict and activation use USD/oz; ATR units reported

    # --- report
    examples_per_rule: int = 20
    max_rules_charted: int = 25
    chart_half_window_min: int = 240

    extra: dict = field(default_factory=dict)

    def with_(self, **kw) -> "F1Config":
        return replace(self, **kw)

    def as_dict(self) -> dict:
        d = asdict(self)
        return json.loads(json.dumps(d, default=str))

    def fingerprint(self) -> str:
        blob = json.dumps(self.as_dict(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


DEFAULT = F1Config()

FAMILIES = ("M1", "M2", "M3")


def horizon_name(h) -> str:
    return "EOD" if h == "EOD" else f"H{int(h)}"
