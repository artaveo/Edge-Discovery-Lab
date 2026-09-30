# Edge Discovery Lab — Roadmap

Owner folder `E:\Trade\Edge-Discovery-Lab` · repository `Edge-Discovery-Lab` (owner publishes it from GitHub Desktop) · commits go straight to `main` (no branches, no PRs).

Status: F1 complete (`F1_WEAK`). **F2 complete: `F2_FAIL`** (one-shot test on 2023–2024, Section 11). Per the pre-registration the F1/F2 hypotheses are closed. 2025 stays locked. **Owner decision 2026-09-30: Lab v2 — Phase F3 (path-dependent exits) is authorized, Section 12.** Nothing beyond F3 is authorized.

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

## 11. F2 — pre-registration (one-shot test on 2023–2024)

Written and committed **before any 2023–2024 data is exported or seen** (owner decision 2026-09-30). Everything in this section is frozen. F2 is a **single shot**: the evaluation runs once. If the code crashes before any number is produced, the bug may be fixed and the run repeated. Once any F2 number exists, nothing changes, and there is no second hypothesis, threshold, horizon or model.

### 11.1 Data

- F2 exports and uses **only 2023-01-01 00:00 → 2024-12-31 23:59** (broker time), in `data/f2/`: `xauusd_m1_2023.csv.gz`, `xauusd_m1_2024.csv.gz`, `manifest.json` (same format as F1; `"phase": "F2"`).
- **2025 and later stay locked.** They are never exported or looked at. 2026 remains "seen" and is never used to decide.
- The F1 data (2020-07 → 2022) may be read **only as feature history** for the first 2023 days (previous day, 20-day medians, daily ATR, ResumeTime reference). No 2022 moment is scored.
- The audit and quarantine rules are unchanged from Section 1 (a gap > 30 min inside the session quarantines the day). The window, targets, costs and features are unchanged: the F1 code (`python/edgelab/{window,targets,features}.py` at commit `872a326`) is used as is, with the F1 config (fingerprint `7e945e717983b088`). Symbol point and digits come from the F2 manifest.

### 11.2 H1 — the second M3-EOD tree, exactly as it is

- **Model:** the M3 EOD tree of F1 fold 2, fitted by F1 on **2020-07-21 → 2021-12-30** (88,578 moments, 370 days; Dec 31 embargoed). Its out-of-fold test year in F1 was 2022. It is **not refitted** on 2022 or on anything else.
- **Files:**
  - `research/f2/prereg/h1_m3_eod_tree.json` holds the rules (authoritative) and the sklearn tree arrays. SHA-256 `9d6f7f24d250452e959a3a1a70a01f60d05ecd1461c4c5145775cab3ebdf64f3`.
  - `h1_m3_eod_tree.pkl` is the sklearn object (scikit-learn 1.9.1), kept for inspection. SHA-256 `b91630b68baac8fc9cf38dbb86a4ac4c9ecc6b5ffc5879de4045854ac109b0f9`.
  - `freeze_models.py` rebuilt them from F1 data and asserted equality with `research/f1/report.json`.
- **Trading rule:** at every decision moment with all 25 features finite and a valid EOD target, trade in the direction of the leaf the moment falls in. The leaves cover every moment. Exit is EOD (last M1 close ≤ 21:30). This is exactly the F1 rule, with overlapping moments counted independently.
- **Rules** (thresholds at full precision; `pd_ret` = previous day return / daily ATR14; `pd_range_rel` = previous day range / 20-day median; `d_asia_hi` in ATR60 units; `weekday` 0 = Monday):

| # | Rule id | If | Then | Train moments / days |
|---|---|---|---|---|
| 1 | `M3-EOD-2022-000` | `pd_ret` <= 1.1535295248031616 **and** `pd_range_rel` <= 0.6848121285438538 **and** `pd_ret` <= 0.2328488603234291 | **SHORT** | 12785 / 53 |
| 2 | `M3-EOD-2022-001` | `pd_ret` <= 1.1535295248031616 **and** `pd_range_rel` <= 0.6848121285438538 **and** 0.2328488603234291 < `pd_ret` | **SHORT** | 2649 / 11 |
| 3 | `M3-EOD-2022-002` | `pd_ret` <= 1.1535295248031616 **and** 0.6848121285438538 < `pd_range_rel` **and** `pd_range_rel` <= 0.8871178030967712 | **LONG** | 18194 / 76 |
| 4 | `M3-EOD-2022-003` | `pd_ret` <= 1.1535295248031616 **and** 0.6848121285438538 < `pd_range_rel` **and** 0.8871178030967712 < `pd_range_rel` | **SHORT** | 51854 / 217 |
| 5 | `M3-EOD-2022-004` | 1.1535295248031616 < `pd_ret` **and** `d_asia_hi` <= 0.4368121325969696 **and** `weekday` <= 1.5 | **LONG** | 831 / 4 |
| 6 | `M3-EOD-2022-005` | 1.1535295248031616 < `pd_ret` **and** `d_asia_hi` <= 0.4368121325969696 **and** 1.5 < `weekday` | **LONG** | 1322 / 9 |
| 7 | `M3-EOD-2022-006` | 1.1535295248031616 < `pd_ret` **and** 0.4368121325969696 < `d_asia_hi` | **LONG** | 943 / 11 |

### 11.3 H2 — the shared "previous-day range" rule

- Thresholds are copied exactly from the second tree. File: `research/f2/prereg/h2_range_rule.json`, SHA-256 `e266849a75741e8b286f8a7d9e02e4e39cfd0f4460667abd24c2372c60a83015`.
  - `pd_range_rel` ≤ **0.6848121285438538** → **no trade**
  - 0.6848121285438538 < `pd_range_rel` ≤ **0.8871178030967712** → **LONG** to EOD
  - `pd_range_rel` > 0.8871178030967712 → **SHORT** to EOD
- **One trade per day.** The entry is at the day's first decision moment, i.e. the first M5 close ≥ ResumeTime(d), which is at most 4 minutes after ResumeTime. The exit is EOD. Costs are as in Section 3.3.
- **Eligible day:** a non-quarantined weekday whose first decision moment has a finite `pd_range_rel` and a valid EOD target. No other condition applies (the tree's `pd_ret ≤ 1.154` branch is deliberately dropped).

### 11.4 Statistics and pass rule

For each hypothesis, over 2023 and 2024 (unit: net USD/oz per trade):

1. **Mean net > 0 in 2023 and > 0 in 2024**, each year separately, with at least one trade in each year.
2. **Bootstrap:** the one-sided day-block bootstrap lower 95% bound of the mean over 2023–2024 must be > 0 (10,000 reps, seed 20260930, whole trade days as blocks, as in F1).
3. **Beats both baselines in each year:** the hypothesis' mean > the mean of B0 "always long" **and** > the mean of B0 "always short", in 2023 and in 2024 separately.
   - H1's baselines use the same set of moments H1 trades (all eligible decision moments).
   - H2's baselines take one trade per **eligible** day (including the days H2 skips) at the same entry moment, to EOD.
4. **Holm over the 2 hypotheses** at α = 0.05. Each hypothesis' p is the one-sided day-block bootstrap p = share of the 10,000 bootstrap means ≤ 0 (the same resamples as in rule 2). Holm: the smaller p < 0.025, the larger p < 0.05.

| Verdict | Rule |
|---|---|
| `F2_PASS` | At least one hypothesis meets **all** of rules 1–4 (the report names which) |
| `F2_FAIL` | Otherwise. **The project stops** |

The report gives, per hypothesis and year: trades, days, mean net (USD/oz and ATR units), win rate, long/short share, B0 means, the bootstrap bound, the raw p and the Holm p. It also gives 10 example charts per hypothesis, chosen at random with seed [20260930, 5].

### 11.5 F2 steps

| Step | Who | What |
|---|---|---|
| **A — pre-registration** | cloud session | This section, the frozen H1/H2 files, and the export script and `verify_export.py` limited to 2023–2024 → `data/f2/`. Say **"F2 Step A done"** |
| **B — export** | Cowork | Compile `EL_ExportM1.mq5` (0 errors / 0 warnings), run it with its defaults (2023–2024, `EdgeLab\\data\\f2`), run `verify_export.py data/f2` (must print `EXPORT OK`), commit `data/f2/*` only. **Never 2025 or later.** Say **"F2 Step B done"** |
| **C — one-shot evaluation** | cloud session | First write `python/edgelab/f2.py` and its tests on synthetic data (a planted H2 edge → pass; random walk → fail; frozen-file SHA-256 check; the 2025 guard) and commit them **before** loading 2023–2024. Then run once, write `research/f2/report.md` + `report.json` + charts, commit and push, and say **"F2 Step C done"** with the verdict |

---

## 12. Lab v2 — Phase F3: path-dependent exits (owner decision 2026-09-30)

### 12.1 Why

F1 measured only **fixed-time exits**: enter at a decision moment, hold 30/60/120 min or to EOD, with no stop and no target. That only measures the average direction. Many real strategies earn from the **shape of the exit**: a small loss is cut and a large gain is allowed to run, so a 35–40% win rate can be profitable. F1 could not see this.

F3 adds exactly one thing: **stop-loss / take-profit / trailing exits**. Everything else is F1 unchanged:
- data 2020-07 → 2022 and the two folds;
- decision moments, window and ResumeTime;
- the 25 features, costs and quarantine;
- model families M1/M2/M3;
- the EOD time stop.

The owner explicitly chose **not** to change the data range: an edge worth trading must show within these years.

### 12.2 Exit grid (pre-registered, 28 exit rules)

Entry is as in F1: at the decision moment's close. A long enters at Ask = Bid + spread(t) and a short at Bid. Let `A = ATR60(t)` (Section 3.4). The stop distance is `S = s × A`.

| Family | Parameters | Count |
|---|---|---|
| **Fixed SL + TP** | s ∈ {0.5, 1.0, 1.5, 2.0}; TP at k × S from entry with k ∈ {1, 1.5, 2, 3}; else EOD | 16 |
| **Fixed SL, no TP** | s ∈ {0.5, 1.0, 1.5, 2.0}; exit at SL or EOD | 4 |
| **Trailing stop** | initial SL = s × A with s ∈ {1.0, 2.0}; after each M1 close the stop trails to (highest Bid close since entry − t × A) for a long (mirrored for a short) with t ∈ {1.0, 2.0}, never loosening; no TP; EOD time stop | 4 |
| **Breakeven + TP** | s ∈ {1.0, 2.0}, TP k ∈ {2, 3}; the stop moves to entry + cost once price has gone +1 × S | 4 |

Every exit also has the **EOD time stop** at the last M1 close ≤ 21:30.

### 12.3 Path resolution and costs (conservative)

- **Resolution.** The path is resolved on **M1 bars**:
  - long SL / trailing stop triggers when the M1 **Bid low** ≤ stop;
  - long TP triggers when the M1 **Bid high** ≥ TP;
  - short SL triggers when **Bid high + spread** (Ask) ≥ stop;
  - short TP triggers when **Bid low + spread** ≤ TP, using that bar's spread.
- **Same-bar conflict.** If SL and TP are both touched in the same M1 bar, the **SL counts** (pessimistic). The report gives the share of such bars per exit rule.
- **Fills.**
  - A stop fills at the stop price, or at the bar open if the bar opened beyond it (gap), whichever is worse.
  - A TP fills at the TP price.
  - EOD fills at the Bid close (long) or the Ask close (short).
- **Cost.** Spread at entry and the FundedNext commission (Section 3.3).
- **Units.** Results are in USD/oz **and in R** (net result / (S + entry cost)).
- **Known limitation.** M1 cannot order ticks inside a bar; the SL-first rule biases **against** us, which is acceptable. A final candidate would be re-checked tick-exactly in MT5 (TRE engine) before any live use.

### 12.4 Models and search

For each exit rule `e` and side, the target per moment is the net R of that exit. The M1 bins, M2 cells and M3 trees are learned exactly as in Section 5.2, on the net R of exit `e` instead of the time-exit result.
- 28 exit rules × 3 families = **84 configurations**, all counted.
- The Section 5.2 activation rules are unchanged: the train-year mean net > 0 and the bootstrap lower bound > 0, with the minimum counts as in F1.

**Overlap rule.** F1 counted every 5-minute moment as a separate trade, so one day produced dozens of nearly identical trades.
- F3 adds a realistic variant as the **primary** count: **one position at a time per configuration**. A signal is taken only when the previous trade of that configuration is closed.
- The F1-style "all moments" count is reported as a secondary.

### 12.5 Multiple testing: reality check on the maximum

- With 84 configurations, Holm alone is weak. The null distribution is therefore built on the **maximum**, in the spirit of White's Reality Check.
- Each of the 200 day-block permutations reruns all 84 configurations and records the **best** out-of-fold mean net R among them.
- The permutation p-value of a configuration is the share of permutations whose best is ≥ that configuration's real mean.
- The shuffle seed is `20260930`, as in F1.
- The targets for all exits are computed once; each permutation only refits the models. This keeps the run time reasonable.

### 12.6 F3 verdict (pre-registered)

| Verdict | Rule |
|---|---|
| `F3_PASS` | At least one configuration meets **all** of these on the one-position-at-a-time count:<br>• out-of-fold mean net R > 0 in **2021 and in 2022** separately;<br>• day-block bootstrap lower 95% > 0 over 2021–2022;<br>• reality-check p < 0.05;<br>• it beats **B0 with the same exit** (always long and always short with that exit rule) in each year;<br>• at least 100 trades per year |
| `F3_WEAK` | Some configuration has mean > 0 in both years and p < 0.10, but fails the full rule |
| `F3_STOP` | Otherwise |

- The report lists every configuration with its readable rules, trades per year, win rate, average win and loss in R, mean net R per year, the bootstrap bound, the p-value, the same-bar-conflict share and max drawdown in R.
- For a passing configuration it also shows 10 example charts from entry to exit.
- `F3_PASS` allows, on owner approval only, a pre-registered one-shot **F4** on 2023–2024 with the rules and exit frozen. 2023–2024 were seen in F2 only through the two H1/H2 rules, which is stated as a limitation. 2025 stays locked for the final test.

### 12.7 Steps

| Step | Who | What |
|---|---|---|
| **A — code + tests** | cloud session | Write `python/edgelab/exits.py` (the exit grid, path resolution, one-position-at-a-time), extend `models.py`/`stats.py`/`report.py` for the 84 configurations and the max-statistic permutation. Add tests (below). Commit, push and say **"F3 Step A done"**. No real-data result may be produced in Step A |
| **B — run** | cloud session | Run once on the committed F1 data (`data/*.csv.gz`, 2020-07 → 2022; **no new export is needed**). Write `research/f3/report.md` + `report.json` + the trials ledger, commit, push and say **"F3 done"** with a short Persian summary |

Required tests:
- **Hand-computed paths:**
  - long and short SL, TP, trailing and breakeven exits on small synthetic M1 series;
  - the same-bar conflict counts SL;
  - the gap fill;
  - the short triggers use Ask;
  - EOD.
- **One-position-at-a-time:** signals during an open trade are skipped.
- **Planted edge:** a synthetic series where a condition gives a +2R-then-reverse pattern (the time exit sees ~0, a TP of 2R sees profit) must reach `F3_PASS` with a TP exit and **fail** with the time exit.
- **Random walk:** the result must be `F3_STOP`.
- **Max-statistic permutation:** determinism, and the p-value bounds.

### 12.8 Backlog (owner idea, not authorized yet)

**F5 — NY-close level study.** The engine marks only the **previous New York close** as a level. When price reaches that level, it examines which entries, exits and reward ratios would have been profitable. The idea is to search for patterns **only at that event**, not at every moment. To be specified and pre-registered before any run if F3 fails and the owner authorizes it.

---

# Update Log

## 2026-09-30 — Lab v2 / F3 authorized (owner decision)
- F3 adds path-dependent exits (28 rules: SL/TP, SL only, trailing, breakeven+TP) to the F1 pipeline. Data, features, folds and models are unchanged; the owner chose not to extend data.
- Primary count: one position at a time. Multiple testing: max-statistic permutation (reality check) over 84 configurations.
- Backlog: F5 NY-close level study (owner idea).

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

## 2026-09-30 — F2 authorized; F2 Step A done (cloud session)
- Owner decision: F2 = a one-shot test of two frozen hypotheses on 2023–2024 (Section 11). 2025 stays locked.
- H1 = the second F1 M3-EOD tree exactly as fitted in F1. Its training data is **2020-07-21 → 2021-12-30**, and 2022 was its out-of-fold test year; it is not refitted on 2022. H2 = the shared previous-day range rule with the second tree's exact thresholds. Model files and their SHA-256 are in `research/f2/prereg/`.
- `EL_ExportM1.mq5` now exports only 2023–2024 to `EdgeLab\data\f2` (hard guard: nothing before 2023-01-01 or from 2025-01-01 on). `verify_export.py` checks F1 (`data/`) or F2 (`data/f2/`) by phase. `config/el_export.ini` and the Run Card are updated. No 2023–2024 data exists in the repo yet.

## 2026-09-30 — F2 Step C done (cloud session) — verdict `F2_FAIL`, project stops
- `python/edgelab/f2.py` and its synthetic tests were committed (`1902058`) **before** the 2023–2024 data was loaded. Planted H2 edge → `F2_PASS`, random walk → `F2_FAIL`; 62 tests pass. `verify_export.py data/f2` → `EXPORT OK`.
- One run (ledger `research/f2/trials_ledger.jsonl`). 2023: 258 days (1 quarantined, 2023-01-16); 2024: 260 days.
- H1 (tree): mean net −0.59 USD/oz (2023 +0.04, 2024 −1.22), bootstrap lower −1.51, p 0.85. H2 (range rule): −0.70 (2023 −0.18, 2024 −1.20), lower −2.21, p 0.78. Neither hypothesis meets any of the four pass checks. Both rules sell 74–79% of the time, and gold rose strongly in 2024 (always long: +0.31 per moment, +1.14 per day).
- Report: `research/f2/report.md`, `report.json`, 10 charts per hypothesis. Per Section 11.4, `F2_FAIL` → the project stops. 2025 was never exported or seen.
