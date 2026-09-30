# Edge Discovery Lab — Run Card

---

## F2 Step B — export 2023–2024 (Cowork on the owner's machine)

Roadmap Section 11. The pre-registration is already committed. **Never export 2025 or later.**
Data folder below = `%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075`.

1. GitHub Desktop: *Fetch origin → Pull*.
2. Copy `MQL5\Scripts\EdgeLab\EL_ExportM1.mq5` (v2.00, F2) over the old copy in `<data folder>\MQL5\Scripts\EdgeLab\`.
3. Compile it with the same MetaEditor command as in F1 Step B below (must show **0 errors, 0 warnings**).
4. Keep *Max bars in chart = Unlimited* and Algo Trading on.
5. Run the script with its defaults: XAUUSD, 2023 → 2024, folder `EdgeLab\data\f2`.
   - The Experts log must end with `EL_ExportM1 DONE: <rows> rows in 2 files`. The script refuses any year outside 2023–2024 and never writes a bar dated 2025-01-01 or later.
6. Copy `xauusd_m1_2023.csv.gz`, `xauusd_m1_2024.csv.gz` and `manifest.json` from `<data folder>\MQL5\Files\EdgeLab\data\f2\` into the repo folder `data\f2\`. Do **not** touch `data\` (F1).
7. Run `%LOCALAPPDATA%\Programs\Python\Python312-arm64\python.exe python\tools\verify_export.py data\f2`. It must print `phase F2` and `EXPORT OK`.
8. Commit only `data/f2/*` → push to `main`. Say **"F2 Step B done"**.

Do not open, plot or summarise the 2023–2024 data. F2 is a one-shot test, and the first look happens in F2 Step C.

---

# Phase F1 (complete)

Companion to `EdgeLab_Roadmap.md` Section 7. Step A (code) is done; this card is for Step B (export,
owner's machine / Cowork) and Step C (analysis, cloud session).

---

## Step B — export (Cowork on the owner's machine)

Data folder below = `%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075`.

1. GitHub Desktop: *Fetch origin → Pull*.
2. Copy `MQL5\Scripts\EdgeLab\EL_ExportM1.mq5` from the repo to `<data folder>\MQL5\Scripts\EdgeLab\`.
3. Compile (must show **0 errors, 0 warnings**):
   ```
   "C:\Program Files\MetaTrader 5\MetaEditor64.exe" /compile:"<data folder>\MQL5\Scripts\EdgeLab\EL_ExportM1.mq5" /log:"<data folder>\MQL5\Scripts\EdgeLab\EL_ExportM1.log" /inc:"<data folder>\MQL5"
   ```
4. In the terminal: *Tools → Options → Charts → Max bars in chart = Unlimited* (date-range `CopyRates`
   can otherwise be capped). Algo Trading on.
5. Run the script with its defaults (XAUUSD, 2020-07-01 → 2022-12-31, folder `EdgeLab\data`):
   either drag it onto any chart, or copy `config\el_export.ini` into `<data folder>\config\` and start
   `terminal64.exe /config:"<data folder>\config\el_export.ini"`.
   - The script **refuses** any year outside 2020–2022, skips every bar before 2020-07-01 and never writes a bar dated 2023-01-01 or later.
   - Experts log must end with `EL_ExportM1 DONE: <rows> rows in 3 files`. Any `ERROR` means nothing
     usable was written — fix and rerun (a rerun is not a trial; no analysis has happened yet).
6. Output in `<data folder>\MQL5\Files\EdgeLab\data\`: `xauusd_m1_2020.csv.gz` (from 2020-07-01) … `xauusd_m1_2022.csv.gz`
   and `manifest.json`. Copy these 4 files into the repo folder `data\`.
7. Verify with the laptop Python (standard library only):
   ```
   %LOCALAPPDATA%\Programs\Python\Python312-arm64\python.exe python\tools\verify_export.py data
   ```
   It must print `EXPORT OK` (checks SHA-256, gzip CRC, header, row counts, first/last bar, every bar
   inside its year and not before 2020-07-01, increasing times, OHLC/spread sanity, and that no 2023+ file exists).
8. Commit only `data/*.csv.gz` + `data/manifest.json` → push to `main`. Say **"Step B done"**.

---

## Step C — analysis (cloud session)

```
cd python
pip install -r requirements.txt
python -m pytest -q                       # all blocking tests (roadmap Section 8) must pass
python -m edgelab.report --data ../data --out ../research/f1 --jobs 4 \
       --tests-summary "<N passed in Xs>" --files-changed "<list>"
```

- Runtime estimate: ~23 s per walk-forward pass at full size (≈250k decision moments); 1 real +
  200 permutation passes ≈ 20–30 min on 4 cores, < 1 GB RAM per process.
- Writes `data/audit_2020_2022.json`, `research/f1/report.md`, `research/f1/report.json`,
  `research/f1/charts/<config>/*.svg` (only for passing configurations) and appends one line to
  `research/f1/trials_ledger.jsonl`. **Every run of the report is a counted trial**; a rerun with
  any change must stay in the ledger.
- `report.md` ends with the completion record (roadmap Section 9). Commit, push, say
  **"Step C done"** with a short Persian summary.

---

## Pre-registered details (frozen in Step A, before any data exists)

The roadmap left these open. They are fixed here, in `python/edgelab/config.py` (fingerprinted in
every report), and in the module docstrings. Changing any of them after results is a new counted trial.

**Time and data**
1. Broker time. A bar is labelled by its open time; an M1 bar closes at open + 1 min. A decision moment
   t is the close of a clock-aligned M5 bar. "Completed at or before t" = M1 close ≤ t.
2. Trading day = calendar date of the bar. A day's session = its first to last bar. A gap = the number
   of missing M1 bars between two bars of the day; > 5 is reported, > 30 quarantines the day.
3. Weekend bars are reported by the audit and not used. Duplicate timestamps: first kept, count reported.
   Zero/negative spreads are reported, not changed.

**Window and targets**
4. ResumeTime uses the previous trading day's bars with open time in [10:00, 21:30). A spread equal to
   1.5 × median counts as normal. The first day of the data has no reference → 16:30.
5. Decision moments: M5 closes with ResumeTime ≤ t < 21:30 on non-quarantined weekdays.
6. Horizon H is valid when t + H ≤ 21:30 and the day still has a bar closing at or after t + H.
   The exit price is the last M1 close ≤ t + H, so a missing exit bar uses the previous close.
   EOD = the last M1 close ≤ 21:30, valid when it is after t.
7. Commission = 2 × 0.000016 × Bid_close(t) per ounce. Spreads: the long pays spread(t), the short
   pays spread at the exit bar.
8. ATR60 = Wilder ATR(14) on the continuous M5 series (first value = mean of 14 TRs), taken at the
   bar closing at t.

**Features** (full definitions in `python/edgelab/features.py`; 25 features)
9. `r_day` is in percent (100·ln(C/day open)), so it is not an exact copy of `d_open`, which is in
   ATR units.
10. The Asian range covers bars closing in [ResumeTime, min(08:00, t)]. If ResumeTime ≥ 08:00, it
    starts at the session start instead.
11. "20-day" statistics use the previous 20 trading days at the same time of day (a day's value is
    its latest M5 value at or before that clock time) and need ≥ 10 valid days. The ATR uses the mean;
    realized vol and tick volume use the median. `spread_rel` uses the median over all M1 bars of the
    previous 20 days. `pd_ret` uses the daily Wilder ATR(14); `pd_range_rel` uses the median daily
    range of the previous 20 days.
12. `consec` is signed and resets on a flat close. `bars_since_high/low` count from the latest M5 bar
    at the extreme. `overlap12` = Σ ranges / (max high − min low) of the last 12 M5 bars.
13. Warm-up: a moment with any missing feature is not in the dataset (about the first 15 trading
    days from 2020-07-01).

**Models** (`python/edgelab/models.py`)
14. Unit of activation, fitting and verdict: **net USD/oz**. ATR units are reported next to it.
15. Bins are quantiles of the train rows of that horizon. A feature with ≤ q distinct values gets one
    bin per value. Bin = [edge₋, edge₊).
16. Activation bootstrap (M1/M2): 1,000 day-block reps, one-sided lower 5% quantile > 0, seeds derived
    from 20260930. M1 bins have no minimum size. M2 cells need ≥ 200 moments on ≥ 50 days.
17. M3: scikit-learn `DecisionTreeRegressor(max_depth=3, min_samples_leaf=500, random_state=0)` on the
    net long result. A leaf trades long if its train mean net long > 0, else short if its mean net
    short > 0.
18. Family trading rule: a moment trades long if some active rule says long and none says short (and
    the mirror for short). A conflict means no trade. At most one trade per moment, family and horizon.
19. Embargo: train moments on the last calendar day before the test year (Dec 31) are dropped.
    Folds (data range update 2026-09-30, before any analysis): train 2020-07..2020-12 → test 2021;
    train 2020-07..2021-12 → test 2022. Out-of-fold years: 2021 and 2022.

**Baselines and statistics** (`models.py`, `stats.py`, `report.py`)
20. B1 permutation: per fold, the train-year days are permuted. Each train day receives another train
    day's targets slot by slot, keeping time of day; slots missing on the source day drop out. All
    horizons share one permutation. Test-year targets are never touched. Run k uses seed
    [20260930, 1, k, fold].
21. Null statistic: the mean net USD per out-of-fold trade, with a run that makes no trade scored 0.
    p = share of the 200 runs with a mean ≥ the real one (literally as in the roadmap, no +1).
    **Consequence:** with 12 configurations Holm needs the smallest p < 0.05/12 ≈ 0.0042. Since
    1/200 = 0.005, the best configuration must beat **all 200** shuffled runs.
    **Known limitation (seen on synthetic noise):** when most shuffled runs make no trade at all, a
    real rule with a lucky positive mean gets a tiny raw p. That can produce `F1_WEAK` on pure noise.
    `F1_PASS` stays protected by the bootstrap bound and the each-year condition. The report shows
    "null runs trading" per configuration so a WEAK result can be read with this in mind.
22. Final bootstrap: 10,000 reps, seed 20260930, whole trade days as blocks, one-sided lower 5%
    quantile.
23. "Mean net > 0 in each out-of-fold year" also requires at least one trade in each year.
24. B0 (always long / always short) is reported as the cost floor and does not enter the verdict.
25. Charts: SVG (no plotting library needed), M5 ±4 h, entry and exit marked. For each passing
    configuration, up to 25 rules (most trades first) × 20 random examples.

**Synthetic tests** (`python/tests/`)
- The planted edge uses +0.6 ATR over 60 min after |r60| > 2 ATR. The 0.3 ATR in the roadmap's
  example is about the synthetic cost (≈ 0.27 ATR), so it is not an edge net of cost. The pattern is
  symmetric so it adds no unconditional drift.
- The synthetic data covers the F1 range (2020-07-01 → 2022, up to 120 weekdays per year).
- B0 on the random walk: always long + always short together must lose the round-trip cost at every
  horizon (one side alone can be positive by chance when the random path drifts).
- The random walk uses the same XAUUSD-like costs. Both end-to-end tests run the full pipeline with
  20 permutation runs instead of 200.
