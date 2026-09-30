# Edge Discovery Lab — Phase F1 report

**Verdict: `F1_WEAK`**

Generated 2026-09-30T12:07:58+00:00 · config fingerprint `7e945e717983b088` · 200 permutation runs · bootstrap 10000 reps, seed 20260930

## Data

- M1 rows: 884546; days: 645; quarantined days: 4
- decision moments: 152249; with complete features (dataset): 149450

- `xauusd_m1_2020.csv.gz` SHA-256 `00ca2cf04db683893907c9eb5eac5468c83d68803703b58fe4b05d0cdac22130`
- `xauusd_m1_2021.csv.gz` SHA-256 `e5e34c796775ecbb7f32195515191ccc3a88c5a893082f5666ad84df55cfbe21`
- `xauusd_m1_2022.csv.gz` SHA-256 `78c5141f34a6de8e2badaa6c81bf3a2b8a303c98869d8cf9b1ae61e3836d1516`

## The 12 configurations (out-of-fold 2021–2022, net of cost)

| Family | H | Trades | Days | Mean USD/oz | Mean ATR | Win % | Boot low 95% USD | 2021 | 2022 | p perm | p Holm | Null runs trading | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | H30 | 0 | 0 | — | — | — | — | — (0) | — (0) | 1.000 | 1.000 | 15/200 | no |
| M1 | H60 | 0 | 0 | — | — | — | — | — (0) | — (0) | 1.000 | 1.000 | 152/200 | no |
| M1 | H120 | 12590 | 215 | -0.2477 | -0.1622 | 47.4 | -0.5703 | -0.165 (5745) | -0.317 (6845) | 0.410 | 1.000 | 198/200 | no |
| M1 | EOD | 41217 | 356 | -0.2402 | -0.3702 | 49.8 | -1.4306 | 0.557 (13999) | -0.650 (27218) | 0.470 | 1.000 | 200/200 | no |
| M2 | H30 | 9197 | 255 | -0.2155 | -0.2196 | 44.5 | -0.2934 | -0.216 (9197) | — (0) | 0.130 | 1.000 | 200/200 | no |
| M2 | H60 | 43519 | 489 | -0.2442 | -0.2375 | 45.4 | -0.3232 | -0.248 (28534) | -0.237 (14985) | 0.370 | 1.000 | 200/200 | no |
| M2 | H120 | 65607 | 511 | -0.2584 | -0.2419 | 47.2 | -0.3769 | -0.206 (32853) | -0.311 (32754) | 0.510 | 1.000 | 200/200 | no |
| M2 | EOD | 70524 | 510 | -0.0159 | -0.0714 | 49.2 | -0.6823 | 0.105 (35333) | -0.137 (35191) | 0.220 | 1.000 | 200/200 | no |
| M3 | H30 | 14130 | 354 | -0.2364 | -0.1647 | 45.6 | -0.3450 | -0.124 (6430) | -0.331 (7700) | 0.395 | 1.000 | 200/200 | no |
| M3 | H60 | 5940 | 173 | -0.0078 | -0.0165 | 47.4 | -0.3510 | 0.095 (3997) | -0.218 (1943) | 0.000 | 0.000 | 200/200 | no |
| M3 | H120 | 8542 | 197 | 0.2762 | 0.1908 | 50.0 | -0.3421 | 0.577 (4796) | -0.108 (3746) | 0.000 | 0.000 | 200/200 | no |
| M3 | EOD | 122341 | 511 | 0.5903 | 0.4914 | 49.4 | -0.1836 | 0.474 (61711) | 0.709 (60630) | 0.035 | 0.350 | 200/200 | no |

Per-year cells: mean net USD/oz (trades). p perm = share of the shuffled runs with a mean >= the real one (a shuffled run without trades scores 0). Holm over the 12 configurations at α = 0.05. 'Null runs trading' shows how many shuffled runs produced any trade: when few do, a small p mostly says the real rule traded at all, so read F1_WEAK with care.

## Baseline B0 (always long / always short, out-of-fold years)

| Baseline | H | Trades | Mean USD/oz | Mean ATR | Win % |
|---|---|---|---|---|---|
| B0 always long | H30 | 119785 | -0.2720 | -0.2603 | 43.3 |
| B0 always short | H30 | 119785 | -0.2393 | -0.2317 | 43.9 |
| B0 always long | H60 | 116719 | -0.2825 | -0.2674 | 45.1 |
| B0 always short | H60 | 116719 | -0.2280 | -0.2247 | 46.0 |
| B0 always long | H120 | 110587 | -0.3030 | -0.2757 | 46.8 |
| B0 always short | H120 | 110587 | -0.2065 | -0.2201 | 47.1 |
| B0 always long | EOD | 122341 | -0.6513 | -0.3312 | 47.1 |
| B0 always short | EOD | 122341 | 0.1420 | -0.1560 | 49.6 |

## Readable rules

### M1_H30 — 0 active rules

### M1_H60 — 0 active rules

### M1_H120 — 2 active rules
- test 2021 (trained before it): 1 rules
  - `M1-H120-2021-000` if -5.457 <= d_pdh < -3.286 then LONG H120
- test 2022 (trained before it): 1 rules
  - `M1-H120-2022-000` if 0.5969 <= pd_range_rel < 0.7176 then SHORT H120

### M1_EOD — 8 active rules
- test 2021 (trained before it): 2 rules
  - `M1-EOD-2021-000` if 25.3 <= d_pdl then LONG EOD
  - `M1-EOD-2021-001` if 0.2442 <= pd_ret < 0.4005 then SHORT EOD
- test 2022 (trained before it): 6 rules
  - `M1-EOD-2022-000` if d_pdl < -0.1759 then SHORT EOD
  - `M1-EOD-2022-001` if 0.9412 <= spread_rel < 1 then SHORT EOD
  - `M1-EOD-2022-002` if 0.7744 <= pd_ret then LONG EOD
  - `M1-EOD-2022-003` if 1.418 <= pd_range_rel < 1.698 then LONG EOD
  - `M1-EOD-2022-004` if 0.5969 <= pd_range_rel < 0.7176 then SHORT EOD
  - `M1-EOD-2022-005` if 0.9075 <= pd_range_rel < 0.9842 then SHORT EOD

### M2_H30 — 6 active rules
- test 2021 (trained before it): 6 rules
  - `M2-H30-2021-000` if r15 < -0.876 and 2.513 <= d_open < 6.279 then LONG H30
  - `M2-H30-2021-001` if -0.6032 <= r240 < 1.497 and consec < -2 then LONG H30
  - `M2-H30-2021-002` if r240 < -2.952 and 6 <= bars_since_high < 23 then LONG H30
  - `M2-H30-2021-003` if 2.513 <= d_open < 6.279 and consec < -2 then LONG H30
  - `M2-H30-2021-004` if 49 <= bars_since_high < 98 and 4 <= hour_bucket then LONG H30
  - `M2-H30-2021-005` if 31 <= bars_since_low < 63 and 4.247 <= overlap12 then LONG H30
- test 2022 (trained before it): 0 rules

### M2_H60 — 45 active rules
- test 2021 (trained before it): 29 rules
- test 2022 (trained before it): 16 rules

### M2_H120 — 133 active rules
- test 2021 (trained before it): 86 rules
- test 2022 (trained before it): 47 rules

### M2_EOD — 312 active rules
- test 2021 (trained before it): 40 rules
- test 2022 (trained before it): 272 rules

### M3_H30 — 8 active rules
- test 2021 (trained before it): 4 rules
  - `M3-H30-2021-000` if d_asia_lo <= -6.264 then SHORT H30
  - `M3-H30-2021-001` if -6.264 < d_asia_lo and r_day <= -0.604 and d_pdl <= -1.998 then SHORT H30
  - `M3-H30-2021-002` if -6.264 < d_asia_lo and r_day <= -0.604 and -1.998 < d_pdl then LONG H30
  - `M3-H30-2021-003` if -6.264 < d_asia_lo and -0.604 < r_day and 151.5 < bars_since_high then SHORT H30
- test 2022 (trained before it): 4 rules
  - `M3-H30-2022-000` if d_pdl <= -2.183 and atr_rel20 <= 1.476 and min_since_resume <= 915.5 then SHORT H30
  - `M3-H30-2022-001` if d_pdl <= -2.183 and 1.476 < atr_rel20 and pd_range_rel <= 1.107 then SHORT H30
  - `M3-H30-2022-002` if -2.183 < d_pdl and r_day <= -0.7504 and min_since_resume <= 871.5 then LONG H30
  - `M3-H30-2022-003` if -2.183 < d_pdl and -0.7504 < r_day and pos_day <= 0.1143 then LONG H30

### M3_H60 — 8 active rules
- test 2021 (trained before it): 3 rules
  - `M3-H60-2021-000` if d_asia_lo <= -6.474 then SHORT H60
  - `M3-H60-2021-001` if -6.474 < d_asia_lo and bars_since_high <= 150.5 and r_day <= -0.7895 then LONG H60
  - `M3-H60-2021-002` if -6.474 < d_asia_lo and 150.5 < bars_since_high and -6.367 < d_asia_hi then SHORT H60
- test 2022 (trained before it): 5 rules
  - `M3-H60-2022-000` if d_asia_lo <= -7.8 and min_since_resume <= 896.5 then SHORT H60
  - `M3-H60-2022-001` if d_asia_lo <= -7.8 and 896.5 < min_since_resume and pd_range_rel <= 0.908 then LONG H60
  - `M3-H60-2022-002` if d_asia_lo <= -7.8 and 896.5 < min_since_resume and 0.908 < pd_range_rel then SHORT H60
  - `M3-H60-2022-003` if -7.8 < d_asia_lo and d_asia_hi <= 9.32 and pd_ret <= -2.034 then LONG H60
  - `M3-H60-2022-004` if -7.8 < d_asia_lo and 9.32 < d_asia_hi then SHORT H60

### M3_H120 — 8 active rules
- test 2021 (trained before it): 4 rules
  - `M3-H120-2021-000` if d_asia_lo <= -5.39 then SHORT H120
  - `M3-H120-2021-001` if -5.39 < d_asia_lo and bars_since_high <= 149.5 and r_day <= -0.7513 then LONG H120
  - `M3-H120-2021-002` if -5.39 < d_asia_lo and 149.5 < bars_since_high and pd_range_rel <= 1.035 then SHORT H120
  - `M3-H120-2021-003` if -5.39 < d_asia_lo and 149.5 < bars_since_high and 1.035 < pd_range_rel then SHORT H120
- test 2022 (trained before it): 4 rules
  - `M3-H120-2022-000` if d_asia_lo <= -7.418 and min_since_resume <= 876.5 then SHORT H120
  - `M3-H120-2022-001` if d_asia_lo <= -7.418 and 876.5 < min_since_resume then SHORT H120
  - `M3-H120-2022-002` if -7.418 < d_asia_lo and pd_ret <= -2.034 then LONG H120
  - `M3-H120-2022-003` if -7.418 < d_asia_lo and -2.034 < pd_ret and 154.5 < bars_since_high then SHORT H120

### M3_EOD — 13 active rules
- test 2021 (trained before it): 6 rules
- test 2022 (trained before it): 7 rules

## Completion record

```
F1 — COMPLETE
Date: 2026-09-30
Files changed: python/edgelab/{config,data,report}.py, python/tests/{synth,test_data_audit,test_end_to_end,test_features,test_folds_permutation,test_stats,test_targets,test_window}.py, docs/EL_RunCard.md, data/audit_2020_2022.json, research/f1/*, EdgeLab_Roadmap.md
Data: rows 884546, days 645, quarantined days 4, manifest SHA-256 xauusd_m1_2020.csv.gz=00ca2cf04db6…, xauusd_m1_2021.csv.gz=e5e34c796775…, xauusd_m1_2022.csv.gz=78c5141f34a6…
Tests: 47 passed in 88.7s (pytest -q, python/tests)
Result: F1_WEAK
  M1  H30: trades      0  mean        — USD  boot_low        —  p 1.000  holm 1.000
  M1  H60: trades      0  mean        — USD  boot_low        —  p 1.000  holm 1.000
  M1 H120: trades  12590  mean  -0.2477 USD  boot_low  -0.5703  p 0.410  holm 1.000
  M1  EOD: trades  41217  mean  -0.2402 USD  boot_low  -1.4306  p 0.470  holm 1.000
  M2  H30: trades   9197  mean  -0.2155 USD  boot_low  -0.2934  p 0.130  holm 1.000
  M2  H60: trades  43519  mean  -0.2442 USD  boot_low  -0.3232  p 0.370  holm 1.000
  M2 H120: trades  65607  mean  -0.2584 USD  boot_low  -0.3769  p 0.510  holm 1.000
  M2  EOD: trades  70524  mean  -0.0159 USD  boot_low  -0.6823  p 0.220  holm 1.000
  M3  H30: trades  14130  mean  -0.2364 USD  boot_low  -0.3450  p 0.395  holm 1.000
  M3  H60: trades   5940  mean  -0.0078 USD  boot_low  -0.3510  p 0.000  holm 0.000
  M3 H120: trades   8542  mean   0.2762 USD  boot_low  -0.3421  p 0.000  holm 0.000
  M3  EOD: trades 122341  mean   0.5903 USD  boot_low  -0.1836  p 0.035  holm 0.350
```
