"""Descriptive note on M3 EOD (owner request after the F1 verdict; the verdict does not change).

Recomputes the *real* walk-forward pass with the frozen config (deterministic, same
fingerprint as research/f1/report.json), checks that M3 EOD matches the report exactly, then
writes long/short shares, a comparison with B0 "always long" / "always short" in the same
test years, and 10 random example charts. No parameter is changed, no permutation is run and
nothing is appended to trials_ledger.jsonl: this is not a new trial.

Run from python/:  python ../research/f1/m3_eod/m3_eod_note.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "python"))
from edgelab.config import DEFAULT  # noqa: E402
from edgelab.data import day_to_date, load_f1, year_of_day  # noqa: E402
from edgelab.models import run_walkforward  # noqa: E402
from edgelab.report import _fmt_t, prepare, svg_chart  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
cfg = DEFAULT
rep = json.loads((ROOT / "research/f1/report.json").read_text())
assert rep["config_fingerprint"] == cfg.fingerprint()

df, spec, _ = load_f1(ROOT / "data", cfg.years)
prep = prepare(df, spec, cfg)
ds, bars = prep.ds, prep.bars
real = run_walkforward(ds, cfg)
r = real[("M3", "EOD")]
row = next(x for x in rep["configurations"] if x["family"] == "M3" and x["horizon"] == "EOD")
assert len(r["rows"]) == row["trades"] and np.isclose(r["net_usd"].mean(), row["mean_usd"]), "not the reported run"

yr = year_of_day(ds.day)
out = {"config_fingerprint": cfg.fingerprint(), "per_year": {}, "rules": {}}
for _, ty in cfg.folds:
    elig = (yr == ty) & np.isfinite(ds.y["long_EOD"])
    m = yr[r["rows"]] == ty
    d, net = r["dir"][m], r["net_usd"][m]
    days_t = ds.day[r["rows"][m]]
    # direction per day (the EOD tree splits only on features that barely change inside a day)
    day_dir = {}
    for dd, di in zip(days_t, d):
        day_dir.setdefault(int(dd), set()).add(int(di))
    out["per_year"][str(ty)] = {
        "eligible_moments": int(elig.sum()), "trades": int(m.sum()),
        "long_share": float((d > 0).mean()), "short_share": float((d < 0).mean()),
        "days": len(day_dir), "days_all_long": sum(v == {1} for v in day_dir.values()),
        "days_all_short": sum(v == {-1} for v in day_dir.values()),
        "days_mixed": sum(len(v) > 1 for v in day_dir.values()),
        "m3_mean_usd": float(net.mean()),
        "m3_long_trades_mean_usd": float(net[d > 0].mean()) if (d > 0).any() else None,
        "m3_short_trades_mean_usd": float(net[d < 0].mean()) if (d < 0).any() else None,
        "b0_long_mean_usd": float(ds.y["long_EOD"][elig].mean()),
        "b0_short_mean_usd": float(ds.y["short_EOD"][elig].mean()),
    }
allm = np.isin(yr, [ty for _, ty in cfg.folds]) & np.isfinite(ds.y["long_EOD"])
out["both_years"] = {"m3_mean_usd": float(r["net_usd"].mean()),
                     "long_share": float((r["dir"] > 0).mean()),
                     "b0_long_mean_usd": float(ds.y["long_EOD"][allm].mean()),
                     "b0_short_mean_usd": float(ds.y["short_EOD"][allm].mean())}
for rule, idx in r["rule_hits"]:
    out["rules"][rule.rid] = {"text": rule.text(), "train_moments": rule.train.get("n"),
                              "train_days": rule.train.get("days"),
                              "train_mean_long_usd": rule.train.get("mean_long_usd"),
                              "train_mean_short_usd": rule.train.get("mean_short_usd"),
                              "test_trades": int(len(idx)),
                              "test_days": int(len(np.unique(ds.day[r["rows"][idx]]))) if len(idx) else 0,
                              "test_mean_usd": float(r["net_usd"][idx].mean()) if len(idx) else None}

# 10 random example trades (fixed seed), charts M5 +-4 h like the main report
rng = np.random.default_rng([cfg.seed, 4])
pick = np.sort(rng.choice(len(r["rows"]), size=10, replace=False))
rule_of = {}
for rule, idx in r["rule_hits"]:
    for i in idx:
        rule_of[int(i)] = rule.rid
cdir = OUT / "charts"
cdir.mkdir(exist_ok=True)
out["examples"] = []
for n, ti in enumerate(pick):
    drow = r["rows"][ti]
    t = int(ds.t[drow])
    t_exit = int(ds.y["exit_t_EOD"][drow])
    side = "LONG" if r["dir"][ti] > 0 else "SHORT"
    title = f"M3 EOD {side} | {rule_of.get(int(ti), '?')} | {_fmt_t(t)} | net {r['net_usd'][ti]:+.2f} USD"
    fn = cdir / f"ex_{n + 1:02d}.svg"
    fn.write_text(svg_chart(bars, t, t_exit, title, cfg.chart_half_window_min), encoding="utf-8")
    out["examples"].append({"file": f"charts/{fn.name}", "time": _fmt_t(t), "exit": _fmt_t(t_exit),
                            "side": side, "rule": rule_of.get(int(ti)), "net_usd": float(r["net_usd"][ti]),
                            "date": day_to_date(ds.day[drow])})
(OUT / "m3_eod.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
