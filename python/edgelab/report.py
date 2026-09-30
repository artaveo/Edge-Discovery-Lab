"""F1 pipeline and report (roadmap Sections 5.3, 6, 7 step C, 9).

Usage (Step C, from ``python/``)::

    python -m edgelab.report --data ../data --out ../research/f1 --jobs 4

Writes ``report.md``, ``report.json``, ``audit_2019_2022.json`` (to the data dir),
chart snapshots (SVG) for passing configurations and appends the run to
``trials_ledger.jsonl`` (every run is a counted trial).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import multiprocessing as mp
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .audit import audit_m1, write_audit
from .config import DEFAULT, F1Config, FAMILIES, MIN_PER_DAY, horizon_name
from .data import (Bars, InstrumentSpec, build_bars, clean_m1, day_to_date, load_f1,
                   minutes_to_datetime, to_minutes, weekday_of_day, year_of_day)
from .features import FEATURES, compute_features, m5_atr
from .models import Dataset, oof_mean, run_walkforward, target_keys
from .stats import day_block_bootstrap, holm, permutation_pvalue, verdict
from .targets import compute_targets
from .window import decision_moments, resume_times


# ----------------------------------------------------------------------------- prepare

@dataclass
class Prepared:
    bars: Bars
    audit: dict
    moments: np.ndarray        # M5 indices of the dataset rows
    ds: Dataset
    n_moments_raw: int
    atr5: np.ndarray


def prepare(df_raw: pd.DataFrame, spec: InstrumentSpec, cfg: F1Config = DEFAULT) -> Prepared:
    """Audit, window, targets and features -> modelling dataset."""
    audit = audit_m1(df_raw, cfg)
    df, _ = clean_m1(df_raw)
    wd = weekday_of_day(to_minutes(df["time"]) // MIN_PER_DAY)
    df = df.loc[wd < 5].reset_index(drop=True)          # weekend bars: reported, not used
    bars = build_bars(df, spec)
    resume = resume_times(bars, cfg)
    moments = decision_moments(bars, resume, audit["excluded_days"], cfg)
    atr5 = m5_atr(bars, cfg)
    F = compute_features(bars, resume, moments, atr5, cfg)
    T = compute_targets(bars, moments, atr5, cfg)
    keep = F.notna().all(axis=1).to_numpy() & np.isfinite(T["atr60"]) & (T["atr60"] > 0)
    j = moments[keep]
    ds = Dataset(
        X={f: F[f].to_numpy()[keep] for f in FEATURES},
        day=bars.day5[j],
        slot=(bars.k5[j] % MIN_PER_DAY) // 5,
        t=bars.tc5[j],
        y={k: T[k][keep] for k in target_keys(cfg)} | {
            k: T[k][keep] for k in T if k.startswith(("move_", "exit_t_"))} | {
            "p0": T["p0"][keep], "atr60": T["atr60"][keep]},
    )
    return Prepared(bars=bars, audit=audit, moments=j, ds=ds, n_moments_raw=len(moments), atr5=atr5)


# ----------------------------------------------------------------------------- null runs

_G = {}


def _null_worker(k):
    return oof_mean(run_walkforward(_G["ds"], _G["cfg"], perm_run=k, keep_rules=False))


def run_null(ds: Dataset, cfg: F1Config, jobs: int = 1, progress=None) -> dict:
    """B1: ``cfg.n_perm`` day-block permutation runs. Returns {config: array of null means}."""
    runs = list(range(cfg.n_perm))
    results = []
    if jobs > 1 and "fork" in mp.get_all_start_methods():
        _G["ds"], _G["cfg"] = ds, cfg
        with mp.get_context("fork").Pool(jobs) as pool:
            for i, r in enumerate(pool.imap(_null_worker, runs)):
                results.append(r)
                if progress:
                    progress(i + 1, len(runs))
        _G.clear()
    else:
        for i, k in enumerate(runs):
            results.append(oof_mean(run_walkforward(ds, cfg, perm_run=k, keep_rules=False)))
            if progress:
                progress(i + 1, len(runs))
    keys = list(results[0]) if results else []
    return {k: np.array([r[k] for r in results]) for k in keys}


# ----------------------------------------------------------------------------- tables

def _summ(net_usd, net_atr, days):
    if len(net_usd) == 0:
        return {"trades": 0, "days": 0, "mean_usd": float("nan"), "mean_atr": float("nan"),
                "win_rate": float("nan")}
    return {"trades": int(len(net_usd)), "days": int(len(np.unique(days))),
            "mean_usd": float(np.mean(net_usd)), "mean_atr": float(np.mean(net_atr)),
            "win_rate": float(np.mean(net_usd > 0))}


def baseline_b0(ds: Dataset, cfg: F1Config) -> list:
    rows = []
    test_years = [ty for _, ty in cfg.folds]
    yr = year_of_day(ds.day)
    for h in cfg.horizons:
        hn = horizon_name(h)
        for side in ("long", "short"):
            v = ds.y[f"{side}_{hn}"]
            m = np.isin(yr, test_years) & np.isfinite(v)
            s = _summ(v[m], ds.y[f"{side}_atr_{hn}"][m], ds.day[m])
            rows.append({"baseline": f"B0 always {side}", "horizon": hn, **s})
    return rows


def results_table(ds: Dataset, real: dict, null: dict, cfg: F1Config) -> list:
    test_years = [ty for _, ty in cfg.folds]
    rows = []
    for fam in FAMILIES:
        for h in cfg.horizons:
            hn = horizon_name(h)
            r = real[(fam, hn)]
            days = ds.day[r["rows"]]
            yrs = year_of_day(days) if len(days) else np.zeros(0, dtype=np.int64)
            row = {"family": fam, "horizon": hn, **_summ(r["net_usd"], r["net_atr"], days)}
            bu = day_block_bootstrap(r["net_usd"], days, cfg.final_boot, cfg.seed, cfg.alpha)
            ba = day_block_bootstrap(r["net_atr"], days, cfg.final_boot, cfg.seed, cfg.alpha)
            row["boot_lower_usd"] = bu["lower"]
            row["boot_lower_atr"] = ba["lower"]
            row["per_year"] = {str(y): _summ(r["net_usd"][yrs == y], r["net_atr"][yrs == y], days[yrs == y])
                               for y in test_years}
            nl = null.get((fam, hn), np.zeros(0))
            row["p_perm"] = permutation_pvalue(row["mean_usd"], nl)
            fin = nl[np.isfinite(nl)]
            row["null_runs"] = int(len(nl))
            row["null_runs_with_trades"] = int(len(fin))
            row["null_mean_usd"] = float(np.mean(fin)) if len(fin) else float("nan")
            row["null_q95_usd"] = float(np.quantile(fin, 0.95)) if len(fin) else float("nan")
            row["n_rules"] = {str(y): len(v) for y, v in r["fold_rules"].items()}
            rows.append(row)
    adj, _ = holm([r["p_perm"] for r in rows], cfg.alpha)
    for r, a in zip(rows, adj):
        r["p_holm"] = float(a)
    return rows


def run_f1(prep: Prepared, cfg: F1Config = DEFAULT, jobs: int = 1, progress=None) -> dict:
    t0 = time.time()
    real = run_walkforward(prep.ds, cfg)
    null = run_null(prep.ds, cfg, jobs=jobs, progress=progress)
    rows = results_table(prep.ds, real, null, cfg)
    test_years = [ty for _, ty in cfg.folds]
    v = verdict(rows, test_years, cfg)
    return {"verdict": v, "rows": rows, "real": real, "null": null,
            "b0": baseline_b0(prep.ds, cfg), "seconds": time.time() - t0}


# ----------------------------------------------------------------------------- charts

def svg_chart(bars: Bars, t: int, t_exit: int, title: str, half: int = 240) -> str:
    """M5 candles in [t - half, t + half] with the entry (blue) and exit (orange) marked."""
    lo_k, hi_k = t - half, t + half
    j0, j1 = np.searchsorted(bars.k5, lo_k), np.searchsorted(bars.k5, hi_k)
    k = bars.k5[j0:j1]
    o, h, l, c = bars.o5[j0:j1], bars.h5[j0:j1], bars.l5[j0:j1], bars.c5[j0:j1]
    W, H, pad = 960, 380, 44
    if len(k) == 0:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="60"><text x="8" y="30">no bars</text></svg>'
    pmin, pmax = float(l.min()), float(h.max())
    span = (pmax - pmin) or 1.0

    def x(m):
        return pad + (m - lo_k) / (2 * half) * (W - 2 * pad)

    def y(p):
        return pad + (pmax - p) / span * (H - 2 * pad)
    cw = max(1.0, (W - 2 * pad) / (2 * half / 5) * 0.7)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="11">',
             f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
             f'<text x="{pad}" y="18" font-size="12" fill="#111">{_esc(title)}</text>']
    for m, col in ((t, "#1f6feb"), (t_exit, "#d97706")):
        if lo_k <= m <= hi_k:
            parts.append(f'<line x1="{x(m):.1f}" y1="{pad}" x2="{x(m):.1f}" y2="{H - pad}" stroke="{col}" stroke-dasharray="4 3"/>')
    for i in range(len(k)):
        xm = x(k[i] + 2.5)
        up = c[i] >= o[i]
        col = "#1a7f37" if up else "#cf222e"
        parts.append(f'<line x1="{xm:.1f}" y1="{y(h[i]):.1f}" x2="{xm:.1f}" y2="{y(l[i]):.1f}" stroke="{col}"/>')
        top, bot = y(max(o[i], c[i])), y(min(o[i], c[i]))
        parts.append(f'<rect x="{xm - cw / 2:.1f}" y="{top:.1f}" width="{cw:.1f}" height="{max(bot - top, 0.8):.1f}" fill="{col}"/>')
    parts.append(f'<text x="4" y="{pad + 4}" fill="#555">{pmax:.2f}</text>')
    parts.append(f'<text x="4" y="{H - pad}" fill="#555">{pmin:.2f}</text>')
    for m in range(lo_k - lo_k % 60 + 60, hi_k, 60):
        parts.append(f'<text x="{x(m) - 14:.1f}" y="{H - pad + 16}" fill="#555">{(m % MIN_PER_DAY) // 60:02d}:00</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt_t(m: int) -> str:
    return str(minutes_to_datetime([m])[0])[:16]


# ----------------------------------------------------------------------------- writing

def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def write_report(prep: Prepared, res: dict, out_dir: Path, cfg: F1Config = DEFAULT,
                 manifest: dict | None = None, tests_summary: str = "", files_changed: str = "") -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ds, bars = prep.ds, prep.bars
    rng = np.random.default_rng([cfg.seed, 3])
    charts = {}
    rules_out = {}
    for row in res["rows"]:
        key = (row["family"], row["horizon"])
        r = res["real"][key]
        name = f"{row['family']}_{row['horizon']}"
        rules_out[name] = {str(y): [x.as_dict() for x in rs] for y, rs in r["fold_rules"].items()}
        if not row.get("passes"):
            continue
        hits = sorted(r["rule_hits"], key=lambda rh: -len(rh[1]))[: cfg.max_rules_charted]
        cdir = out_dir / "charts" / name
        cdir.mkdir(parents=True, exist_ok=True)
        charts[name] = []
        for rule, idx in hits:
            if len(idx) == 0:
                continue
            pick = rng.choice(idx, size=min(cfg.examples_per_rule, len(idx)), replace=False)
            files = []
            for n_ex, ti in enumerate(sorted(pick)):
                drow = r["rows"][ti]
                t = int(ds.t[drow])
                t_exit = int(ds.y[f"exit_t_{row['horizon']}"][drow])
                title = f"{rule.text()} | {_fmt_t(t)} | net {r['net_usd'][ti]:+.2f} USD"
                fn = cdir / f"{rule.rid}_{n_ex:02d}.svg"
                fn.write_text(svg_chart(bars, t, t_exit, title, cfg.chart_half_window_min), encoding="utf-8")
                files.append(str(fn.relative_to(out_dir)))
            charts[name].append({"rule": rule.rid, "text": rule.text(), "files": files})

    summary = {
        "phase": "F1",
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "verdict": res["verdict"],
        "config_fingerprint": cfg.fingerprint(),
        "config": cfg.as_dict(),
        "n_configurations": len(res["rows"]),
        "data": {
            "rows_raw": prep.audit["rows_raw"], "days": prep.audit["n_days"],
            "quarantined_days": prep.audit["n_quarantined"],
            "decision_moments": prep.n_moments_raw, "dataset_rows": ds.n,
            "manifest_sha256": {f["file"]: f["sha256"] for f in (manifest or {}).get("files", [])},
        },
        "configurations": res["rows"],
        "baselines_b0": res["b0"],
        "rules": rules_out,
        "charts": charts,
        "runtime_seconds": res.get("seconds"),
    }
    (out_dir / "report.json").write_text(json.dumps(_jsonable(summary), indent=1), encoding="utf-8")
    (out_dir / "report.md").write_text(_markdown(summary, tests_summary, files_changed), encoding="utf-8")
    with open(out_dir / "trials_ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at_utc": summary["generated_at_utc"], "fingerprint": summary["config_fingerprint"],
                            "verdict": res["verdict"], "configurations": len(res["rows"]),
                            "n_perm": cfg.n_perm}) + "\n")
    return summary


def _f(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def _markdown(s: dict, tests_summary: str, files_changed: str) -> str:
    L = [f"# Edge Discovery Lab — Phase F1 report", "",
         f"**Verdict: `{s['verdict']}`**", "",
         f"Generated {s['generated_at_utc']} · config fingerprint `{s['config_fingerprint']}` · "
         f"{s['config']['n_perm']} permutation runs · bootstrap {s['config']['final_boot']} reps, seed {s['config']['seed']}",
         "", "## Data", "",
         f"- M1 rows: {s['data']['rows_raw']}; days: {s['data']['days']}; quarantined days: {s['data']['quarantined_days']}",
         f"- decision moments: {s['data']['decision_moments']}; with complete features (dataset): {s['data']['dataset_rows']}",
         ""]
    for fn, h in s["data"]["manifest_sha256"].items():
        L.append(f"- `{fn}` SHA-256 `{h}`")
    L += ["", "## The 12 configurations (out-of-fold 2020–2022, net of cost)", "",
          "| Family | H | Trades | Days | Mean USD/oz | Mean ATR | Win % | Boot low 95% USD | 2020 | 2021 | 2022 | p perm | p Holm | Null runs trading | Pass |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in s["configurations"]:
        py = r["per_year"]
        L.append("| " + " | ".join([
            r["family"], r["horizon"], str(r["trades"]), str(r["days"]), _f(r["mean_usd"], 4),
            _f(r["mean_atr"], 4), _f(100 * r["win_rate"] if r["trades"] else float("nan"), 1),
            _f(r["boot_lower_usd"], 4),
            *[f"{_f(py[y]['mean_usd'], 3)} ({py[y]['trades']})" for y in sorted(py)],
            _f(r["p_perm"], 3), _f(r["p_holm"], 3), f"{r['null_runs_with_trades']}/{r['null_runs']}",
            "yes" if r.get("passes") else "no"]) + " |")
    L += ["", "Per-year cells: mean net USD/oz (trades). p perm = share of the shuffled runs with a "
          "mean >= the real one (a shuffled run without trades scores 0). Holm over the 12 configurations "
          "at α = 0.05. 'Null runs trading' shows how many shuffled runs produced any trade: when few do, "
          "a small p mostly says the real rule traded at all, so read F1_WEAK with care.", "",
          "## Baseline B0 (always long / always short, out-of-fold years)", "",
          "| Baseline | H | Trades | Mean USD/oz | Mean ATR | Win % |", "|---|---|---|---|---|---|"]
    for b in s["baselines_b0"]:
        L.append(f"| {b['baseline']} | {b['horizon']} | {b['trades']} | {_f(b['mean_usd'], 4)} | "
                 f"{_f(b['mean_atr'], 4)} | {_f(100 * b['win_rate'] if b['trades'] else float('nan'), 1)} |")
    L += ["", "## Readable rules", ""]
    for name, by_year in s["rules"].items():
        n = sum(len(v) for v in by_year.values())
        L.append(f"### {name} — {n} active rules")
        if not n:
            L.append("")
            continue
        passing = name in s["charts"]
        for y, rules in by_year.items():
            L.append(f"- test {y} (trained before it): {len(rules)} rules")
            if passing or n <= 12:
                for r in rules[:60]:
                    L.append(f"  - `{r['id']}` {r['text']}")
        L.append("")
    if s["charts"]:
        L += ["## Chart snapshots (passing configurations)", ""]
        for name, items in s["charts"].items():
            L.append(f"### {name}")
            for it in items:
                L.append(f"- `{it['rule']}` {it['text']}: " + ", ".join(f"[{i + 1}]({p})" for i, p in enumerate(it["files"])))
            L.append("")
    L += ["## Completion record", "", "```", "F1 — COMPLETE",
          f"Date: {s['generated_at_utc'][:10]}",
          f"Files changed: {files_changed or '...'}",
          f"Data: rows {s['data']['rows_raw']}, days {s['data']['days']}, quarantined days "
          f"{s['data']['quarantined_days']}, manifest SHA-256 " +
          ", ".join(f"{k}={v[:12]}…" for k, v in s["data"]["manifest_sha256"].items()),
          f"Tests: {tests_summary or '...'}",
          f"Result: {s['verdict']}"]
    for r in s["configurations"]:
        L.append(f"  {r['family']} {r['horizon']:>4}: trades {r['trades']:>6}  mean {_f(r['mean_usd'], 4):>8} USD  "
                 f"boot_low {_f(r['boot_lower_usd'], 4):>8}  p {_f(r['p_perm'], 3)}  holm {_f(r['p_holm'], 3)}")
    L += ["```", ""]
    return "\n".join(L)


# ----------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Edge Discovery Lab F1 run")
    ap.add_argument("--data", default="../data")
    ap.add_argument("--out", default="../research/f1")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 1)))
    ap.add_argument("--tests-summary", default="")
    ap.add_argument("--files-changed", default="")
    a = ap.parse_args(argv)
    cfg = DEFAULT
    df, spec, manifest = load_f1(Path(a.data), cfg.years)
    prep = prepare(df, spec, cfg)
    write_audit(prep.audit, Path(a.data) / "audit_2019_2022.json")
    print(f"dataset rows {prep.ds.n}, days {prep.audit['n_days']}, quarantined {prep.audit['n_quarantined']}",
          flush=True)

    def progress(i, n):
        if i % 10 == 0 or i == n:
            print(f"  permutation {i}/{n}", flush=True)
    res = run_f1(prep, cfg, jobs=a.jobs, progress=progress)
    write_report(prep, res, Path(a.out), cfg, manifest, a.tests_summary, a.files_changed)
    print(f"verdict {res['verdict']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
