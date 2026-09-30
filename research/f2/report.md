# Edge Discovery Lab — Phase F2 report (one-shot, 2023–2024)

**Verdict: `F2_FAIL`**

Generated 2026-09-30T12:51:18+00:00 · F1 config fingerprint `7e945e717983b088` · bootstrap 10000 day-block reps, seed 20260930 · pre-registration: roadmap Section 11

## Data

- 2023: 258 days, 352093 M1 bars, 1 quarantined
- 2024: 260 days, 355625 M1 bars, 0 quarantined
- quarantined: 2023-01-16
- `xauusd_m1_2023.csv.gz` SHA-256 `ad872abe38adf8d0fbaa7d94a589d687bd350f898152dbdfdaa23ff71a6b82c7`
- `xauusd_m1_2024.csv.gz` SHA-256 `65415baed98abced7c0e6ce5be54e5f89d59283ac41faad6e7248add28c4c17e`

## Result per hypothesis (net USD/oz per trade)

| | H1 (M3-EOD tree) | H2 (previous-day range) |
|---|---|---|
| 2023 trades / days | 61869 / 256 | 212 / 212 |
| 2023 long share | 22.3% | 21.2% |
| 2023 mean net | 0.0371 | -0.1790 |
| 2023 mean net (ATR) | 0.3204 | -0.2652 |
| 2023 win rate | 51.0% | 50.0% |
| 2023 B0 always long | -0.1944 | 0.1783 |
| 2023 B0 always short | -0.3187 | -0.7024 |
| 2024 trades / days | 62190 / 259 | 222 / 222 |
| 2024 long share | 26.5% | 25.7% |
| 2024 mean net | -1.2236 | -1.2016 |
| 2024 mean net (ATR) | -1.2994 | -2.0302 |
| 2024 win rate | 46.6% | 44.6% |
| 2024 B0 always long | 0.3122 | 1.1379 |
| 2024 B0 always short | -0.7937 | -1.6424 |
| 2023–2024 trades / days | 124059 / 515 | 434 / 434 |
| 2023–2024 mean net | -0.5949 | -0.7021 |
| bootstrap lower 95% | -1.5132 | -2.2077 |
| p (bootstrap) | 0.8509 | 0.7759 |
| p (Holm, 2 hypotheses) | 1.0000 | 1.0000 |

## Pass rule (roadmap 11.4)

| Check | H1 | H2 |
|---|---|---|
| 1. mean > 0 in 2023 and in 2024 | **no** | **no** |
| 2. bootstrap lower 95% > 0 | **no** | **no** |
| 3. beats always long and always short, each year | **no** | **no** |
| 4. Holm-adjusted p < 0.05 | **no** | **no** |
| **passes** | **no** | **no** |

H1 trades every eligible decision moment (overlapping moments counted independently, as in F1); H2 trades once per day at the first decision moment. B0 baselines use the same eligible moments/days.

## Example charts (10 per hypothesis, seed [20260930, 5])

### H1
- [1](charts/H1/ex_01.svg) SHORT 2023-03-06 12:00 → 2023-03-06 21:30, net +4.00
- [2](charts/H1/ex_02.svg) SHORT 2023-04-28 15:35 → 2023-04-28 21:30, net -8.33
- [3](charts/H1/ex_03.svg) SHORT 2023-08-02 02:20 → 2023-08-02 21:30, net +14.59
- [4](charts/H1/ex_04.svg) SHORT 2023-11-15 10:45 → 2023-11-15 21:30, net +9.56
- [5](charts/H1/ex_05.svg) SHORT 2023-11-24 05:00 → 2023-11-24 20:45, net -10.51
- [6](charts/H1/ex_06.svg) SHORT 2024-04-04 04:20 → 2024-04-04 21:30, net -1.63
- [7](charts/H1/ex_07.svg) LONG 2024-04-08 13:45 → 2024-04-08 21:30, net -1.35
- [8](charts/H1/ex_08.svg) SHORT 2024-04-16 18:15 → 2024-04-16 21:30, net -4.17
- [9](charts/H1/ex_09.svg) SHORT 2024-07-16 14:20 → 2024-07-16 21:30, net -24.65
- [10](charts/H1/ex_10.svg) SHORT 2024-11-11 04:30 → 2024-11-11 21:30, net +53.92

### H2
- [1](charts/H2/ex_01.svg) SHORT 2023-02-06 01:10 → 2023-02-06 21:30, net -3.61
- [2](charts/H2/ex_02.svg) SHORT 2023-03-31 01:10 → 2023-03-31 21:30, net +11.08
- [3](charts/H2/ex_03.svg) SHORT 2023-06-23 01:10 → 2023-06-23 21:30, net -5.89
- [4](charts/H2/ex_04.svg) SHORT 2023-08-02 02:20 → 2023-08-02 21:30, net +14.59
- [5](charts/H2/ex_05.svg) SHORT 2023-09-04 01:10 → 2023-09-04 21:30, net +1.38
- [6](charts/H2/ex_06.svg) SHORT 2023-10-06 01:05 → 2023-10-06 21:30, net -13.15
- [7](charts/H2/ex_07.svg) SHORT 2023-10-09 01:05 → 2023-10-09 21:30, net -1.87
- [8](charts/H2/ex_08.svg) SHORT 2023-11-23 02:40 → 2023-11-23 21:30, net -1.78
- [9](charts/H2/ex_09.svg) LONG 2024-08-30 01:40 → 2024-08-30 21:30, net -17.87
- [10](charts/H2/ex_10.svg) LONG 2024-10-03 01:10 → 2024-10-03 21:30, net -0.83

## Completion record

```
F2 — COMPLETE
Date: 2026-09-30
Data: 2023: 352093 bars / 258 days / 1 quarantined, 2024: 355625 bars / 260 days / 0 quarantined
Tests: 62 passed in 102.3s (pytest -q, python/tests); f2.py + tests committed in 1902058 before the data was loaded
Result: F2_FAIL
  H1: trades 124059  mean -0.5949  2023 0.0371  2024 -1.2236  boot_low -1.5132  p 0.8509  holm 1.0000  pass False
  H2: trades 434  mean -0.7021  2023 -0.1790  2024 -1.2016  boot_low -2.2077  p 0.7759  holm 1.0000  pass False
```
