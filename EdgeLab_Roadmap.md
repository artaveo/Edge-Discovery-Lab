# Edge Discovery Lab — Roadmap

Owner folder `E:\Trade\Edge-Discovery-Lab` · repository `Edge-Discovery-Lab` (owner publishes it from GitHub Desktop) · commits go straight to `main` (no branches, no PRs).

Status: **Phase F1 (feasibility study) is authorized.** Nothing beyond F1 is authorized. After F1 the owner decides.

---

## 0. What this project is (read first)

### 0.1 The idea (owner, 2026-09-30)

Previous projects started from a **human-defined setup** and asked the market to grade it:
- LSR — liquidity sweep reversal;
- Pro BTB — back to breakeven, v1 and v2;
- ORB — opening range breakout.

All of them came out near zero after costs on XAUUSD M5/M15. BTB-v2 also showed that a rule found by looking at a sample fails on unseen data.

This project reverses the direction. It **describes the market state numerically at many moments, records what happened next net of costs, and lets the data show where (if anywhere) the future is predictable.** No named setups are used; a pattern, if one exists, is extracted from the data.

### 0.2 The question of Phase F1

> Does XAUUSD, in 2020-07 → 2022, contain **predictability beyond cost**? Is there a rule, learned only from the past, that on later unseen years picks moments where the average move in the predicted direction exceeds the full trading cost (spread + commission)?

- If the answer is **no even inside 2020-07 → 2022**, the project stops cheaply.
- If **yes**, Phase F2 (validation on 2023–2024) may be authorized.

### 0.3 Non-negotiables (carried over from LSR/BTB)

- **Broker Server Time** is authoritative.
- **No look-ahead.** A feature at decision time t uses only bars completed at or before t.
- **Costs are real.** Long entries use Ask and exits Bid; shorts the reverse. Spread comes from the broker's own M1 spread field, and commission uses the FundedNext metals formula (Section 3.3).
- **Every configuration tried is counted** and enters the multiple-testing correction. There is no silent retry.
- **Rules are frozen before the numbers are seen.** Any change after a result is logged as a new, counted trial.
- **Data discipline:**
  - F1 **exports and uses only 2020-07-01 → 2022-12-31** (see the 2026-09-30 data update below). Later years are not exported in F1.
  - The years 2023–2024 are reserved for F2.
  - **2025** is the final locked test, never looked at by anyone for XAUUSD.
  - 2026 was already used in LSR/BTB and is "seen"; it may only be reported as an extra, never used to decide.
- **Interpretability.** Every model that can generate trades must be readable as a short list of "if … then …" rules that can be drawn on a chart. This is the owner's requirement: we must be able to check that the code does what we mean.

---

## 1. Data (Phase F1)

| Item | Value |
|---|---|
| Symbol / server | XAUUSD, FundedNext-Server 2. **Real M1 history starts mid-June 2020** (`SERIES_SERVER_FIRSTDATE` 2019-12-23, but 2019 has 134 bars and Jan–May 2020 about 500 bars a month; checked by Cowork 2026-09-30). FundedNext-Server has the same history |
| Bars | M1, Bid OHLC + `tick_volume` + `spread` (points), via `CopyRates` |
| Range exported in F1 | **2020-07-01 00:00 → 2022-12-31 23:59** (broker time); files 2020 (from 07-01), 2021, 2022 |
| Format | One CSV per year, gzip. Columns `time,open,high,low,close,tick_volume,spread_pts`. The time is ISO broker time; prices are normalized to digits. Paths: `data/xauusd_m1_<YYYY>.csv.gz` |
| Integrity | `data/manifest.json` holds per-file SHA-256, row count, first/last bar, symbol digits/point/contract size at export, server name, terminal build and export time |
| Data audit | Minutes per day, gaps > 5 min inside trade sessions, zero/negative spreads, duplicate timestamps, weekends. Report `data/audit_2020_2022.json`. A day with a gap > 30 min inside its session is **quarantined** (excluded from the sample), not repaired |

---

## 2. Decision moments

- A decision moment is the close of every **M5** bar, built from M1 inside the tradeable window.
- The tradeable window is `[ResumeTime(d), 21:30)` broker time. This reuses the BTB late-spread block and the spread-normal rule:
  - ResumeTime(d) = first M1 close after the session start at which the last 5 M1 spreads are each ≤ 1.5 × the median M1 spread of the previous day's `[10:00, 21:30)`;
  - if the rule is not met by 16:30, resume at 16:30.
- There are no decision moments in quarantined days, and none whose horizon (Section 3) would cross 21:30. The position is flat at 21:30 at the latest.

---

## 3. Targets (what happened next, net of cost)

### 3.1 Horizons

H ∈ {30, 60, 120 min} after the decision moment, plus `EOD` = exit at the last M1 close before 21:30.

### 3.2 Gross move

`move_H = Bid_close(t+H) − Bid_close(t)`, in USD per ounce.

### 3.3 Cost of one round trip

For a **long**:

```
cost = spread(t) + commission
```

- `spread(t)` = `spread_pts(t) × point`.
- The long entry pays the spread at t (Ask = Bid + spread); the exit at Bid pays nothing more.
- `commission` = FundedNext metals: 0.0016% × price × 2 (open + close), per ounce.

Net results:
- **Long net** = `move_H − cost`.
- **Short net** = `−move_H − spread(t+H) − commission`. The short exits at Ask(t+H) = Bid + spread(t+H) and enters at Bid(t).

### 3.4 Normalization

Every value is also expressed in units of `ATR60(t)`: the Wilder ATR(14) of M5 bars, i.e. roughly the last 70 minutes. Moments with different volatility are then comparable.

---

## 4. Features (the market snapshot at t)

About 30 numbers per moment, all from completed bars at or before t. Prices are scaled by ATR60(t) unless stated otherwise. **No feature is a named setup.** The list is frozen here; adding a feature later is a new counted trial.

| Group | Features |
|---|---|
| Recent returns | r5, r15, r60, r240: Bid close change over 5 / 15 / 60 / 240 min, in ATR units; r_day: change since the day's first M1 open |
| Volatility | ATR60 / ATR over the previous 20 days at the same time of day; range of the last 60 min / ATR60; realized vol of the last 30 M1 returns / its 20-day median |
| Position | (close − day low)/(day high − day low); distance to the previous day high and low, the Asian range high and low (resume → 08:00) and the day open, in ATR units (signed) |
| Structure | number of consecutive same-direction M5 closes; bars since the day's high and since the day's low; overlap ratio of the last 12 M5 bars (range compression) |
| Activity | tick_volume of the last 15 min / its 20-day median at the same time of day; spread(t) / 20-day median spread |
| Calendar | minutes since ResumeTime; hour bucket (`00–08`, `08–10`, `10–13`, `13–16:30`, `16:30–18`, `18–21:30`); weekday |
| Previous day | previous day return / its ATR; previous day range / its 20-day median |

`features.py` computes these. `test_features.py` recomputes each feature by brute force on a small synthetic series and must match. There is also a **look-ahead test**: shifting any future bar must not change any feature at t.

---

## 5. Method: walk-forward inside 2020-07 → 2022

### 5.1 Folds (expanding window, 1-day embargo)

| Fold | Train | Test (out-of-fold) |
|---|---|---|
| 1 | 2020-07 → 2020-12 | 2021 |
| 2 | 2020-07 → 2021-12 | 2022 |

Only the **out-of-fold** results (2021, 2022) count.

### 5.2 Model families (pre-registered, all counted)

1. **M1 — single-feature bins.** Each feature is cut into deciles on the train years. The target is the net result for long and short at each horizon. A bin is "active" if on the train years its mean net result (long or short) is > 0 with a day-block bootstrap lower 95% bound > 0.
2. **M2 — two-feature bins.** All feature pairs, each cut into 5 × 5 quintiles. Same activation rule, and each cell needs ≥ 200 train moments on ≥ 50 days.
3. **M3 — shallow tree.** Per horizon, a decision tree regressor on the net long result:
   - depth ≤ 3;
   - leaves need ≥ 500 train moments;
   - trade long in a leaf whose train mean net long > 0 and short where the train mean net short > 0.
   - It is readable, so it satisfies the interpretability rule.
4. **Trading rule for M1–M3.** In the test year, take a trade at every moment that falls in an active bin, cell or leaf, in its direction, with horizon H. Overlapping trades are counted independently, as in the BTB proxy studies. The rule is fixed by the train years only.

### 5.3 Baselines (the rule must beat these)

- **B0 — always long / always short** at every moment (the cost floor).
- **B1 — permutation.** Repeat the whole M1–M3 train/test pipeline 200 times, each time with the target shuffled **by whole days** inside the train years (this keeps the time-of-day structure and breaks predictability). This gives the null distribution of out-of-fold results.

---

## 6. Statistics and the F1 verdict

For each model family × horizon (3 × 4 = **12 configurations**), across the out-of-fold years:
- trades, days, mean net result (USD/oz and ATR units), win rate;
- a one-sided day-block bootstrap 95% interval (10,000 reps, seed 20260930);
- per-year values (2021, 2022);
- the permutation p-value = share of the 200 shuffled runs with a mean ≥ the real one.

Holm–Bonferroni is applied over the 12 configurations at α = 0.05.

**Verdict (pre-registered):**

| Verdict | Rule |
|---|---|
| `F1_PASS` | At least one configuration: Holm-adjusted permutation p < 0.05 **and** bootstrap lower 95% > 0 **and** mean net > 0 in **each** of the two out-of-fold years |
| `F1_WEAK` | Some configuration has a positive mean and permutation p < 0.05 before Holm, but fails the full rule |
| `F1_STOP` | Otherwise |

- `F1_PASS` → the owner may authorize F2: validation on 2023–2024 with the rules frozen from 2020-07 → 2022.
- `F1_WEAK` or `F1_STOP` → the report says so plainly, and the owner decides.

The report also shows, for any passing configuration, the **readable rules** (bins, cells or tree leaves), and 20 random example moments per rule as chart snapshots (M5, ±4 h) for the owner's visual check.

---

## 7. Phases and who does what

| Step | Who | What |
|---|---|---|
| **A — code** | Claude Code **cloud** session | `MQL5/Scripts/EdgeLab/EL_ExportM1.mq5` (the export with manifest); `python/edgelab/{data,audit,window,targets,features,models,stats,report}.py`; tests with synthetic data (Section 8); `config/el_export.ini`; `docs/EL_RunCard.md`. Python may use numpy, pandas and scikit-learn (list them in `python/requirements.txt`). Commit and push to `main`, then say **"Step A done"** |
| (owner) | owner | Fetch origin → Pull in GitHub Desktop |
| **B — export** | **Cowork** on the owner's machine | Install and compile the export script (0 errors / 0 warnings). Run it for 2020-07-01 → 2022-12-31 **only** (script defaults). Check the manifest, commit `data/*.csv.gz` + `data/manifest.json`, and push. It **must not** export 2023 or later. Say **"Step B done"** |
| (owner) | owner | Nothing to do: the cloud session pulls from GitHub |
| **C — analysis** | Claude Code **cloud** session | Install the requirements, run the tests, then the audit, targets, features, walk-forward, baselines and report. Write `research/f1/report.md` + `report.json` + chart snapshots, and the completion record. Commit and push, then say **"Step C done"** with a short Persian summary |

Steps A and C may be the same cloud session.

---

## 8. Blocking tests (Step A)

- **Window:** ResumeTime and 21:30 cut on synthetic days; no horizon crosses 21:30.
- **Targets:** hand-computed long/short net for a 4-bar example, including the spread at t and at t+H and the commission.
- **Features:**
  - brute-force equality;
  - the look-ahead test (mutate bars after t; the features at t must be unchanged);
  - the ATR scaling.
- **Folds:** the embargo; no train moment dated inside a test year.
- **Permutation:** day-block shuffle keeps each day's rows together and changes day assignment; the seed is deterministic.
- **Holm and bootstrap:** determinism and known small cases.
- **End-to-end:**
  - on a synthetic series with a **planted** edge (for example, after r60 > 2 ATR the next 60 min drift +0.3 ATR) the pipeline reaches `F1_PASS`;
  - on pure random-walk data it reaches `F1_STOP`.

  This is the proof that the machine finds real patterns and rejects noise.

---

## 9. Completion record

```
F1 — COMPLETE
Date: YYYY-MM-DD
Files changed: ...
Data: rows, days, quarantined days, manifest SHA-256
Tests: ...
Result: verdict + table of the 12 configurations
```

## 10. Operator notes (owner's machine)

Same as the ProBTB roadmap Section 10:
- MetaEditor CLI compile: `C:\Program Files\MetaTrader 5\MetaEditor64.exe /compile:"<file>" /log:"<log>" /inc:"<repo>\MQL5"`.
- MT5 data folder `%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075`.
- Script startup via `config\<name>.ini` with `[StartUp] Script=...`; the ini must sit inside the data folder.
- XAUUSD real M1 history on FundedNext starts mid-June 2020 (the local 2019.hcc is only 24 KB).
- Python on the laptop: `%LOCALAPPDATA%\Programs\Python\Python312-arm64\python.exe` (standard library only). Heavy analysis runs in the cloud session.
- The owner switches on Algo Trading after any terminal restart.

---

# Update Log

## 2026-09-30 — Roadmap created (owner decision)
- New project; no named setups. Market state → next move net of cost; patterns extracted from data.
- F1 = feasibility on XAUUSD 2019–2022 with walk-forward, permutation baseline and Holm. 2023–2024 reserved for F2; 2025 locked final; 2026 seen.

## 2026-09-30 — Step A done (cloud session)
- Code: `MQL5/Scripts/EdgeLab/EL_ExportM1.mq5` (2019–2022 only, gzip CSV + manifest with SHA-256), `config/el_export.ini`, `python/edgelab/{config,data,audit,window,targets,features,models,stats,report}.py`, `python/tools/verify_export.py` (stdlib-only check for Step B), `docs/EL_RunCard.md`.
- Blocking tests (Section 8) in `python/tests/`, all passing: window, hand-computed targets, feature brute force + look-ahead + ATR scaling, folds/embargo, day-block permutation, Holm/bootstrap, end-to-end (planted edge → `F1_PASS`, random walk → `F1_STOP`).
- Details the roadmap left open are pre-registered in `docs/EL_RunCard.md` ("Pre-registered details") before any data exists.

## 2026-09-30 — Data range changed (owner decision, before any analysis)
- Step B found that FundedNext-Server 2 has **no real XAUUSD M1 history before mid-June 2020** (2019: 134 bars; Jan–May 2020: about 500 bars a month). Nothing was exported or committed; no analysis had run, so this is not a counted trial.
- F1 range is now **2020-07-01 → 2022-12-31**. Folds: train 2020-07..12 → test 2021; train 2020-07..2021 → test 2022. The F1_PASS rule needs a positive mean in both out-of-fold years. 2023–2024 (F2), 2025 (locked) and 2026 (seen) are unchanged.
- Done in this commit (Step B can continue from where it stopped): `EL_ExportM1.mq5` (min year 2020, `EL_START_DATE` 2020-07-01, 2020 starts at month 7; compiled 0 errors / 0 warnings), `python/tools/verify_export.py` (years 2020–2022, no bar before 2020-07-01), `config/el_export.ini`, `docs/EL_RunCard.md` (Step B part).
- **Step C must first adapt the analysis code** (not changed here, because its tests need numpy/pandas): `python/edgelab/config.py` (`F1_YEARS = (2020, 2021, 2022)`, a 2020-07-01 start, the two folds above), `data.py` year guard, `report.py` (audit file name, per-year columns 2021/2022), and the tests that use 2019 dates or three out-of-fold years. All tests must pass before the analysis runs.


## 2026-09-30 — Step C done (cloud session) — verdict `F1_WEAK`
- Analysis code adapted to 2020-07-01 → 2022-12-31 **before** any run (commit `fba074e`): `config.py` (years 2020–2022, start 2020-07-01, two folds), `data.py` guard (no bar before 2020-07-01 or after 2022), `report.py` (audit file name, per-year columns 2021/2022), tests moved off 2019 dates. The B0 end-to-end check on random-walk data now asserts that long + short together lose the round-trip cost (one side alone can be positive by chance over two test years). 47 tests pass, including planted edge → `F1_PASS` and random walk → `F1_STOP`.
- `verify_export.py data` → `EXPORT OK`. Data: 884,546 M1 rows, 645 days, 4 quarantined (2020-11-27, 2021-01-18, 2021-02-15, 2021-07-05); 149,450 decision moments with complete features.
- One run, one trial (ledger `research/f1/trials_ledger.jsonl`, fingerprint `7e945e717983b088`), 200 permutation runs. No parameter was changed after the result.
- Result: **no configuration passes.** M3 H120 (+0.28 USD/oz, p = 0.000) and M3 EOD (+0.59 USD/oz, p = 0.035) are positive with a small permutation p, but the bootstrap lower bound is negative and M3 H120 loses in 2022, so the verdict is `F1_WEAK`. The permutation p compares against shuffled rules, which lose about the cost, so a small p here means "loses less than chance", not "profitable". No chart snapshots were written, because the roadmap draws them only for passing configurations.
- Files: `research/f1/{report.md,report.json,trials_ledger.jsonl}`, `data/audit_2020_2022.json`. The owner decides what comes next.
