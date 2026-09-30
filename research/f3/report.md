# Edge Discovery Lab — Phase F3 report (path-dependent exits)

**Verdict: `F3_STOP`**

Generated 2026-09-30T15:21:32+00:00 · F1 config fingerprint `7e945e717983b088` · 84 configurations · 200 day-block permutations, reality check on the maximum

## Data

- M1 rows 884546; days 645; quarantined 4; dataset moments 149450
- `xauusd_m1_2020.csv.gz` SHA-256 `00ca2cf04db683893907c9eb5eac5468c83d68803703b58fe4b05d0cdac22130`
- `xauusd_m1_2021.csv.gz` SHA-256 `e5e34c796775ecbb7f32195515191ccc3a88c5a893082f5666ad84df55cfbe21`
- `xauusd_m1_2022.csv.gz` SHA-256 `78c5141f34a6de8e2badaa6c81bf3a2b8a303c98869d8cf9b1ae61e3836d1516`

Null distribution of the best configuration (mean net R, one position at a time): median 0.000, 95% 0.167, 90% 0.100.

## All 84 configurations (out-of-fold 2021–2022, one position at a time, net R)

| Family | Exit | Trades 2021 / 2022 | Win % | Avg win R | Avg loss R | Mean R 2021 | Mean R 2022 | Mean R | Boot low R | p (RC) | B0 long 2021/2022 | B0 short 2021/2022 | Same-bar % | Max DD R | All-moments n / mean R | Result |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | `SL0.5_TP1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.311/-0.305 | -0.299/-0.299 | — | 0.0 | 0 / — |  |
| M1 | `SL0.5_TP1.5` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.309/-0.303 | -0.293/-0.297 | — | 0.0 | 0 / — |  |
| M1 | `SL0.5_TP2` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.309/-0.308 | -0.296/-0.297 | — | 0.0 | 0 / — |  |
| M1 | `SL0.5_TP3` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.312/-0.307 | -0.296/-0.297 | — | 0.0 | 0 / — |  |
| M1 | `SL1_TP1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.197/-0.194 | -0.182/-0.178 | — | 0.0 | 0 / — |  |
| M1 | `SL1_TP1.5` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.198/-0.192 | -0.176/-0.179 | — | 0.0 | 0 / — |  |
| M1 | `SL1_TP2` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.195/-0.197 | -0.166/-0.175 | — | 0.0 | 0 / — |  |
| M1 | `SL1_TP3` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.200/-0.199 | -0.166/-0.160 | — | 0.0 | 0 / — |  |
| M1 | `SL1.5_TP1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.145/-0.141 | -0.125/-0.127 | — | 0.0 | 0 / — |  |
| M1 | `SL1.5_TP1.5` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.149/-0.138 | -0.113/-0.112 | — | 0.0 | 0 / — |  |
| M1 | `SL1.5_TP2` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.151/-0.146 | -0.116/-0.111 | — | 0.0 | 0 / — |  |
| M1 | `SL1.5_TP3` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.157/-0.150 | -0.097/-0.097 | — | 0.0 | 0 / — |  |
| M1 | `SL2_TP1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.123/-0.112 | -0.086/-0.087 | — | 0.0 | 0 / — |  |
| M1 | `SL2_TP1.5` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.128/-0.115 | -0.082/-0.083 | — | 0.0 | 0 / — |  |
| M1 | `SL2_TP2` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.134/-0.118 | -0.073/-0.071 | — | 0.0 | 0 / — |  |
| M1 | `SL2_TP3` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.138/-0.120 | -0.066/-0.060 | — | 0.0 | 0 / — |  |
| M1 | `SL0.5` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.398/-0.354 | -0.319/-0.304 | — | 0.0 | 0 / — |  |
| M1 | `SL1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.278/-0.202 | -0.151/-0.124 | — | 0.0 | 0 / — |  |
| M1 | `SL1.5` | 0 / 144 | 10.4 | 6.61 | -0.85 | — | -0.074 | -0.074 | -0.442 | 1.000 | -0.218/-0.138 | -0.076/-0.069 | 0.0 | 57.5 | 4238 / 0.071 |  |
| M1 | `SL2` | 0 / 110 | 13.6 | 5.05 | -0.88 | — | -0.072 | -0.072 | -0.443 | 1.000 | -0.205/-0.102 | -0.035/-0.058 | 0.0 | 43.2 | 4238 / 0.095 |  |
| M1 | `TR1x1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.180/-0.176 | -0.161/-0.163 | — | 0.0 | 0 / — |  |
| M1 | `TR1x2` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.195/-0.185 | -0.153/-0.149 | — | 0.0 | 0 / — |  |
| M1 | `TR2x1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.100/-0.096 | -0.088/-0.088 | — | 0.0 | 0 / — |  |
| M1 | `TR2x2` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.108/-0.098 | -0.074/-0.079 | — | 0.0 | 0 / — |  |
| M1 | `BE1_TP2` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.193/-0.190 | -0.167/-0.174 | — | 0.0 | 0 / — |  |
| M1 | `BE1_TP3` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.198/-0.193 | -0.164/-0.166 | — | 0.0 | 0 / — |  |
| M1 | `BE2_TP2` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.123/-0.113 | -0.080/-0.077 | — | 0.0 | 0 / — |  |
| M1 | `BE2_TP3` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.129/-0.115 | -0.075/-0.067 | — | 0.0 | 0 / — |  |
| M2 | `SL0.5_TP1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.311/-0.305 | -0.299/-0.299 | — | 0.0 | 0 / — |  |
| M2 | `SL0.5_TP1.5` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.309/-0.303 | -0.293/-0.297 | — | 0.0 | 0 / — |  |
| M2 | `SL0.5_TP2` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.309/-0.308 | -0.296/-0.297 | — | 0.0 | 0 / — |  |
| M2 | `SL0.5_TP3` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.312/-0.307 | -0.296/-0.297 | — | 0.0 | 0 / — |  |
| M2 | `SL1_TP1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.197/-0.194 | -0.182/-0.178 | — | 0.0 | 0 / — |  |
| M2 | `SL1_TP1.5` | 0 / 197 | 35.0 | 1.28 | -0.92 | — | -0.148 | -0.148 | -0.259 | 1.000 | -0.198/-0.192 | -0.176/-0.179 | 0.0 | 35.7 | 658 / -0.129 |  |
| M2 | `SL1_TP2` | 1085 / 171 | 26.4 | 1.54 | -0.84 | -0.213 | -0.202 | -0.211 | -0.256 | 1.000 | -0.195/-0.197 | -0.166/-0.175 | 0.1 | 267.3 | 3997 / -0.197 |  |
| M2 | `SL1_TP3` | 927 / 142 | 20.5 | 2.20 | -0.84 | -0.214 | -0.210 | -0.214 | -0.274 | 1.000 | -0.200/-0.199 | -0.166/-0.160 | 0.0 | 230.3 | 3997 / -0.178 |  |
| M2 | `SL1.5_TP1` | 592 / 150 | 43.9 | 0.84 | -0.90 | -0.138 | -0.122 | -0.135 | -0.183 | 1.000 | -0.145/-0.141 | -0.125/-0.127 | 0.0 | 104.6 | 3010 / -0.135 |  |
| M2 | `SL1.5_TP1.5` | 1303 / 415 | 36.3 | 1.20 | -0.87 | -0.134 | -0.083 | -0.122 | -0.162 | 1.000 | -0.149/-0.138 | -0.113/-0.112 | 0.0 | 209.7 | 9496 / -0.098 |  |
| M2 | `SL1.5_TP2` | 2119 / 438 | 31.0 | 1.54 | -0.87 | -0.127 | -0.117 | -0.125 | -0.161 | 1.000 | -0.151/-0.146 | -0.116/-0.111 | 0.0 | 340.5 | 15809 / -0.128 |  |
| M2 | `SL1.5_TP3` | 1171 / 748 | 24.1 | 2.16 | -0.87 | -0.162 | -0.109 | -0.141 | -0.189 | 1.000 | -0.157/-0.150 | -0.097/-0.097 | 0.0 | 285.6 | 14103 / -0.128 |  |
| M2 | `SL2_TP1` | 2002 / 376 | 47.3 | 0.84 | -0.88 | -0.064 | -0.064 | -0.064 | -0.092 | 1.000 | -0.123/-0.112 | -0.086/-0.087 | 0.0 | 173.6 | 15550 / -0.074 |  |
| M2 | `SL2_TP1.5` | 2331 / 1098 | 37.4 | 1.23 | -0.89 | -0.111 | -0.076 | -0.100 | -0.130 | 1.000 | -0.128/-0.115 | -0.082/-0.083 | 0.0 | 362.6 | 27155 / -0.081 |  |
| M2 | `SL2_TP2` | 1772 / 839 | 31.8 | 1.58 | -0.89 | -0.084 | -0.142 | -0.103 | -0.140 | 1.000 | -0.134/-0.118 | -0.073/-0.071 | 0.0 | 279.0 | 24494 / -0.096 |  |
| M2 | `SL2_TP3` | 1316 / 1401 | 27.8 | 2.16 | -0.89 | -0.041 | -0.048 | -0.045 | -0.091 | 1.000 | -0.138/-0.120 | -0.066/-0.060 | 0.1 | 202.7 | 27905 / -0.107 |  |
| M2 | `SL0.5` | 0 / 1215 | 5.0 | 10.77 | -0.81 | — | -0.228 | -0.228 | -0.364 | 1.000 | -0.398/-0.354 | -0.319/-0.304 | 0.0 | 357.8 | 5698 / -0.251 |  |
| M2 | `SL1` | 774 / 1330 | 9.2 | 6.37 | -0.84 | -0.223 | -0.154 | -0.179 | -0.283 | 1.000 | -0.278/-0.202 | -0.151/-0.124 | 0.0 | 411.2 | 20465 / -0.142 |  |
| M2 | `SL1.5` | 1333 / 1348 | 12.4 | 5.18 | -0.86 | -0.149 | -0.077 | -0.112 | -0.205 | 1.000 | -0.218/-0.138 | -0.076/-0.069 | 0.0 | 372.5 | 37687 / -0.096 |  |
| M2 | `SL2` | 878 / 1243 | 14.9 | 3.76 | -0.88 | -0.267 | -0.130 | -0.187 | -0.270 | 1.000 | -0.205/-0.102 | -0.035/-0.058 | 0.0 | 403.3 | 48812 / -0.040 |  |
| M2 | `TR1x1` | 519 / 219 | 27.6 | 0.91 | -0.65 | -0.243 | -0.162 | -0.219 | -0.269 | 1.000 | -0.180/-0.176 | -0.161/-0.163 | 0.0 | 162.4 | 1711 / -0.197 |  |
| M2 | `TR1x2` | 834 / 144 | 22.1 | 1.75 | -0.76 | -0.207 | -0.182 | -0.204 | -0.272 | 1.000 | -0.195/-0.185 | -0.153/-0.149 | 0.0 | 211.8 | 3125 / -0.107 |  |
| M2 | `TR2x1` | 469 / 218 | 29.5 | 0.51 | -0.39 | -0.148 | -0.081 | -0.127 | -0.158 | 1.000 | -0.100/-0.096 | -0.088/-0.088 | 0.0 | 87.4 | 1711 / -0.116 |  |
| M2 | `TR2x2` | 1035 / 638 | 33.1 | 1.01 | -0.63 | -0.125 | -0.032 | -0.090 | -0.128 | 1.000 | -0.108/-0.098 | -0.074/-0.079 | 0.0 | 156.7 | 9328 / -0.044 |  |
| M2 | `BE1_TP2` | 0 / 202 | 20.3 | 1.69 | -0.62 | — | -0.151 | -0.151 | -0.246 | 1.000 | -0.193/-0.190 | -0.167/-0.174 | 0.0 | 37.6 | 658 / -0.163 |  |
| M2 | `BE1_TP3` | 954 / 179 | 13.6 | 2.22 | -0.57 | -0.203 | -0.142 | -0.193 | -0.242 | 1.000 | -0.198/-0.193 | -0.164/-0.166 | 0.1 | 224.5 | 3125 / -0.177 |  |
| M2 | `BE2_TP2` | 1406 / 644 | 24.6 | 1.55 | -0.64 | -0.088 | -0.128 | -0.101 | -0.137 | 1.000 | -0.123/-0.113 | -0.080/-0.077 | 0.0 | 226.8 | 15439 / -0.090 |  |
| M2 | `BE2_TP3` | 994 / 1084 | 17.9 | 2.18 | -0.59 | -0.152 | -0.052 | -0.100 | -0.141 | 1.000 | -0.129/-0.115 | -0.075/-0.067 | 0.0 | 210.8 | 17894 / -0.082 |  |
| M3 | `SL0.5_TP1` | 0 / 0 | — | — | — | — | — | — | — | 1.000 | -0.311/-0.305 | -0.299/-0.299 | — | 0.0 | 0 / — |  |
| M3 | `SL0.5_TP1.5` | 0 / 2 | 0.0 | — | -0.94 | — | -0.940 | -0.940 | -0.958 | 1.000 | -0.309/-0.303 | -0.293/-0.297 | 0.0 | 1.9 | 3 / -0.939 |  |
| M3 | `SL0.5_TP2` | 156 / 0 | 31.4 | 1.57 | -0.89 | -0.119 | — | -0.119 | -0.276 | 1.000 | -0.309/-0.308 | -0.296/-0.297 | 0.0 | 18.6 | 172 / -0.082 |  |
| M3 | `SL0.5_TP3` | 668 / 192 | 21.5 | 2.25 | -0.86 | -0.241 | -0.025 | -0.193 | -0.260 | 1.000 | -0.312/-0.307 | -0.296/-0.297 | 0.0 | 168.8 | 1506 / -0.210 |  |
| M3 | `SL1_TP1` | 1284 / 159 | 46.1 | 0.81 | -0.87 | -0.093 | -0.129 | -0.097 | -0.133 | 1.000 | -0.197/-0.194 | -0.182/-0.178 | 0.0 | 161.3 | 1649 / -0.103 |  |
| M3 | `SL1_TP1.5` | 1810 / 131 | 32.9 | 1.18 | -0.86 | -0.194 | -0.057 | -0.185 | -0.222 | 1.000 | -0.198/-0.192 | -0.176/-0.179 | 0.0 | 366.0 | 5441 / -0.168 |  |
| M3 | `SL1_TP2` | 4562 / 1550 | 29.8 | 1.59 | -0.87 | -0.135 | -0.144 | -0.137 | -0.161 | 1.000 | -0.195/-0.197 | -0.166/-0.175 | 0.1 | 855.9 | 29345 / -0.159 |  |
| M3 | `SL1_TP3` | 3837 / 855 | 22.2 | 2.27 | -0.86 | -0.161 | -0.176 | -0.163 | -0.196 | 1.000 | -0.200/-0.199 | -0.166/-0.160 | 0.0 | 793.5 | 28429 / -0.182 |  |
| M3 | `SL1.5_TP1` | 3588 / 542 | 43.9 | 0.84 | -0.88 | -0.134 | -0.091 | -0.128 | -0.150 | 1.000 | -0.145/-0.141 | -0.125/-0.127 | 0.0 | 532.9 | 21508 / -0.149 |  |
| M3 | `SL1.5_TP1.5` | 1820 / 431 | 35.3 | 1.24 | -0.88 | -0.136 | -0.109 | -0.131 | -0.171 | 1.000 | -0.149/-0.138 | -0.113/-0.112 | 0.0 | 304.1 | 14995 / -0.142 |  |
| M3 | `SL1.5_TP2` | 1735 / 434 | 31.0 | 1.61 | -0.88 | -0.104 | -0.119 | -0.107 | -0.151 | 1.000 | -0.151/-0.146 | -0.116/-0.111 | 0.0 | 236.8 | 20421 / -0.102 |  |
| M3 | `SL1.5_TP3` | 931 / 568 | 23.2 | 2.26 | -0.89 | -0.164 | -0.156 | -0.161 | -0.216 | 1.000 | -0.157/-0.150 | -0.097/-0.097 | 0.0 | 244.2 | 17852 / -0.127 |  |
| M3 | `SL2_TP1` | 1927 / 317 | 48.0 | 0.85 | -0.89 | -0.048 | -0.075 | -0.051 | -0.083 | 1.000 | -0.123/-0.112 | -0.086/-0.087 | 0.1 | 131.5 | 17398 / -0.102 |  |
| M3 | `SL2_TP1.5` | 1624 / 223 | 37.4 | 1.26 | -0.90 | -0.098 | -0.022 | -0.089 | -0.131 | 1.000 | -0.128/-0.115 | -0.082/-0.083 | 0.0 | 181.8 | 21619 / -0.093 |  |
| M3 | `SL2_TP2` | 878 / 728 | 31.1 | 1.61 | -0.90 | -0.138 | -0.100 | -0.121 | -0.170 | 1.000 | -0.134/-0.118 | -0.073/-0.071 | 0.0 | 201.3 | 24097 / -0.083 |  |
| M3 | `SL2_TP3` | 1591 / 134 | 24.2 | 2.39 | -0.90 | -0.113 | 0.014 | -0.103 | -0.162 | 1.000 | -0.138/-0.120 | -0.066/-0.060 | 0.0 | 198.9 | 32591 / -0.110 |  |
| M3 | `SL0.5` | 3677 / 2339 | 4.1 | 9.28 | -0.73 | -0.365 | -0.251 | -0.321 | -0.376 | 1.000 | -0.398/-0.354 | -0.319/-0.304 | 0.0 | 1983.1 | 40251 / -0.259 |  |
| M3 | `SL1` | 3077 / 1066 | 7.8 | 6.75 | -0.83 | -0.251 | -0.190 | -0.235 | -0.301 | 1.000 | -0.278/-0.202 | -0.151/-0.124 | 0.0 | 1011.5 | 75415 / -0.191 |  |
| M3 | `SL1.5` | 1755 / 1988 | 11.8 | 5.26 | -0.87 | -0.135 | -0.148 | -0.142 | -0.211 | 1.000 | -0.218/-0.138 | -0.076/-0.069 | 0.0 | 538.2 | 113938 / -0.106 |  |
| M3 | `SL2` | 1323 / 1188 | 15.8 | 3.89 | -0.89 | -0.118 | -0.154 | -0.135 | -0.211 | 1.000 | -0.205/-0.102 | -0.035/-0.058 | 0.0 | 352.0 | 91820 / -0.084 |  |
| M3 | `TR1x1` | 831 / 334 | 31.3 | 0.92 | -0.65 | -0.142 | -0.188 | -0.155 | -0.192 | 1.000 | -0.180/-0.176 | -0.161/-0.163 | 0.0 | 183.8 | 4315 / -0.180 |  |
| M3 | `TR1x2` | 1189 / 445 | 24.2 | 1.67 | -0.78 | -0.215 | -0.110 | -0.186 | -0.250 | 1.000 | -0.195/-0.185 | -0.153/-0.149 | 0.0 | 315.1 | 10913 / -0.238 |  |
| M3 | `TR2x1` | 393 / 125 | 36.1 | 0.46 | -0.37 | -0.055 | -0.112 | -0.069 | -0.097 | 1.000 | -0.100/-0.096 | -0.088/-0.088 | 0.0 | 37.8 | 1876 / -0.102 |  |
| M3 | `TR2x2` | 3460 / 476 | 33.5 | 0.95 | -0.62 | -0.088 | -0.129 | -0.093 | -0.116 | 1.000 | -0.108/-0.098 | -0.074/-0.079 | 0.0 | 387.6 | 39410 / -0.110 |  |
| M3 | `BE1_TP2` | 530 / 164 | 20.3 | 1.66 | -0.64 | -0.156 | -0.239 | -0.176 | -0.232 | 1.000 | -0.193/-0.190 | -0.167/-0.174 | 0.0 | 122.3 | 2863 / -0.169 |  |
| M3 | `BE1_TP3` | 1005 / 674 | 18.3 | 2.06 | -0.60 | -0.093 | -0.137 | -0.111 | -0.156 | 1.000 | -0.198/-0.193 | -0.164/-0.166 | 0.0 | 195.3 | 10082 / -0.131 |  |
| M3 | `BE2_TP2` | 877 / 501 | 26.3 | 1.54 | -0.66 | -0.110 | -0.027 | -0.080 | -0.120 | 1.000 | -0.123/-0.113 | -0.080/-0.077 | 0.0 | 114.8 | 17299 / -0.087 |  |
| M3 | `BE2_TP3` | 765 / 739 | 18.0 | 2.11 | -0.57 | -0.101 | -0.076 | -0.089 | -0.131 | 1.000 | -0.129/-0.115 | -0.075/-0.067 | 0.0 | 134.5 | 21144 / -0.112 |  |

p (RC) = share of the permutation runs whose **best** configuration had a mean ≥ this one. B0 = always long / always short with the same exit, one position at a time. Same-bar % = trades whose stop and TP were touched in the same M1 bar (counted as the stop).

## Exit rules

- `SL0.5_TP1`: SL 0.5 ATR, TP 1 x SL, else EOD
- `SL0.5_TP1.5`: SL 0.5 ATR, TP 1.5 x SL, else EOD
- `SL0.5_TP2`: SL 0.5 ATR, TP 2 x SL, else EOD
- `SL0.5_TP3`: SL 0.5 ATR, TP 3 x SL, else EOD
- `SL1_TP1`: SL 1 ATR, TP 1 x SL, else EOD
- `SL1_TP1.5`: SL 1 ATR, TP 1.5 x SL, else EOD
- `SL1_TP2`: SL 1 ATR, TP 2 x SL, else EOD
- `SL1_TP3`: SL 1 ATR, TP 3 x SL, else EOD
- `SL1.5_TP1`: SL 1.5 ATR, TP 1 x SL, else EOD
- `SL1.5_TP1.5`: SL 1.5 ATR, TP 1.5 x SL, else EOD
- `SL1.5_TP2`: SL 1.5 ATR, TP 2 x SL, else EOD
- `SL1.5_TP3`: SL 1.5 ATR, TP 3 x SL, else EOD
- `SL2_TP1`: SL 2 ATR, TP 1 x SL, else EOD
- `SL2_TP1.5`: SL 2 ATR, TP 1.5 x SL, else EOD
- `SL2_TP2`: SL 2 ATR, TP 2 x SL, else EOD
- `SL2_TP3`: SL 2 ATR, TP 3 x SL, else EOD
- `SL0.5`: SL 0.5 ATR, no TP, else EOD
- `SL1`: SL 1 ATR, no TP, else EOD
- `SL1.5`: SL 1.5 ATR, no TP, else EOD
- `SL2`: SL 2 ATR, no TP, else EOD
- `TR1x1`: initial SL 1 ATR, trailing 1 ATR behind the best close, else EOD
- `TR1x2`: initial SL 1 ATR, trailing 2 ATR behind the best close, else EOD
- `TR2x1`: initial SL 2 ATR, trailing 1 ATR behind the best close, else EOD
- `TR2x2`: initial SL 2 ATR, trailing 2 ATR behind the best close, else EOD
- `BE1_TP2`: SL 1 ATR -> breakeven after +1 x SL, TP 2 x SL, else EOD
- `BE1_TP3`: SL 1 ATR -> breakeven after +1 x SL, TP 3 x SL, else EOD
- `BE2_TP2`: SL 2 ATR -> breakeven after +1 x SL, TP 2 x SL, else EOD
- `BE2_TP3`: SL 2 ATR -> breakeven after +1 x SL, TP 3 x SL, else EOD

## Readable rules

All rules of all configurations are in `report.json` (`rules`). Listed here: configurations that pass or are weak, and any configuration with at most 12 rules.

### M1_SL1.5 — 1 rules
- test 2021: 0 rules
- test 2022: 1 rules
  - `M1-SL1.5-2022-000` if 0.9075 <= pd_range_rel < 0.9842 then SHORT SL1.5

### M1_SL2 — 1 rules
- test 2021: 0 rules
- test 2022: 1 rules
  - `M1-SL2-2022-000` if 0.9075 <= pd_range_rel < 0.9842 then SHORT SL2

### M2_SL1_TP1.5 — 1 rules
- test 2021: 0 rules
- test 2022: 1 rules
  - `M2-SL1_TP1.5-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT SL1_TP1.5

### M2_SL1_TP2 — 5 rules
- test 2021: 4 rules
  - `M2-SL1_TP2-2021-000` if -0.3134 <= r_day < -0.02803 and 64 <= bars_since_low < 113 then SHORT SL1_TP2
  - `M2-SL1_TP2-2021-001` if 0.2633 <= pos_day < 0.4671 and 64 <= bars_since_low < 113 then SHORT SL1_TP2
  - `M2-SL1_TP2-2021-002` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG SL1_TP2
  - `M2-SL1_TP2-2021-003` if -3.516 <= d_open < -0.4054 and 64 <= bars_since_low < 113 then SHORT SL1_TP2
- test 2022: 1 rules
  - `M2-SL1_TP2-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT SL1_TP2

### M2_SL1_TP3 — 5 rules
- test 2021: 4 rules
  - `M2-SL1_TP3-2021-000` if -0.3134 <= r_day < -0.02803 and 64 <= bars_since_low < 113 then SHORT SL1_TP3
  - `M2-SL1_TP3-2021-001` if 0.2633 <= pos_day < 0.4671 and 64 <= bars_since_low < 113 then SHORT SL1_TP3
  - `M2-SL1_TP3-2021-002` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG SL1_TP3
  - `M2-SL1_TP3-2021-003` if -3.516 <= d_open < -0.4054 and 64 <= bars_since_low < 113 then SHORT SL1_TP3
- test 2022: 1 rules
  - `M2-SL1_TP3-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT SL1_TP3

### M2_SL1.5_TP1 — 4 rules
- test 2021: 3 rules
  - `M2-SL1.5_TP1-2021-000` if -0.3134 <= r_day < -0.02803 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP1
  - `M2-SL1.5_TP1-2021-001` if 0.2633 <= pos_day < 0.4671 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP1
  - `M2-SL1.5_TP1-2021-002` if -3.516 <= d_open < -0.4054 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP1
- test 2022: 1 rules
  - `M2-SL1.5_TP1-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT SL1.5_TP1

### M2_SL1.5_TP1.5 — 8 rules
- test 2021: 6 rules
  - `M2-SL1.5_TP1.5-2021-000` if -0.3134 <= r_day < -0.02803 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP1.5
  - `M2-SL1.5_TP1.5-2021-001` if rv30_rel < 0.7536 and 113 <= bars_since_low then SHORT SL1.5_TP1.5
  - `M2-SL1.5_TP1.5-2021-002` if 0.2633 <= pos_day < 0.4671 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP1.5
  - `M2-SL1.5_TP1.5-2021-003` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG SL1.5_TP1.5
  - `M2-SL1.5_TP1.5-2021-004` if -3.516 <= d_open < -0.4054 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP1.5
  - `M2-SL1.5_TP1.5-2021-005` if 113 <= bars_since_low and tv_rel < 0.7789 then SHORT SL1.5_TP1.5
- test 2022: 2 rules
  - `M2-SL1.5_TP1.5-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT SL1.5_TP1.5
  - `M2-SL1.5_TP1.5-2022-001` if 3.57 <= d_pdl < 8.353 and 106 <= bars_since_low then SHORT SL1.5_TP1.5

### M2_SL1.5_TP2 — 12 rules
- test 2021: 9 rules
  - `M2-SL1.5_TP2-2021-000` if -0.3134 <= r_day < -0.02803 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP2
  - `M2-SL1.5_TP2-2021-001` if 1.261 <= atr_rel20 and -3.657 <= d_asia_hi < -1.622 then SHORT SL1.5_TP2
  - `M2-SL1.5_TP2-2021-002` if rv30_rel < 0.7536 and 113 <= bars_since_low then SHORT SL1.5_TP2
  - `M2-SL1.5_TP2-2021-003` if 0.2633 <= pos_day < 0.4671 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP2
  - `M2-SL1.5_TP2-2021-004` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG SL1.5_TP2
  - `M2-SL1.5_TP2-2021-005` if -1.622 <= d_asia_hi < 0.288 and 0.5733 <= d_asia_lo < 2.563 then SHORT SL1.5_TP2
  - `M2-SL1.5_TP2-2021-006` if 2.563 <= d_asia_lo < 4.909 and 7 <= bars_since_high < 24 then SHORT SL1.5_TP2
  - `M2-SL1.5_TP2-2021-007` if -3.516 <= d_open < -0.4054 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP2
  - `M2-SL1.5_TP2-2021-008` if 113 <= bars_since_low and tv_rel < 0.7789 then SHORT SL1.5_TP2
- test 2022: 3 rules
  - `M2-SL1.5_TP2-2022-000` if 0.3796 <= r_day and -17.25 <= d_pdh < -10.67 then SHORT SL1.5_TP2
  - `M2-SL1.5_TP2-2022-001` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT SL1.5_TP2
  - `M2-SL1.5_TP2-2022-002` if 3.57 <= d_pdl < 8.353 and 106 <= bars_since_low then SHORT SL1.5_TP2

### M2_SL1.5_TP3 — 10 rules
- test 2021: 5 rules
  - `M2-SL1.5_TP3-2021-000` if -0.3134 <= r_day < -0.02803 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP3
  - `M2-SL1.5_TP3-2021-001` if atr_rel20 < 0.7414 and 0.4671 <= pos_day < 0.6744 then SHORT SL1.5_TP3
  - `M2-SL1.5_TP3-2021-002` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG SL1.5_TP3
  - `M2-SL1.5_TP3-2021-003` if -1.622 <= d_asia_hi < 0.288 and 0.5733 <= d_asia_lo < 2.563 then SHORT SL1.5_TP3
  - `M2-SL1.5_TP3-2021-004` if -3.516 <= d_open < -0.4054 and 64 <= bars_since_low < 113 then SHORT SL1.5_TP3
- test 2022: 5 rules
  - `M2-SL1.5_TP3-2022-000` if 0.3796 <= r_day and -17.25 <= d_pdh < -10.67 then SHORT SL1.5_TP3
  - `M2-SL1.5_TP3-2022-001` if 0.1388 <= r_day < 0.3796 and weekday < 0.5 then SHORT SL1.5_TP3
  - `M2-SL1.5_TP3-2022-002` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT SL1.5_TP3
  - `M2-SL1.5_TP3-2022-003` if d_asia_hi < -6.509 and 1.418 <= pd_range_rel then LONG SL1.5_TP3
  - `M2-SL1.5_TP3-2022-004` if d_open < -3.436 and 1.418 <= pd_range_rel then LONG SL1.5_TP3

### M2_SL2_TP1 — 11 rules
- test 2021: 9 rules
  - `M2-SL2_TP1-2021-000` if -0.3134 <= r_day < -0.02803 and 64 <= bars_since_low < 113 then SHORT SL2_TP1
  - `M2-SL2_TP1-2021-001` if rv30_rel < 0.7536 and 113 <= bars_since_low then SHORT SL2_TP1
  - `M2-SL2_TP1-2021-002` if 0.921 <= rv30_rel < 1.116 and 64 <= bars_since_low < 113 then SHORT SL2_TP1
  - `M2-SL2_TP1-2021-003` if 0.2633 <= pos_day < 0.4671 and 64 <= bars_since_low < 113 then SHORT SL2_TP1
  - `M2-SL2_TP1-2021-004` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG SL2_TP1
  - `M2-SL2_TP1-2021-005` if -3.516 <= d_open < -0.4054 and 64 <= bars_since_low < 113 then SHORT SL2_TP1
  - `M2-SL2_TP1-2021-006` if 7 <= bars_since_high < 24 and 934 <= min_since_resume then SHORT SL2_TP1
  - `M2-SL2_TP1-2021-007` if 113 <= bars_since_low and tv_rel < 0.7789 then SHORT SL2_TP1
  - `M2-SL2_TP1-2021-008` if 64 <= bars_since_low < 113 and 0.9412 <= spread_rel < 1.059 then SHORT SL2_TP1
- test 2022: 2 rules
  - `M2-SL2_TP1-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT SL2_TP1
  - `M2-SL2_TP1-2022-001` if 3.57 <= d_pdl < 8.353 and 106 <= bars_since_low then SHORT SL2_TP1

### M2_SL0.5 — 4 rules
- test 2021: 0 rules
- test 2022: 4 rules
  - `M2-SL0.5-2022-000` if r_day < -0.2387 and 718 <= min_since_resume < 957 then SHORT SL0.5
  - `M2-SL0.5-2022-001` if r_day < -0.2387 and 3 <= hour_bucket < 4 then SHORT SL0.5
  - `M2-SL0.5-2022-002` if d_pdl < 3.57 and 3 <= hour_bucket < 4 then SHORT SL0.5
  - `M2-SL0.5-2022-003` if d_open < -3.436 and 718 <= min_since_resume < 957 then SHORT SL0.5

### M2_TR1x1 — 2 rules
- test 2021: 1 rules
  - `M2-TR1x1-2021-000` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG TR1x1
- test 2022: 1 rules
  - `M2-TR1x1-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT TR1x1

### M2_TR1x2 — 3 rules
- test 2021: 2 rules
  - `M2-TR1x2-2021-000` if 0.2633 <= pos_day < 0.4671 and 64 <= bars_since_low < 113 then SHORT TR1x2
  - `M2-TR1x2-2021-001` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG TR1x2
- test 2022: 1 rules
  - `M2-TR1x2-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT TR1x2

### M2_TR2x1 — 2 rules
- test 2021: 1 rules
  - `M2-TR2x1-2021-000` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG TR2x1
- test 2022: 1 rules
  - `M2-TR2x1-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT TR2x1

### M2_TR2x2 — 8 rules
- test 2021: 5 rules
  - `M2-TR2x2-2021-000` if -0.3134 <= r_day < -0.02803 and 64 <= bars_since_low < 113 then SHORT TR2x2
  - `M2-TR2x2-2021-001` if 0.2633 <= pos_day < 0.4671 and 64 <= bars_since_low < 113 then SHORT TR2x2
  - `M2-TR2x2-2021-002` if -5.295 <= d_pdh < -0.4686 and 3 <= hour_bucket < 4 then LONG TR2x2
  - `M2-TR2x2-2021-003` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG TR2x2
  - `M2-TR2x2-2021-004` if -3.516 <= d_open < -0.4054 and 64 <= bars_since_low < 113 then SHORT TR2x2
- test 2022: 3 rules
  - `M2-TR2x2-2022-000` if 1.174 <= atr_rel20 and 2.319 <= d_open < 5.823 then LONG TR2x2
  - `M2-TR2x2-2022-001` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT TR2x2
  - `M2-TR2x2-2022-002` if 718 <= min_since_resume < 957 and pd_range_rel < 0.7176 then SHORT TR2x2

### M2_BE1_TP2 — 1 rules
- test 2021: 0 rules
- test 2022: 1 rules
  - `M2-BE1_TP2-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT BE1_TP2

### M2_BE1_TP3 — 3 rules
- test 2021: 2 rules
  - `M2-BE1_TP3-2021-000` if 0.2633 <= pos_day < 0.4671 and 64 <= bars_since_low < 113 then SHORT BE1_TP3
  - `M2-BE1_TP3-2021-001` if 14.29 <= d_pdl < 20.81 and d_asia_lo < 0.5733 then LONG BE1_TP3
- test 2022: 1 rules
  - `M2-BE1_TP3-2022-000` if -1.34 <= d_pdh and 3.57 <= d_pdl < 8.353 then SHORT BE1_TP3

### M3_SL0.5_TP1.5 — 1 rules
- test 2021: 0 rules
- test 2022: 1 rules
  - `M3-SL0.5_TP1.5-2022-000` if 2.5 < hour_bucket and spread_rel <= 0.6583 and d_pdl <= -0.9133 then SHORT SL0.5_TP1.5

### M3_SL0.5_TP2 — 1 rules
- test 2021: 1 rules
  - `M3-SL0.5_TP2-2021-000` if spread_rel <= 0.6583 and -7.988 < d_asia_hi and 4.827 < range60 then LONG SL0.5_TP2
- test 2022: 0 rules

### M3_SL0.5_TP3 — 4 rules
- test 2021: 2 rules
  - `M3-SL0.5_TP3-2021-000` if spread_rel <= 0.4881 and -0.5534 < r_day and d_open <= 6.387 then LONG SL0.5_TP3
  - `M3-SL0.5_TP3-2021-001` if 0.4881 < spread_rel and 1.418 < pd_range_rel and 143.5 < bars_since_high then LONG SL0.5_TP3
- test 2022: 2 rules
  - `M3-SL0.5_TP3-2022-000` if hour_bucket <= 2.5 and 1.288 < atr_rel20 and r_day <= -0.6982 then LONG SL0.5_TP3
  - `M3-SL0.5_TP3-2022-001` if 2.5 < hour_bucket and spread_rel <= 0.6742 and d_pdl <= -0.9133 then SHORT SL0.5_TP3

### M3_SL1_TP1 — 2 rules
- test 2021: 1 rules
  - `M3-SL1_TP1-2021-000` if 0.9972 < rv30_rel and r5 <= -0.9243 and 1.033 < pd_range_rel then LONG SL1_TP1
- test 2022: 1 rules
  - `M3-SL1_TP1-2022-000` if hour_bucket <= 2.5 and r_day <= -0.2609 and 2.18 < rv30_rel then LONG SL1_TP1

### M3_SL1_TP1.5 — 4 rules
- test 2021: 3 rules
  - `M3-SL1_TP1.5-2021-000` if spread_rel <= 0.6056 and d_open <= -5.436 then SHORT SL1_TP1.5
  - `M3-SL1_TP1.5-2021-001` if spread_rel <= 0.6056 and -5.436 < d_open and d_asia_hi <= -5.638 then LONG SL1_TP1.5
  - `M3-SL1_TP1.5-2021-002` if 0.6056 < spread_rel and pos_day <= 0.2073 and 2.5 < weekday then LONG SL1_TP1.5
- test 2022: 1 rules
  - `M3-SL1_TP1.5-2022-000` if 110.5 < min_since_resume and r_day <= -0.7347 and range60 <= 2.265 then LONG SL1_TP1.5

### M3_SL1_TP2 — 7 rules
- test 2021: 4 rules
  - `M3-SL1_TP2-2021-000` if atr_rel20 <= 1.298 and bars_since_low <= 60.5 and 855.5 < min_since_resume then LONG SL1_TP2
  - `M3-SL1_TP2-2021-001` if atr_rel20 <= 1.298 and 60.5 < bars_since_low and r_day <= 0.4281 then SHORT SL1_TP2
  - `M3-SL1_TP2-2021-002` if 1.298 < atr_rel20 and pd_range_rel <= 1.2 and 1.83 < atr_rel20 then SHORT SL1_TP2
  - `M3-SL1_TP2-2021-003` if 1.298 < atr_rel20 and 1.2 < pd_range_rel and d_asia_hi <= -6.172 then LONG SL1_TP2
- test 2022: 3 rules
  - `M3-SL1_TP2-2022-000` if min_since_resume <= 100.5 and 1.598 < atr_rel20 then LONG SL1_TP2
  - `M3-SL1_TP2-2022-001` if 100.5 < min_since_resume and 1.324 < atr_rel20 and pd_range_rel <= 1.178 then SHORT SL1_TP2
  - `M3-SL1_TP2-2022-002` if 100.5 < min_since_resume and 1.324 < atr_rel20 and 1.178 < pd_range_rel then LONG SL1_TP2

### M3_SL1_TP3 — 7 rules
- test 2021: 4 rules
  - `M3-SL1_TP3-2021-000` if pd_ret <= 1.194 and bars_since_low <= 53.5 and pd_ret <= -0.3731 then LONG SL1_TP3
  - `M3-SL1_TP3-2021-001` if pd_ret <= 1.194 and 53.5 < bars_since_low and r_day <= 0.3965 then SHORT SL1_TP3
  - `M3-SL1_TP3-2021-002` if 1.194 < pd_ret and bars_since_high <= 48.5 then SHORT SL1_TP3
  - `M3-SL1_TP3-2021-003` if 1.194 < pd_ret and 48.5 < bars_since_high then LONG SL1_TP3
- test 2022: 3 rules
  - `M3-SL1_TP3-2022-000` if 1.33 < atr_rel20 and pd_range_rel <= 1.224 and pd_ret <= -0.1339 then SHORT SL1_TP3
  - `M3-SL1_TP3-2022-001` if 1.33 < atr_rel20 and 1.224 < pd_range_rel and r_day <= 0.9778 then LONG SL1_TP3
  - `M3-SL1_TP3-2022-002` if 1.33 < atr_rel20 and 1.224 < pd_range_rel and 0.9778 < r_day then SHORT SL1_TP3

### M3_SL1.5_TP1 — 6 rules
- test 2021: 4 rules
  - `M3-SL1.5_TP1-2021-000` if bars_since_high <= 41.5 and atr_rel20 <= 0.6478 and pd_range_rel <= 0.7753 then SHORT SL1.5_TP1
  - `M3-SL1.5_TP1-2021-001` if 41.5 < bars_since_high and bars_since_low <= 45.5 and atr_rel20 <= 1.756 then LONG SL1.5_TP1
  - `M3-SL1.5_TP1-2021-002` if 41.5 < bars_since_high and bars_since_low <= 45.5 and 1.756 < atr_rel20 then SHORT SL1.5_TP1
  - `M3-SL1.5_TP1-2021-003` if 41.5 < bars_since_high and 45.5 < bars_since_low and 1.262 < d_pdh then LONG SL1.5_TP1
- test 2022: 2 rules
  - `M3-SL1.5_TP1-2022-000` if 110.5 < min_since_resume and atr_rel20 <= 0.9914 and r_day <= -0.7165 then LONG SL1.5_TP1
  - `M3-SL1.5_TP1-2022-001` if 110.5 < min_since_resume and 0.9914 < atr_rel20 and 2.704 < rv30_rel then LONG SL1.5_TP1

### M3_SL1.5_TP1.5 — 8 rules
- test 2021: 5 rules
  - `M3-SL1.5_TP1.5-2021-000` if pd_range_rel <= 0.7211 and pd_ret <= 0.2307 and 54.5 < bars_since_low then SHORT SL1.5_TP1.5
  - `M3-SL1.5_TP1.5-2021-001` if pd_range_rel <= 0.7211 and 0.2307 < pd_ret and atr_rel20 <= 1.104 then SHORT SL1.5_TP1.5
  - `M3-SL1.5_TP1.5-2021-002` if pd_range_rel <= 0.7211 and 0.2307 < pd_ret and 1.104 < atr_rel20 then SHORT SL1.5_TP1.5
  - `M3-SL1.5_TP1.5-2021-003` if 0.7211 < pd_range_rel and pos_day <= 0.2188 and 2.5 < weekday then LONG SL1.5_TP1.5
  - `M3-SL1.5_TP1.5-2021-004` if 0.7211 < pd_range_rel and 0.2188 < pos_day and 1.194 < pd_ret then LONG SL1.5_TP1.5
- test 2022: 3 rules
  - `M3-SL1.5_TP1.5-2022-000` if pd_range_rel <= 1.443 and 115.5 < min_since_resume and 0.7576 < pd_ret then SHORT SL1.5_TP1.5
  - `M3-SL1.5_TP1.5-2022-001` if 1.443 < pd_range_rel and r_day <= -1.01 then LONG SL1.5_TP1.5
  - `M3-SL1.5_TP1.5-2022-002` if 1.443 < pd_range_rel and -1.01 < r_day and pd_range_rel <= 1.509 then LONG SL1.5_TP1.5

### M3_SL1.5_TP2 — 6 rules
- test 2021: 4 rules
  - `M3-SL1.5_TP2-2021-000` if pd_ret <= 1.194 and pd_ret <= -0.1922 and -10.29 < d_pdh then LONG SL1.5_TP2
  - `M3-SL1.5_TP2-2021-001` if pd_ret <= 1.194 and -0.1922 < pd_ret and pd_range_rel <= 0.7211 then SHORT SL1.5_TP2
  - `M3-SL1.5_TP2-2021-002` if 1.194 < pd_ret and d_asia_lo <= 8.301 then LONG SL1.5_TP2
  - `M3-SL1.5_TP2-2021-003` if 1.194 < pd_ret and 8.301 < d_asia_lo then SHORT SL1.5_TP2
- test 2022: 2 rules
  - `M3-SL1.5_TP2-2022-000` if 1.443 < pd_range_rel and d_open <= -2.915 and -2.367 < d_asia_lo then LONG SL1.5_TP2
  - `M3-SL1.5_TP2-2022-001` if 1.443 < pd_range_rel and -2.915 < d_open and pd_range_rel <= 1.509 then LONG SL1.5_TP2

### M3_SL1.5_TP3 — 10 rules
- test 2021: 5 rules
  - `M3-SL1.5_TP3-2021-000` if pd_ret <= -0.1922 and d_pdh <= -10.29 and d_open <= -2.71 then LONG SL1.5_TP3
  - `M3-SL1.5_TP3-2021-001` if pd_ret <= -0.1922 and -10.29 < d_pdh and min_since_resume <= 852.5 then LONG SL1.5_TP3
  - `M3-SL1.5_TP3-2021-002` if -0.1922 < pd_ret and pd_ret <= 1.194 and 0.8871 < pd_ret then SHORT SL1.5_TP3
  - `M3-SL1.5_TP3-2021-003` if -0.1922 < pd_ret and 1.194 < pd_ret and d_asia_lo <= 8.301 then LONG SL1.5_TP3
  - `M3-SL1.5_TP3-2021-004` if -0.1922 < pd_ret and 1.194 < pd_ret and 8.301 < d_asia_lo then SHORT SL1.5_TP3
- test 2022: 5 rules
  - `M3-SL1.5_TP3-2022-000` if pd_range_rel <= 1.443 and pd_ret <= 0.7576 and pd_range_rel <= 0.4787 then LONG SL1.5_TP3
  - `M3-SL1.5_TP3-2022-001` if pd_range_rel <= 1.443 and 0.7576 < pd_ret and 0.8241 < d_asia_lo then SHORT SL1.5_TP3
  - `M3-SL1.5_TP3-2022-002` if 1.443 < pd_range_rel and pd_range_rel <= 1.509 and d_pdl <= 16.14 then LONG SL1.5_TP3
  - `M3-SL1.5_TP3-2022-003` if 1.443 < pd_range_rel and pd_range_rel <= 1.509 and 16.14 < d_pdl then LONG SL1.5_TP3
  - `M3-SL1.5_TP3-2022-004` if 1.443 < pd_range_rel and 1.509 < pd_range_rel and d_open <= -2.563 then LONG SL1.5_TP3

### M3_SL2_TP1 — 7 rules
- test 2021: 4 rules
  - `M3-SL2_TP1-2021-000` if pd_range_rel <= 0.6857 and pd_ret <= 0.2275 and 52.5 < bars_since_low then SHORT SL2_TP1
  - `M3-SL2_TP1-2021-001` if pd_range_rel <= 0.6857 and 0.2275 < pd_ret then SHORT SL2_TP1
  - `M3-SL2_TP1-2021-002` if 0.6857 < pd_range_rel and d_asia_lo <= 0.0759 and atr_rel20 <= 1.683 then LONG SL2_TP1
  - `M3-SL2_TP1-2021-003` if 0.6857 < pd_range_rel and d_asia_lo <= 0.0759 and 1.683 < atr_rel20 then SHORT SL2_TP1
- test 2022: 3 rules
  - `M3-SL2_TP1-2022-000` if pd_range_rel <= 1.443 and 95.5 < min_since_resume and 0.7576 < pd_ret then SHORT SL2_TP1
  - `M3-SL2_TP1-2022-001` if 1.443 < pd_range_rel and d_open <= 8.481 and pd_range_rel <= 1.525 then LONG SL2_TP1
  - `M3-SL2_TP1-2022-002` if 1.443 < pd_range_rel and 8.481 < d_open and pos_day <= 0.8005 then SHORT SL2_TP1

### M3_SL2_TP1.5 — 8 rules
- test 2021: 5 rules
  - `M3-SL2_TP1.5-2021-000` if pd_ret <= -0.1922 and d_pdh <= -10.24 and d_open <= -2.11 then LONG SL2_TP1.5
  - `M3-SL2_TP1.5-2021-001` if pd_ret <= -0.1922 and -10.24 < d_pdh and min_since_resume <= 863.5 then LONG SL2_TP1.5
  - `M3-SL2_TP1.5-2021-002` if -0.1922 < pd_ret and pd_range_rel <= 0.7211 and bars_since_low <= 63.5 then SHORT SL2_TP1.5
  - `M3-SL2_TP1.5-2021-003` if -0.1922 < pd_ret and pd_range_rel <= 0.7211 and 63.5 < bars_since_low then SHORT SL2_TP1.5
  - `M3-SL2_TP1.5-2021-004` if -0.1922 < pd_ret and 0.7211 < pd_range_rel and 1.194 < pd_ret then LONG SL2_TP1.5
- test 2022: 3 rules
  - `M3-SL2_TP1.5-2022-000` if pd_range_rel <= 1.443 and 0.7576 < pd_ret and 1.073 < d_asia_lo then SHORT SL2_TP1.5
  - `M3-SL2_TP1.5-2022-001` if 1.443 < pd_range_rel and d_open <= 8.552 and pd_range_rel <= 1.525 then LONG SL2_TP1.5
  - `M3-SL2_TP1.5-2022-002` if 1.443 < pd_range_rel and 8.552 < d_open and bars_since_low <= 158.5 then SHORT SL2_TP1.5

### M3_SL2_TP2 — 10 rules
- test 2021: 5 rules
  - `M3-SL2_TP2-2021-000` if pd_ret <= -0.1922 and d_pdh <= -10.28 and d_open <= -2.597 then LONG SL2_TP2
  - `M3-SL2_TP2-2021-001` if pd_ret <= -0.1922 and -10.28 < d_pdh and min_since_resume <= 833.5 then LONG SL2_TP2
  - `M3-SL2_TP2-2021-002` if -0.1922 < pd_ret and pd_ret <= 1.194 and 0.7576 < pd_ret then SHORT SL2_TP2
  - `M3-SL2_TP2-2021-003` if -0.1922 < pd_ret and 1.194 < pd_ret and d_asia_lo <= 8.322 then LONG SL2_TP2
  - `M3-SL2_TP2-2021-004` if -0.1922 < pd_ret and 1.194 < pd_ret and 8.322 < d_asia_lo then SHORT SL2_TP2
- test 2022: 5 rules
  - `M3-SL2_TP2-2022-000` if pd_range_rel <= 1.406 and pd_ret <= 0.7471 and pd_ret <= -0.6601 then SHORT SL2_TP2
  - `M3-SL2_TP2-2022-001` if pd_range_rel <= 1.406 and 0.7471 < pd_ret and 1.073 < d_asia_lo then SHORT SL2_TP2
  - `M3-SL2_TP2-2022-002` if 1.406 < pd_range_rel and d_open <= -2.511 and d_asia_lo <= -2.097 then SHORT SL2_TP2
  - `M3-SL2_TP2-2022-003` if 1.406 < pd_range_rel and d_open <= -2.511 and -2.097 < d_asia_lo then LONG SL2_TP2
  - `M3-SL2_TP2-2022-004` if 1.406 < pd_range_rel and -2.511 < d_open and pd_range_rel <= 1.509 then LONG SL2_TP2

### M3_SL2_TP3 — 9 rules
- test 2021: 5 rules
  - `M3-SL2_TP3-2021-000` if pd_ret <= -0.1922 and d_pdh <= -10.48 and d_open <= -2.707 then LONG SL2_TP3
  - `M3-SL2_TP3-2021-001` if pd_ret <= -0.1922 and -10.48 < d_pdh and min_since_resume <= 833.5 then LONG SL2_TP3
  - `M3-SL2_TP3-2021-002` if -0.1922 < pd_ret and pd_ret <= 1.194 and min_since_resume <= 671.5 then SHORT SL2_TP3
  - `M3-SL2_TP3-2021-003` if -0.1922 < pd_ret and 1.194 < pd_ret and d_asia_lo <= 8.322 then LONG SL2_TP3
  - `M3-SL2_TP3-2021-004` if -0.1922 < pd_ret and 1.194 < pd_ret and 8.322 < d_asia_lo then SHORT SL2_TP3
- test 2022: 4 rules
  - `M3-SL2_TP3-2022-000` if pd_range_rel <= 1.406 and pd_range_rel <= 1.12 and pd_range_rel <= 0.4787 then LONG SL2_TP3
  - `M3-SL2_TP3-2022-001` if 1.406 < pd_range_rel and r_day <= 0.8522 and pd_range_rel <= 1.509 then LONG SL2_TP3
  - `M3-SL2_TP3-2022-002` if 1.406 < pd_range_rel and 0.8522 < r_day and min_since_resume <= 746.5 then SHORT SL2_TP3
  - `M3-SL2_TP3-2022-003` if 1.406 < pd_range_rel and 0.8522 < r_day and 746.5 < min_since_resume then SHORT SL2_TP3

### M3_SL0.5 — 8 rules
- test 2021: 5 rules
  - `M3-SL0.5-2021-000` if pd_ret <= -0.05556 and pd_ret <= -0.5915 and d_pdl <= 2.466 then LONG SL0.5
  - `M3-SL0.5-2021-001` if pd_ret <= -0.05556 and -0.5915 < pd_ret and pd_ret <= -0.3731 then LONG SL0.5
  - `M3-SL0.5-2021-002` if pd_ret <= -0.05556 and -0.5915 < pd_ret and -0.3731 < pd_ret then LONG SL0.5
  - `M3-SL0.5-2021-003` if -0.05556 < pd_ret and pd_ret <= 1.194 and 7.389 < r240 then LONG SL0.5
  - `M3-SL0.5-2021-004` if -0.05556 < pd_ret and 1.194 < pd_ret and pos_day <= 0.5668 then LONG SL0.5
- test 2022: 3 rules
  - `M3-SL0.5-2022-000` if d_pdh <= -12.25 and d_open <= -3.774 and pd_ret <= -0.9796 then LONG SL0.5
  - `M3-SL0.5-2022-001` if d_pdh <= -12.25 and d_open <= -3.774 and -0.9796 < pd_ret then SHORT SL0.5
  - `M3-SL0.5-2022-002` if -12.25 < d_pdh and pd_ret <= -0.01776 and weekday <= 3.5 then LONG SL0.5

### M3_SL1 — 11 rules
- test 2021: 6 rules
  - `M3-SL1-2021-000` if pd_ret <= -0.05556 and pd_ret <= -0.5915 and d_pdl <= 3.683 then LONG SL1
  - `M3-SL1-2021-001` if pd_ret <= -0.05556 and -0.5915 < pd_ret and pd_ret <= -0.3731 then LONG SL1
  - `M3-SL1-2021-002` if pd_ret <= -0.05556 and -0.5915 < pd_ret and -0.3731 < pd_ret then LONG SL1
  - `M3-SL1-2021-003` if -0.05556 < pd_ret and pd_ret <= 1.194 and d_pdh <= 0.6179 then SHORT SL1
  - `M3-SL1-2021-004` if -0.05556 < pd_ret and pd_ret <= 1.194 and 0.6179 < d_pdh then LONG SL1
  - `M3-SL1-2021-005` if -0.05556 < pd_ret and 1.194 < pd_ret and pos_day <= 0.621 then LONG SL1
- test 2022: 5 rules
  - `M3-SL1-2022-000` if pd_ret <= -0.5711 and d_pdl <= 4.389 and pd_ret <= -0.9465 then LONG SL1
  - `M3-SL1-2022-001` if pd_ret <= -0.5711 and 4.389 < d_pdl and d_pdh <= -11.31 then SHORT SL1
  - `M3-SL1-2022-002` if -0.5711 < pd_ret and pd_ret <= -0.3777 and pd_ret <= -0.416 then LONG SL1
  - `M3-SL1-2022-003` if -0.5711 < pd_ret and pd_ret <= -0.3777 and -0.416 < pd_ret then LONG SL1
  - `M3-SL1-2022-004` if -0.5711 < pd_ret and -0.3777 < pd_ret and 1.453 < pd_range_rel then LONG SL1

### M3_SL2 — 12 rules
- test 2021: 7 rules
  - `M3-SL2-2021-000` if pd_range_rel <= 0.7211 and min_since_resume <= 841.5 and weekday <= 0.5 then SHORT SL2
  - `M3-SL2-2021-001` if pd_range_rel <= 0.7211 and min_since_resume <= 841.5 and 0.5 < weekday then SHORT SL2
  - `M3-SL2-2021-002` if pd_range_rel <= 0.7211 and 841.5 < min_since_resume and bars_since_low <= 41.5 then LONG SL2
  - `M3-SL2-2021-003` if pd_range_rel <= 0.7211 and 841.5 < min_since_resume and 41.5 < bars_since_low then SHORT SL2
  - `M3-SL2-2021-004` if 0.7211 < pd_range_rel and pd_range_rel <= 0.867 and pd_range_rel <= 0.817 then LONG SL2
  - `M3-SL2-2021-005` if 0.7211 < pd_range_rel and pd_range_rel <= 0.867 and 0.817 < pd_range_rel then LONG SL2
  - `M3-SL2-2021-006` if 0.7211 < pd_range_rel and 0.867 < pd_range_rel and -0.5915 < pd_ret then LONG SL2
- test 2022: 5 rules
  - `M3-SL2-2022-000` if pd_ret <= 1.154 and pd_ret <= -0.01776 and d_pdh <= -11.25 then SHORT SL2
  - `M3-SL2-2022-001` if pd_ret <= 1.154 and pd_ret <= -0.01776 and -11.25 < d_pdh then LONG SL2
  - `M3-SL2-2022-002` if pd_ret <= 1.154 and -0.01776 < pd_ret and 3.794 < d_open then SHORT SL2
  - `M3-SL2-2022-003` if 1.154 < pd_ret and d_asia_hi <= -2.553 and pd_range_rel <= 1.75 then LONG SL2
  - `M3-SL2-2022-004` if 1.154 < pd_ret and d_asia_hi <= -2.553 and 1.75 < pd_range_rel then LONG SL2

### M3_TR1x1 — 5 rules
- test 2021: 3 rules
  - `M3-TR1x1-2021-000` if pd_range_rel <= 2.202 and 1.265 < pd_ret then LONG TR1x1
  - `M3-TR1x1-2021-001` if 2.202 < pd_range_rel and d_pdl <= 12.38 then LONG TR1x1
  - `M3-TR1x1-2021-002` if 2.202 < pd_range_rel and 12.38 < d_pdl then SHORT TR1x1
- test 2022: 2 rules
  - `M3-TR1x1-2022-000` if 1.111 < atr_rel20 and pd_ret <= 1.42 and pd_ret <= -2.034 then LONG TR1x1
  - `M3-TR1x1-2022-001` if 1.111 < atr_rel20 and 1.42 < pd_ret then LONG TR1x1

### M3_TR1x2 — 7 rules
- test 2021: 3 rules
  - `M3-TR1x2-2021-000` if pd_ret <= 1.194 and bars_since_low <= 43.5 and pd_ret <= -0.3731 then LONG TR1x2
  - `M3-TR1x2-2021-001` if 1.194 < pd_ret and d_asia_lo <= 8.036 then LONG TR1x2
  - `M3-TR1x2-2021-002` if 1.194 < pd_ret and 8.036 < d_asia_lo then SHORT TR1x2
- test 2022: 4 rules
  - `M3-TR1x2-2022-000` if atr_rel20 <= 1.33 and 92.5 < min_since_resume and pd_range_rel <= 0.4201 then LONG TR1x2
  - `M3-TR1x2-2022-001` if 1.33 < atr_rel20 and pd_ret <= 0.2669 and pd_ret <= -1.909 then LONG TR1x2
  - `M3-TR1x2-2022-002` if 1.33 < atr_rel20 and 0.2669 < pd_ret and d_asia_hi <= 2.011 then LONG TR1x2
  - `M3-TR1x2-2022-003` if 1.33 < atr_rel20 and 0.2669 < pd_ret and 2.011 < d_asia_hi then SHORT TR1x2

### M3_TR2x1 — 4 rules
- test 2021: 3 rules
  - `M3-TR2x1-2021-000` if pd_ret <= 1.194 and hour_bucket <= 2.5 and r_day <= -0.7043 then LONG TR2x1
  - `M3-TR2x1-2021-001` if 1.194 < pd_ret and bars_since_high <= 48.5 then SHORT TR2x1
  - `M3-TR2x1-2021-002` if 1.194 < pd_ret and 48.5 < bars_since_high then LONG TR2x1
- test 2022: 1 rules
  - `M3-TR2x1-2022-000` if min_since_resume <= 138.5 and 1.275 < atr_rel20 and 1.532 < pd_range_rel then LONG TR2x1

### M3_TR2x2 — 7 rules
- test 2021: 5 rules
  - `M3-TR2x2-2021-000` if bars_since_low <= 43.5 and pd_range_rel <= 0.5763 then LONG TR2x2
  - `M3-TR2x2-2021-001` if bars_since_low <= 43.5 and 0.5763 < pd_range_rel and pd_ret <= -0.3731 then LONG TR2x2
  - `M3-TR2x2-2021-002` if 43.5 < bars_since_low and d_pdh <= -1.03 and atr_rel20 <= 1.294 then SHORT TR2x2
  - `M3-TR2x2-2021-003` if 43.5 < bars_since_low and d_pdh <= -1.03 and 1.294 < atr_rel20 then LONG TR2x2
  - `M3-TR2x2-2021-004` if 43.5 < bars_since_low and -1.03 < d_pdh and d_pdl <= 24.28 then LONG TR2x2
- test 2022: 2 rules
  - `M3-TR2x2-2022-000` if d_pdl <= 30.99 and 1.456 < pd_range_rel and min_since_resume <= 511.5 then LONG TR2x2
  - `M3-TR2x2-2022-001` if 30.99 < d_pdl and 1.134 < pd_ret and 19.5 < bars_since_high then LONG TR2x2

### M3_BE1_TP2 — 3 rules
- test 2021: 2 rules
  - `M3-BE1_TP2-2021-000` if 2.202 < pd_range_rel and d_pdl <= 12.61 then LONG BE1_TP2
  - `M3-BE1_TP2-2021-001` if 2.202 < pd_range_rel and 12.61 < d_pdl then SHORT BE1_TP2
- test 2022: 1 rules
  - `M3-BE1_TP2-2022-000` if r_day <= -0.256 and 2.254 < pd_range_rel then LONG BE1_TP2

### M3_BE1_TP3 — 5 rules
- test 2021: 3 rules
  - `M3-BE1_TP3-2021-000` if pd_ret <= 1.194 and bars_since_low <= 45.5 and 940.5 < min_since_resume then LONG BE1_TP3
  - `M3-BE1_TP3-2021-001` if 1.194 < pd_ret and bars_since_high <= 48.5 then SHORT BE1_TP3
  - `M3-BE1_TP3-2021-002` if 1.194 < pd_ret and 48.5 < bars_since_high then LONG BE1_TP3
- test 2022: 2 rules
  - `M3-BE1_TP3-2022-000` if 1.331 < atr_rel20 and pd_ret <= -1.909 then LONG BE1_TP3
  - `M3-BE1_TP3-2022-001` if 1.331 < atr_rel20 and -1.909 < pd_ret and pd_ret <= -0.1092 then SHORT BE1_TP3

### M3_BE2_TP2 — 9 rules
- test 2021: 4 rules
  - `M3-BE2_TP2-2021-000` if pd_ret <= 1.194 and pd_ret <= -0.1922 and -10.45 < d_pdh then LONG BE2_TP2
  - `M3-BE2_TP2-2021-001` if pd_ret <= 1.194 and -0.1922 < pd_ret and 0.7576 < pd_ret then SHORT BE2_TP2
  - `M3-BE2_TP2-2021-002` if 1.194 < pd_ret and d_asia_lo <= 8.272 then LONG BE2_TP2
  - `M3-BE2_TP2-2021-003` if 1.194 < pd_ret and 8.272 < d_asia_lo then SHORT BE2_TP2
- test 2022: 5 rules
  - `M3-BE2_TP2-2022-000` if pd_range_rel <= 1.443 and pd_ret <= 0.7576 and pd_ret <= -0.7274 then SHORT BE2_TP2
  - `M3-BE2_TP2-2022-001` if pd_range_rel <= 1.443 and 0.7576 < pd_ret and 1.088 < d_asia_lo then SHORT BE2_TP2
  - `M3-BE2_TP2-2022-002` if 1.443 < pd_range_rel and d_open <= 8.481 and pd_range_rel <= 1.525 then LONG BE2_TP2
  - `M3-BE2_TP2-2022-003` if 1.443 < pd_range_rel and 8.481 < d_open and d_pdl <= 21 then SHORT BE2_TP2
  - `M3-BE2_TP2-2022-004` if 1.443 < pd_range_rel and 8.481 < d_open and 21 < d_pdl then SHORT BE2_TP2

### M3_BE2_TP3 — 10 rules
- test 2021: 4 rules
  - `M3-BE2_TP3-2021-000` if pd_ret <= 1.194 and pd_ret <= -0.1922 and -0.2303 < pd_ret then LONG BE2_TP3
  - `M3-BE2_TP3-2021-001` if pd_ret <= 1.194 and -0.1922 < pd_ret and 24.55 < d_pdl then SHORT BE2_TP3
  - `M3-BE2_TP3-2021-002` if 1.194 < pd_ret and d_asia_lo <= 8.272 then LONG BE2_TP3
  - `M3-BE2_TP3-2021-003` if 1.194 < pd_ret and 8.272 < d_asia_lo then SHORT BE2_TP3
- test 2022: 6 rules
  - `M3-BE2_TP3-2022-000` if pd_range_rel <= 1.621 and d_pdl <= 24.65 and pd_range_rel <= 0.4787 then LONG BE2_TP3
  - `M3-BE2_TP3-2022-001` if pd_range_rel <= 1.621 and 24.65 < d_pdl and weekday <= 2.5 then SHORT BE2_TP3
  - `M3-BE2_TP3-2022-002` if 1.621 < pd_range_rel and min_since_resume <= 450.5 and pd_range_rel <= 1.734 then LONG BE2_TP3
  - `M3-BE2_TP3-2022-003` if 1.621 < pd_range_rel and min_since_resume <= 450.5 and 1.734 < pd_range_rel then LONG BE2_TP3
  - `M3-BE2_TP3-2022-004` if 1.621 < pd_range_rel and 450.5 < min_since_resume and d_pdh <= -11.19 then SHORT BE2_TP3
  - `M3-BE2_TP3-2022-005` if 1.621 < pd_range_rel and 450.5 < min_since_resume and -11.19 < d_pdh then LONG BE2_TP3

## Completion record

```
F3 — COMPLETE
Date: 2026-09-30
Data: rows 884546, days 645, quarantined 4
Tests: 87 passed in 334.4s (pytest -q, python/tests)
Result: F3_STOP
  best 10 by mean net R (one position at a time):
  M2    SL2_TP3: trades  2717  mean  -0.045 R  2021 -0.041  2022 -0.048  boot_low -0.091  p 1.000
  M3    SL2_TP1: trades  2244  mean  -0.051 R  2021 -0.048  2022 -0.075  boot_low -0.083  p 1.000
  M2    SL2_TP1: trades  2378  mean  -0.064 R  2021 -0.064  2022 -0.064  boot_low -0.092  p 1.000
  M3      TR2x1: trades   518  mean  -0.069 R  2021 -0.055  2022 -0.112  boot_low -0.097  p 1.000
  M1        SL2: trades   110  mean  -0.072 R  2021 —  2022 -0.072  boot_low -0.443  p 1.000
  M1      SL1.5: trades   144  mean  -0.074 R  2021 —  2022 -0.074  boot_low -0.442  p 1.000
  M3    BE2_TP2: trades  1378  mean  -0.080 R  2021 -0.110  2022 -0.027  boot_low -0.120  p 1.000
  M3  SL2_TP1.5: trades  1847  mean  -0.089 R  2021 -0.098  2022 -0.022  boot_low -0.131  p 1.000
  M3    BE2_TP3: trades  1504  mean  -0.089 R  2021 -0.101  2022 -0.076  boot_low -0.131  p 1.000
  M2      TR2x2: trades  1673  mean  -0.090 R  2021 -0.125  2022 -0.032  boot_low -0.128  p 1.000
```
