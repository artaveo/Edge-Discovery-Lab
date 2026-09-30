"""Phase F2: one-shot test of the two frozen hypotheses on 2023-2024 (EdgeLab_Roadmap.md, Section 11).

Usage (F2 Step C, from ``python/``), exactly once::

    python -m edgelab.f2 --f1-data ../data --f2-data ../data/f2 --out ../research/f2

* Data: ``data/f2/xauusd_m1_{2023,2024}.csv.gz`` (+ manifest, ``"phase": "F2"``). The F1 file
  of 2022 is read only as feature history; no 2022 moment is scored. Nothing dated 2025 or
  later is ever read.
* Window, targets, costs and features: the F1 code and config, unchanged
  (``report.prepare``, fingerprint checked against the pre-registration).
* H1 = the frozen fold-2 M3-EOD tree (rules from ``research/f2/prereg/h1_m3_eod_tree.json``),
  H2 = the previous-day range rule (``h2_range_rule.json``). Both files must match the
  SHA-256 written in the roadmap before anything is loaded.
* One shot: the run refuses to start when ``<out>/report.json`` already exists.

Pre-registered details not spelled out in Section 11 (fixed here before the data is loaded):
* H2 entry = the day's first decision moment (first M5 close >= ResumeTime). If that moment
  has no finite ``pd_range_rel`` or no valid EOD target, the day is not eligible (no later
  moment is tried).
* Bootstrap and p: one resample set per hypothesis, ``default_rng(20260930)``, 10,000 draws of
  whole trade days; lower bound = 5% quantile of the resampled means; p = share of the
  resampled means <= 0.
* Charts (descriptive only): M5 candles from 4 h before the entry until at least the exit,
  i.e. half-window = max(240 min, exit - entry + 30 min), centred on the entry.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DEFAULT, F1Config
from .data import DataDisciplineError, InstrumentSpec, read_year_csv, sha256_file, spec_from_manifest, year_file, year_of_day
from .models import Cond, Rule, rules_direction
from .report import _fmt_t, prepare, svg_chart
from .stats import holm

F2_YEARS = (2023, 2024)
F2_START = "2023-01-01"
F2_FIRST_FORBIDDEN_YEAR = 2025
HISTORY_YEAR = 2022                 # F1 year read as feature history only
F1_FINGERPRINT = "7e945e717983b088"
SEED = 20260930
N_BOOT = 10000
ALPHA = 0.05
N_EXAMPLES = 10

ROOT = Path(__file__).resolve().parents[2]
PREREG = ROOT / "research" / "f2" / "prereg"
PREREG_SHA256 = {                   # EdgeLab_Roadmap.md Section 11.2 / 11.3
    "h1_m3_eod_tree.json": "9d6f7f24d250452e959a3a1a70a01f60d05ecd1461c4c5145775cab3ebdf64f3",
    "h1_m3_eod_tree.pkl": "b91630b68baac8fc9cf38dbb86a4ac4c9ecc6b5ffc5879de4045854ac109b0f9",
    "h2_range_rule.json": "e266849a75741e8b286f8a7d9e02e4e39cfd0f4460667abd24c2372c60a83015",
}


# ----------------------------------------------------------------------------- frozen files

def check_prereg(prereg_dir: Path = PREREG) -> None:
    for name, want in PREREG_SHA256.items():
        got = hashlib.sha256((Path(prereg_dir) / name).read_bytes()).hexdigest()
        if got != want:
            raise RuntimeError(f"{name} differs from the pre-registration ({got} != {want})")


def load_hypotheses(prereg_dir: Path = PREREG):
    h1 = json.loads((Path(prereg_dir) / "h1_m3_eod_tree.json").read_text(encoding="utf-8"))
    h2 = json.loads((Path(prereg_dir) / "h2_range_rule.json").read_text(encoding="utf-8"))
    rules = []
    for r in h1["rules"]:
        conds = [Cond(c["feature"], -np.inf if c["lo"] is None else c["lo"],
                      np.inf if c["hi"] is None else c["hi"], c["lo_closed"], c["hi_closed"])
                 for c in r["conditions"]]
        rule = Rule("M3", "EOD", 1 if r["direction"] == "long" else -1, conds, r["train"])
        rule.rid = r["id"]
        rules.append(rule)
    return rules, (float(h2["thresholds"]["small_max"]), float(h2["thresholds"]["medium_max"]))


# ----------------------------------------------------------------------------- data

def load_f2(f1_dir: Path, f2_dir: Path):
    """F1 2022 (history) + F2 2023-2024, both checked against their manifests.
    Returns (DataFrame, InstrumentSpec, F2 manifest)."""
    f1_dir, f2_dir = Path(f1_dir), Path(f2_dir)
    man2 = json.loads((f2_dir / "manifest.json").read_text(encoding="utf-8"))
    if str(man2.get("phase", "")).upper() != "F2":
        raise DataDisciplineError("the F2 manifest must say \"phase\": \"F2\"")
    years2 = sorted(int(f["year"]) for f in man2.get("files", []))
    if years2 != list(F2_YEARS):
        raise DataDisciplineError(f"F2 manifest years {years2} != {list(F2_YEARS)}")
    for p in f2_dir.parent.rglob("*.csv*"):
        m = re.search(r"(\d{4})\.csv", p.name)
        if m and int(m.group(1)) >= F2_FIRST_FORBIDDEN_YEAR:
            raise DataDisciplineError(f"{p}: 2025 and later are locked")
    man1 = json.loads((f1_dir / "manifest.json").read_text(encoding="utf-8"))
    frames = []
    for man, d, y in [(man1, f1_dir, HISTORY_YEAR)] + [(man2, f2_dir, y) for y in F2_YEARS]:
        entry = {int(f["year"]): f for f in man["files"]}[y]
        path = year_file(d, y)
        if sha256_file(path).lower() != str(entry["sha256"]).lower():
            raise ValueError(f"{path.name}: sha256 differs from its manifest")
        df = read_year_csv(path)
        if len(df) != int(entry["rows"]):
            raise ValueError(f"{path.name}: {len(df)} rows != manifest {entry['rows']}")
        yrs = pd.DatetimeIndex(df["time"]).year
        if len(df) and (yrs.min() != y or yrs.max() != y):
            raise DataDisciplineError(f"{path.name}: bars outside {y}")
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    t = pd.DatetimeIndex(df["time"])
    if int(t.year.max()) >= F2_FIRST_FORBIDDEN_YEAR:
        raise DataDisciplineError("data contains bars dated 2025 or later")
    s1, s2 = spec_from_manifest(man1), spec_from_manifest(man2)
    if (s1.point, s1.digits) != (s2.point, s2.digits):
        raise ValueError(f"symbol spec changed between F1 and F2: {s1} vs {s2}")
    return df, s2, man2


# ----------------------------------------------------------------------------- hypotheses

def h1_trades(prep, rules):
    """Every scored moment with complete features and a valid EOD target, in its leaf's direction."""
    ds = prep.ds
    yr = year_of_day(ds.day)
    m = np.isin(yr, F2_YEARS) & np.isfinite(ds.y["long_EOD"]) & np.isfinite(ds.y["short_EOD"])
    rows = np.flatnonzero(m)
    d, _ = rules_direction(rules, {f: v[rows] for f, v in ds.X.items()}, len(rows))
    return _trades(prep, rows, d)


def h2_trades(prep, cuts):
    """One trade per eligible day at its first decision moment. Rows index ``prep.T_all``."""
    lo, hi = cuts
    A = prep_all(prep)
    yr = year_of_day(A["day"])
    first = np.r_[True, A["day"][1:] != A["day"][:-1]]          # moments are in time order
    m = first & np.isin(yr, F2_YEARS) & np.isfinite(A["pd_range_rel"]) & \
        np.isfinite(A["long_EOD"]) & np.isfinite(A["short_EOD"])
    rows = np.flatnonzero(m)
    x = A["pd_range_rel"][rows]
    d = np.where(x <= lo, 0, np.where(x <= hi, 1, -1))
    return _trades_all(A, rows, d)


def prep_all(prep):
    """Feature and target arrays for *all* decision moments (not only complete-feature rows)."""
    if getattr(prep, "_all", None) is None:
        from .features import compute_features
        from .targets import compute_targets
        from .window import decision_moments, resume_times
        bars, cfg = prep.bars, prep.cfg
        resume = resume_times(bars, cfg)
        moments = decision_moments(bars, resume, prep.audit["excluded_days"], cfg)
        F = compute_features(bars, resume, moments, prep.atr5, cfg)
        T = compute_targets(bars, moments, prep.atr5, cfg)
        prep._all = {"day": bars.day5[moments], "t": bars.tc5[moments],
                     "pd_range_rel": F["pd_range_rel"].to_numpy(float),
                     **{k: np.asarray(T[k]) for k in ("long_EOD", "short_EOD", "long_atr_EOD",
                                                     "short_atr_EOD", "exit_t_EOD")}}
    return prep._all


def _trades(prep, rows, d):
    ds = prep.ds
    A = {"day": ds.day, "t": ds.t, **{k: ds.y[k] for k in ("long_EOD", "short_EOD", "long_atr_EOD",
                                                        "short_atr_EOD", "exit_t_EOD")}}
    return _trades_all(A, rows, d)


def _trades_all(A, rows, d):
    """Pool of eligible rows with direction d (0 = no trade)."""
    return {
        "day": A["day"][rows], "t": A["t"][rows], "dir": d, "exit_t": A["exit_t_EOD"][rows],
        "long": A["long_EOD"][rows], "short": A["short_EOD"][rows],
        "long_atr": A["long_atr_EOD"][rows], "short_atr": A["short_atr_EOD"][rows],
    }


# ----------------------------------------------------------------------------- statistics

def _mean(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    return float(v.mean()) if len(v) else float("nan")


def boot(values, days, n_boot=N_BOOT, seed=SEED, alpha=ALPHA):
    """Day-block bootstrap: (lower 1-alpha bound, p = share of resampled means <= 0)."""
    values = np.asarray(values, float)
    if len(values) == 0:
        return float("nan"), 1.0
    ud, inv = np.unique(np.asarray(days), return_inverse=True)
    s = np.bincount(inv, weights=values, minlength=len(ud))
    c = np.bincount(inv, minlength=len(ud)).astype(float)
    idx = np.random.default_rng(seed).integers(0, len(ud), size=(n_boot, len(ud)))
    bm = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    return float(np.quantile(bm, alpha)), float(np.mean(bm <= 0))


def evaluate(pool: dict, name: str) -> dict:
    """Per-year and pooled results of one hypothesis plus its B0 baselines on the same pool."""
    tr = pool["dir"] != 0
    net = np.where(pool["dir"] > 0, pool["long"], pool["short"])
    net_atr = np.where(pool["dir"] > 0, pool["long_atr"], pool["short_atr"])
    yr = year_of_day(pool["day"])
    out = {"hypothesis": name, "per_year": {}}
    for y in F2_YEARS:
        m, ym = tr & (yr == y), yr == y
        out["per_year"][str(y)] = {
            "trades": int(m.sum()), "days": int(len(np.unique(pool["day"][m]))),
            "mean_usd": _mean(net[m]), "mean_atr": _mean(net_atr[m]),
            "win_rate": float(np.mean(net[m] > 0)) if m.any() else float("nan"),
            "long_share": float(np.mean(pool["dir"][m] > 0)) if m.any() else float("nan"),
            "eligible": int(ym.sum()),
            "b0_long_usd": _mean(pool["long"][ym]), "b0_short_usd": _mean(pool["short"][ym]),
        }
    lower, p = boot(net[tr], pool["day"][tr])
    out.update({"trades": int(tr.sum()), "days": int(len(np.unique(pool["day"][tr]))),
                "mean_usd": _mean(net[tr]), "mean_atr": _mean(net_atr[tr]),
                "win_rate": float(np.mean(net[tr] > 0)) if tr.any() else float("nan"),
                "boot_lower_usd": lower, "p_boot": p})
    py = out["per_year"].values()
    out["checks"] = {
        "positive_each_year": all(v["trades"] > 0 and v["mean_usd"] > 0 for v in py),
        "boot_lower_positive": bool(np.isfinite(lower) and lower > 0),
        "beats_b0_each_year": all(v["trades"] > 0 and v["mean_usd"] > v["b0_long_usd"]
                                  and v["mean_usd"] > v["b0_short_usd"] for v in py),
    }
    return out


def verdict(results: list) -> str:
    adj, rej = holm([r["p_boot"] for r in results], ALPHA)
    for r, a, ok in zip(results, adj, rej):
        r["p_holm"] = float(a)
        r["checks"]["holm"] = bool(ok)
        r["passes"] = all(r["checks"].values())
    return "F2_PASS" if any(r["passes"] for r in results) else "F2_FAIL"


# ----------------------------------------------------------------------------- run

def run(df: pd.DataFrame, spec: InstrumentSpec, cfg: F1Config = DEFAULT, prereg_dir: Path = PREREG,
        check_fingerprint: bool = True) -> dict:
    check_prereg(prereg_dir)
    if check_fingerprint and cfg.fingerprint() != F1_FINGERPRINT:
        raise RuntimeError("the F1 config changed; F2 must use the frozen F1 config")
    rules, cuts = load_hypotheses(prereg_dir)
    prep = prepare(df, spec, cfg)
    prep.cfg, prep._all = cfg, None
    pools = {"H1": h1_trades(prep, rules), "H2": h2_trades(prep, cuts)}
    results = [evaluate(pools["H1"], "H1"), evaluate(pools["H2"], "H2")]
    v = verdict(results)
    return {"verdict": v, "results": results, "pools": pools, "prep": prep, "cuts": cuts}


def write_report(res: dict, out_dir: Path, manifest: dict, cfg: F1Config = DEFAULT, tests_summary: str = "") -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prep = res["prep"]
    rng = np.random.default_rng([SEED, 5])
    charts = {}
    for name in ("H1", "H2"):
        pool = res["pools"][name]
        idx = np.flatnonzero(pool["dir"] != 0)
        pick = np.sort(rng.choice(idx, size=min(N_EXAMPLES, len(idx)), replace=False)) if len(idx) else []
        cdir = out_dir / "charts" / name
        cdir.mkdir(parents=True, exist_ok=True)
        charts[name] = []
        for n, i in enumerate(pick):
            t, te = int(pool["t"][i]), int(pool["exit_t"][i])
            side = "LONG" if pool["dir"][i] > 0 else "SHORT"
            net = pool["long"][i] if pool["dir"][i] > 0 else pool["short"][i]
            title = f"F2 {name} {side} | {_fmt_t(t)} -> {_fmt_t(te)} | net {net:+.2f} USD"
            fn = cdir / f"ex_{n + 1:02d}.svg"
            fn.write_text(svg_chart(prep.bars, t, te, title, max(240, te - t + 30)), encoding="utf-8")
            charts[name].append({"file": str(fn.relative_to(out_dir)), "entry": _fmt_t(t), "exit": _fmt_t(te),
                                 "side": side, "net_usd": float(net)})
    a = prep.audit
    summary = {
        "phase": "F2", "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "verdict": res["verdict"], "config_fingerprint": cfg.fingerprint(),
        "prereg_sha256": PREREG_SHA256, "h2_thresholds": list(res["cuts"]),
        "data": {"manifest_sha256": {f["file"]: f["sha256"] for f in manifest.get("files", [])},
                 "per_year": {k: v for k, v in a["per_year"].items() if int(k) in F2_YEARS},
                 "quarantined_dates": [d for d in a["quarantined_dates"] if int(d[:4]) in F2_YEARS]},
        "results": res["results"], "charts": charts,
    }
    (out_dir / "report.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "report.md").write_text(_markdown(summary, tests_summary), encoding="utf-8")
    with open(out_dir / "trials_ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at_utc": summary["generated_at_utc"], "phase": "F2", "verdict": res["verdict"],
                            "fingerprint": summary["config_fingerprint"]}) + "\n")
    return summary


def _f(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def _yes(b):
    return "yes" if b else "**no**"


def _markdown(s: dict, tests_summary: str) -> str:
    L = ["# Edge Discovery Lab — Phase F2 report (one-shot, 2023–2024)", "",
         f"**Verdict: `{s['verdict']}`**", "",
         f"Generated {s['generated_at_utc']} · F1 config fingerprint `{s['config_fingerprint']}` · "
         f"bootstrap {N_BOOT} day-block reps, seed {SEED} · pre-registration: roadmap Section 11", "",
         "## Data", ""]
    for y, v in s["data"]["per_year"].items():
        L.append(f"- {y}: {v['days']} days, {v['bars']} M1 bars, {v['quarantined']} quarantined")
    if s["data"]["quarantined_dates"]:
        L.append(f"- quarantined: {', '.join(s['data']['quarantined_dates'])}")
    for fn, h in s["data"]["manifest_sha256"].items():
        L.append(f"- `{fn}` SHA-256 `{h}`")
    L += ["", "## Result per hypothesis (net USD/oz per trade)", "",
          "| | H1 (M3-EOD tree) | H2 (previous-day range) |", "|---|---|---|"]
    r1, r2 = s["results"]
    def row(label, fn):
        L.append(f"| {label} | {fn(r1)} | {fn(r2)} |")
    for y in map(str, F2_YEARS):
        row(f"{y} trades / days", lambda r: f"{r['per_year'][y]['trades']} / {r['per_year'][y]['days']}")
        row(f"{y} long share", lambda r: f"{_f(100 * r['per_year'][y]['long_share'], 1)}%")
        row(f"{y} mean net", lambda r: _f(r["per_year"][y]["mean_usd"], 4))
        row(f"{y} mean net (ATR)", lambda r: _f(r["per_year"][y]["mean_atr"], 4))
        row(f"{y} win rate", lambda r: f"{_f(100 * r['per_year'][y]['win_rate'], 1)}%")
        row(f"{y} B0 always long", lambda r: _f(r["per_year"][y]["b0_long_usd"], 4))
        row(f"{y} B0 always short", lambda r: _f(r["per_year"][y]["b0_short_usd"], 4))
    row("2023–2024 trades / days", lambda r: f"{r['trades']} / {r['days']}")
    row("2023–2024 mean net", lambda r: _f(r["mean_usd"], 4))
    row("bootstrap lower 95%", lambda r: _f(r["boot_lower_usd"], 4))
    row("p (bootstrap)", lambda r: _f(r["p_boot"], 4))
    row("p (Holm, 2 hypotheses)", lambda r: _f(r["p_holm"], 4))
    L += ["", "## Pass rule (roadmap 11.4)", "",
          "| Check | H1 | H2 |", "|---|---|---|"]
    for k, label in [("positive_each_year", "1. mean > 0 in 2023 and in 2024"),
                     ("boot_lower_positive", "2. bootstrap lower 95% > 0"),
                     ("beats_b0_each_year", "3. beats always long and always short, each year"),
                     ("holm", "4. Holm-adjusted p < 0.05")]:
        L.append(f"| {label} | {_yes(r1['checks'][k])} | {_yes(r2['checks'][k])} |")
    L.append(f"| **passes** | {_yes(r1['passes'])} | {_yes(r2['passes'])} |")
    L += ["", "H1 trades every eligible decision moment (overlapping moments counted independently, as in F1); "
          "H2 trades once per day at the first decision moment. B0 baselines use the same eligible moments/days.",
          "", "## Example charts (10 per hypothesis, seed [20260930, 5])", ""]
    for name, items in s["charts"].items():
        L.append(f"### {name}")
        for i, it in enumerate(items):
            L.append(f"- [{i + 1}]({it['file']}) {it['side']} {it['entry']} → {it['exit']}, net {it['net_usd']:+.2f}")
        L.append("")
    L += ["## Completion record", "", "```", "F2 — COMPLETE", f"Date: {s['generated_at_utc'][:10]}",
          "Data: " + ", ".join(f"{y}: {v['bars']} bars / {v['days']} days / {v['quarantined']} quarantined"
                               for y, v in s["data"]["per_year"].items()),
          f"Tests: {tests_summary or '...'}", f"Result: {s['verdict']}"]
    for r in s["results"]:
        L.append(f"  {r['hypothesis']}: trades {r['trades']}  mean {_f(r['mean_usd'], 4)}  "
                 f"2023 {_f(r['per_year']['2023']['mean_usd'], 4)}  2024 {_f(r['per_year']['2024']['mean_usd'], 4)}  "
                 f"boot_low {_f(r['boot_lower_usd'], 4)}  p {_f(r['p_boot'], 4)}  holm {_f(r['p_holm'], 4)}  "
                 f"pass {r['passes']}")
    L += ["```", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Edge Discovery Lab F2 one-shot run")
    ap.add_argument("--f1-data", default="../data")
    ap.add_argument("--f2-data", default="../data/f2")
    ap.add_argument("--out", default="../research/f2")
    ap.add_argument("--tests-summary", default="")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if (out / "report.json").exists():
        print("REFUSED: F2 is a one-shot test and research/f2/report.json already exists.", flush=True)
        return 2
    check_prereg()
    df, spec, man = load_f2(Path(a.f1_data), Path(a.f2_data))
    res = run(df, spec)
    write_report(res, out, man, tests_summary=a.tests_summary)
    print(f"verdict {res['verdict']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
