"""Phase F3: path-dependent exits (EdgeLab_Roadmap.md Section 12).

Usage (F3 Step B, from ``python/``), once::

    python -m edgelab.f3 --data ../data --out ../research/f3 --jobs 4

Everything but the exits is F1, unchanged: data 2020-07-01 .. 2022 (``load_f1``), the two
folds, decision moments, window, 25 features, costs, quarantine, the M1/M2/M3 learners and
their activation rules (``models.run_walkforward``), and the F1 config (fingerprint checked).

* Targets: for every exit rule of ``exits.EXIT_GRID`` (28) and side, the net R of that exit
  (``exits.simulate``). The learners fit and activate on net R.
* 28 exits x 3 families = 84 configurations, all counted.
* Primary count: one position at a time per configuration (``exits.one_at_a_time``);
  secondary: every signalled moment (F1 style).
* B1: 200 day-block permutations of the train targets (F1 seeds); each reruns all 84
  configurations and records the best one-position mean net R (reality check, Section 12.5).
* Verdict: Section 12.6.

Pre-registered details not spelled out in Section 12 (frozen here, before any F3 run):
* A configuration's statistic is the mean net R per out-of-fold trade on the one-position
  count; a permutation run in which a configuration makes no trade scores 0 for it.
* B0 with the same exit = always long / always short at every eligible out-of-fold moment
  (finite target), one position at a time, compared year by year on mean net R.
* Bootstrap: day-block over the one-position trades, 10,000 reps, seed 20260930, lower 5%
  quantile (as in F1). "At least 100 trades per year" is counted on the one-position trades.
* Charts (passing configurations only): 10 random one-position trades, seed [20260930, 6],
  M5 candles from 4 h before the entry to at least the exit.
* The run refuses to start when ``<out>/report.json`` already exists; every run is appended
  to ``trials_ledger.jsonl``.
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

from .config import DEFAULT, F1Config, FAMILIES
from .data import InstrumentSpec, load_f1, year_of_day
from .exits import EXIT_GRID, REASONS, one_at_a_time, simulate
from .models import Dataset, run_walkforward
from .report import Prepared, _fmt_t, prepare, svg_chart
from .stats import day_block_bootstrap, max_drawdown, max_stat_pvalue, null_max

F1_FINGERPRINT = "7e945e717983b088"
MIN_TRADES_PER_YEAR = 100
P_PASS = 0.05
P_WEAK = 0.10
N_EXAMPLES = 10


@dataclass
class Prepared3:
    prep: Prepared
    ds: Dataset
    exits: tuple
    names: list


def prepare_f3(df: pd.DataFrame, spec: InstrumentSpec, cfg: F1Config = DEFAULT, exits=EXIT_GRID) -> Prepared3:
    """F1 dataset (moments with complete features) + the exit targets of every rule and side."""
    prep = prepare(df, spec, cfg)
    sim = simulate(prep.bars, prep.moments, prep.atr5, cfg, exits)
    y = {}
    for e in exits:
        for side in ("long", "short"):
            s = sim[(e.name, side)]
            y[f"{side}_{e.name}"] = s["r"]
            y[f"usd_{side}_{e.name}"] = s["net_usd"]
            y[f"exit_t_{side}_{e.name}"] = s["exit_t"]
            y[f"reason_{side}_{e.name}"] = s["reason"]
            y[f"conflict_{side}_{e.name}"] = s["conflict"]
    base = prep.ds
    ds = Dataset(X=base.X, day=base.day, slot=base.slot, t=base.t, y=y)
    return Prepared3(prep=prep, ds=ds, exits=tuple(exits), names=[e.name for e in exits])


# ----------------------------------------------------------------------------- trades

def config_trades(ds: Dataset, r: dict, name: str) -> dict:
    """Out-of-fold trades of one configuration and the one-position-at-a-time mask."""
    rows = np.asarray(r["rows"], dtype=np.int64)
    d = np.asarray(r["dir"])
    lng = d > 0
    pick = lambda k: np.where(lng, ds.y[f"{k}long_{name}"][rows], ds.y[f"{k}short_{name}"][rows])  # noqa: E731
    tr = {"rows": rows, "dir": d, "r": np.asarray(r["net_usd"], float), "usd": pick("usd_"),
          "exit_t": pick("exit_t_").astype(np.int64), "reason": pick("reason_"),
          "conflict": pick("conflict_").astype(bool), "t": ds.t[rows], "day": ds.day[rows]}
    tr["take"] = one_at_a_time(tr["t"], tr["exit_t"]) if len(rows) else np.zeros(0, dtype=bool)
    return tr


def onepos_means(ds: Dataset, res: dict, names) -> np.ndarray:
    """Mean net R per configuration on the one-position count (NaN = no trade), in the
    order FAMILIES x names."""
    out = []
    for fam in FAMILIES:
        for n in names:
            tr = config_trades(ds, res[(fam, n)], n)
            v = tr["r"][tr["take"]]
            out.append(float(v.mean()) if len(v) else float("nan"))
    return np.array(out)


_G = {}


def _null_worker(k):
    ds, cfg, names = _G["ds"], _G["cfg"], _G["names"]
    return onepos_means(ds, run_walkforward(ds, cfg, perm_run=k, keep_rules=False, targets=names), names)


def run_null(p3: Prepared3, cfg: F1Config, jobs: int = 1, progress=None) -> np.ndarray:
    """(n_perm, 84) one-position means of every configuration in every permutation run."""
    runs = list(range(cfg.n_perm))
    results = []
    _G.update(ds=p3.ds, cfg=cfg, names=p3.names)
    try:
        if jobs > 1 and "fork" in mp.get_all_start_methods():
            with mp.get_context("fork").Pool(jobs) as pool:
                for i, r in enumerate(pool.imap(_null_worker, runs)):
                    results.append(r)
                    if progress:
                        progress(i + 1, len(runs))
        else:
            for i, k in enumerate(runs):
                results.append(_null_worker(k))
                if progress:
                    progress(i + 1, len(runs))
    finally:
        _G.clear()
    return np.array(results).reshape(len(runs), len(FAMILIES) * len(p3.names))


# ----------------------------------------------------------------------------- statistics

def _summ(r: np.ndarray, usd: np.ndarray, days: np.ndarray) -> dict:
    if len(r) == 0:
        return {"trades": 0, "days": 0, "mean_r": float("nan"), "mean_usd": float("nan"),
                "win_rate": float("nan"), "avg_win_r": float("nan"), "avg_loss_r": float("nan")}
    w, lo = r[r > 0], r[r <= 0]
    return {"trades": int(len(r)), "days": int(len(np.unique(days))), "mean_r": float(r.mean()),
            "mean_usd": float(np.nanmean(usd)), "win_rate": float(np.mean(r > 0)),
            "avg_win_r": float(w.mean()) if len(w) else float("nan"),
            "avg_loss_r": float(lo.mean()) if len(lo) else float("nan")}


def baseline_b0(ds: Dataset, names, test_years) -> dict:
    """{(exit, side): {year: mean net R}} for always long / always short, one position at a time."""
    yr = year_of_day(ds.day)
    tm = np.isin(yr, test_years)
    out = {}
    for n in names:
        for side in ("long", "short"):
            v = ds.y[f"{side}_{n}"]
            rows = np.flatnonzero(tm & np.isfinite(v))
            take = one_at_a_time(ds.t[rows], ds.y[f"exit_t_{side}_{n}"][rows])
            rr, yy = v[rows][take], yr[rows][take]
            out[(n, side)] = {str(y): (float(rr[yy == y].mean()) if (yy == y).any() else float("nan"))
                              for y in test_years}
            out[(n, side)]["trades"] = int(take.sum())
    return out


def results_table(p3: Prepared3, real: dict, null: np.ndarray, cfg: F1Config) -> list:
    ds = p3.ds
    test_years = [ty for _, ty in cfg.folds]
    best = null_max(null)
    b0 = baseline_b0(ds, p3.names, test_years)
    rows = []
    ci = 0
    for fam in FAMILIES:
        for e in p3.exits:
            n = e.name
            tr = config_trades(ds, real[(fam, n)], n)
            k = tr["take"]
            r, usd, days = tr["r"][k], tr["usd"][k], tr["day"][k]
            yrs = year_of_day(days) if len(days) else np.zeros(0, dtype=np.int64)
            row = {"family": fam, "exit": n, "exit_text": e.text(), **_summ(r, usd, days)}
            row["per_year"] = {str(y): _summ(r[yrs == y], usd[yrs == y], days[yrs == y]) for y in test_years}
            row["boot_lower_r"] = day_block_bootstrap(r, days, cfg.final_boot, cfg.seed, cfg.alpha)["lower"] \
                if len(r) else float("nan")
            row["p_rc"] = max_stat_pvalue(row["mean_r"], best)
            row["null_mean_this"] = float(np.nanmean(null[:, ci])) if null.size and np.isfinite(null[:, ci]).any() else float("nan")
            row["conflict_share"] = float(tr["conflict"][k].mean()) if k.any() else float("nan")
            row["exit_reasons"] = {REASONS[c]: int(np.sum(tr["reason"][k] == c)) for c in REASONS}
            row["max_dd_r"] = max_drawdown(r)
            row["all_moments"] = {"trades": int(len(tr["r"])),
                                  "mean_r": float(tr["r"].mean()) if len(tr["r"]) else float("nan")}
            row["b0"] = {side: b0[(n, side)] for side in ("long", "short")}
            row["n_rules"] = {str(y): len(v) for y, v in real[(fam, n)]["fold_rules"].items()}
            rows.append(row)
            ci += 1
    return rows


def verdict(rows: list, test_years) -> str:
    any_weak = False
    for r in rows:
        py = [r["per_year"][str(y)] for y in test_years]
        pos = all(v["trades"] > 0 and v["mean_r"] > 0 for v in py)
        beats = all(v["trades"] > 0 and v["mean_r"] > r["b0"]["long"][str(y)] and v["mean_r"] > r["b0"]["short"][str(y)]
                    for v, y in zip(py, test_years))
        r["checks"] = {
            "positive_each_year": pos,
            "boot_lower_positive": bool(np.isfinite(r["boot_lower_r"]) and r["boot_lower_r"] > 0),
            "reality_check_p": r["p_rc"] < P_PASS,
            "beats_b0_same_exit_each_year": beats,
            "min_100_trades_each_year": all(v["trades"] >= MIN_TRADES_PER_YEAR for v in py),
        }
        r["passes"] = all(r["checks"].values())
        r["weak"] = (not r["passes"]) and pos and r["p_rc"] < P_WEAK
        any_weak |= r["weak"]
    if any(r["passes"] for r in rows):
        return "F3_PASS"
    return "F3_WEAK" if any_weak else "F3_STOP"


def run_f3(p3: Prepared3, cfg: F1Config = DEFAULT, jobs: int = 1, progress=None,
           check_fingerprint: bool = True) -> dict:
    if check_fingerprint and cfg.fingerprint() != F1_FINGERPRINT:
        raise RuntimeError("F3 must use the frozen F1 config")
    t0 = time.time()
    real = run_walkforward(p3.ds, cfg, targets=p3.names)
    null = run_null(p3, cfg, jobs=jobs, progress=progress)
    rows = results_table(p3, real, null, cfg)
    v = verdict(rows, [ty for _, ty in cfg.folds])
    return {"verdict": v, "rows": rows, "real": real, "null": null, "seconds": time.time() - t0}


# ----------------------------------------------------------------------------- report

def _f(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def write_report(p3: Prepared3, res: dict, out_dir: Path, cfg: F1Config = DEFAULT, manifest: dict | None = None,
                 tests_summary: str = "") -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ds, bars = p3.ds, p3.prep.bars
    rng = np.random.default_rng([cfg.seed, 6])
    charts = {}
    for row in res["rows"]:
        if not row.get("passes"):
            continue
        name = f"{row['family']}_{row['exit']}"
        tr = config_trades(ds, res["real"][(row["family"], row["exit"])], row["exit"])
        idx = np.flatnonzero(tr["take"])
        pick = np.sort(rng.choice(idx, size=min(N_EXAMPLES, len(idx)), replace=False))
        cdir = out_dir / "charts" / name
        cdir.mkdir(parents=True, exist_ok=True)
        charts[name] = []
        for n_ex, i in enumerate(pick):
            t, te = int(tr["t"][i]), int(tr["exit_t"][i])
            side = "LONG" if tr["dir"][i] > 0 else "SHORT"
            title = (f"{name} {side} | {_fmt_t(t)} -> {_fmt_t(te)} {REASONS.get(int(tr['reason'][i]), '?')} | "
                     f"{tr['r'][i]:+.2f} R")
            fn = cdir / f"ex_{n_ex + 1:02d}.svg"
            fn.write_text(svg_chart(bars, t, te, title, max(240, te - t + 30)), encoding="utf-8")
            charts[name].append({"file": str(fn.relative_to(out_dir)), "entry": _fmt_t(t), "exit": _fmt_t(te),
                                 "side": side, "r": float(tr["r"][i])})
    rules = {f"{fam}_{n}": {str(y): [x.as_dict() for x in rs] for y, rs in res["real"][(fam, n)]["fold_rules"].items()}
             for fam in FAMILIES for n in p3.names}
    a = p3.prep.audit
    summary = {
        "phase": "F3", "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "verdict": res["verdict"], "config_fingerprint": cfg.fingerprint(), "n_configurations": len(res["rows"]),
        "n_perm": cfg.n_perm, "test_years": [ty for _, ty in cfg.folds],
        "exits": [{"name": e.name, "text": e.text()} for e in p3.exits],
        "data": {"rows_raw": a["rows_raw"], "days": a["n_days"], "quarantined_days": a["n_quarantined"],
                 "dataset_rows": ds.n,
                 "manifest_sha256": {f["file"]: f["sha256"] for f in (manifest or {}).get("files", [])}},
        "configurations": res["rows"], "null_best": null_max(res["null"]).tolist(),
        "rules": rules, "charts": charts, "runtime_seconds": res.get("seconds"),
    }
    (out_dir / "report.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    (out_dir / "report.md").write_text(_markdown(summary, tests_summary), encoding="utf-8")
    with open(out_dir / "trials_ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at_utc": summary["generated_at_utc"], "phase": "F3", "verdict": res["verdict"],
                            "fingerprint": summary["config_fingerprint"], "configurations": len(res["rows"]),
                            "n_perm": cfg.n_perm}) + "\n")
    return summary


def _markdown(s: dict, tests_summary: str) -> str:
    ty = [str(y) for y in s["test_years"]]
    nb = np.asarray(s["null_best"], float)
    L = ["# Edge Discovery Lab — Phase F3 report (path-dependent exits)", "",
         f"**Verdict: `{s['verdict']}`**", "",
         f"Generated {s['generated_at_utc']} · F1 config fingerprint `{s['config_fingerprint']}` · "
         f"{s['n_configurations']} configurations · {s['n_perm']} day-block permutations, reality check on the maximum",
         "", "## Data", "",
         f"- M1 rows {s['data']['rows_raw']}; days {s['data']['days']}; quarantined {s['data']['quarantined_days']}; "
         f"dataset moments {s['data']['dataset_rows']}"]
    for fn, h in s["data"]["manifest_sha256"].items():
        L.append(f"- `{fn}` SHA-256 `{h}`")
    if len(nb):
        L += ["", f"Null distribution of the best configuration (mean net R, one position at a time): "
              f"median {_f(float(np.median(nb)))}, 95% {_f(float(np.quantile(nb, 0.95)))}, 90% {_f(float(np.quantile(nb, 0.90)))}."]
    L += ["", f"## All {s['n_configurations']} configurations (out-of-fold {ty[0]}–{ty[-1]}, one position at a time, net R)", "",
          "| Family | Exit | Trades " + " / ".join(ty) + " | Win % | Avg win R | Avg loss R | " +
          " | ".join(f"Mean R {y}" for y in ty) + " | Mean R | Boot low R | p (RC) | B0 long " + "/".join(ty) +
          " | B0 short " + "/".join(ty) + " | Same-bar % | Max DD R | All-moments n / mean R | Result |",
          "|" + "---|" * (14 + len(ty)) ]
    for r in s["configurations"]:
        py = r["per_year"]
        res = "PASS" if r.get("passes") else ("weak" if r.get("weak") else "")
        L.append("| " + " | ".join([
            r["family"], f"`{r['exit']}`", " / ".join(str(py[y]["trades"]) for y in ty),
            _f(100 * r["win_rate"], 1) if r["trades"] else "—", _f(r["avg_win_r"], 2), _f(r["avg_loss_r"], 2),
            *[_f(py[y]["mean_r"], 3) for y in ty], _f(r["mean_r"], 3), _f(r["boot_lower_r"], 3), _f(r["p_rc"], 3),
            "/".join(_f(r["b0"]["long"][y], 3) for y in ty), "/".join(_f(r["b0"]["short"][y], 3) for y in ty),
            _f(100 * r["conflict_share"], 1), _f(r["max_dd_r"], 1),
            f"{r['all_moments']['trades']} / {_f(r['all_moments']['mean_r'], 3)}", res]) + " |")
    L += ["", "p (RC) = share of the permutation runs whose **best** configuration had a mean ≥ this one. "
          "B0 = always long / always short with the same exit, one position at a time. "
          "Same-bar % = trades whose stop and TP were touched in the same M1 bar (counted as the stop).", "",
          "## Exit rules", ""]
    for e in s["exits"]:
        L.append(f"- `{e['name']}`: {e['text']}")
    L += ["", "## Readable rules", "",
          "All rules of all configurations are in `report.json` (`rules`). Listed here: configurations that "
          "pass or are weak, and any configuration with at most 12 rules.", ""]
    flagged = {f"{r['family']}_{r['exit']}" for r in s["configurations"] if r.get("passes") or r.get("weak")}
    for name, by_year in s["rules"].items():
        n = sum(len(v) for v in by_year.values())
        if not n or (name not in flagged and n > 12):
            continue
        L.append(f"### {name} — {n} rules")
        for y, rs in by_year.items():
            L.append(f"- test {y}: {len(rs)} rules")
            for x in rs[:60]:
                L.append(f"  - `{x['id']}` {x['text']}")
        L.append("")
    if s["charts"]:
        L += ["## Chart snapshots (passing configurations)", ""]
        for name, items in s["charts"].items():
            L.append(f"### {name}")
            for i, it in enumerate(items):
                L.append(f"- [{i + 1}]({it['file']}) {it['side']} {it['entry']} → {it['exit']}, {it['r']:+.2f} R")
            L.append("")
    L += ["## Completion record", "", "```", "F3 — COMPLETE", f"Date: {s['generated_at_utc'][:10]}",
          f"Data: rows {s['data']['rows_raw']}, days {s['data']['days']}, quarantined {s['data']['quarantined_days']}",
          f"Tests: {tests_summary or '...'}", f"Result: {s['verdict']}"]
    top = sorted(s["configurations"], key=lambda r: -(r["mean_r"] if np.isfinite(r["mean_r"]) else -9))[:10]
    L.append("  best 10 by mean net R (one position at a time):")
    for r in top:
        L.append(f"  {r['family']} {r['exit']:>10}: trades {r['trades']:>5}  mean {_f(r['mean_r'], 3):>7} R  "
                 + "  ".join(f"{y} {_f(r['per_year'][y]['mean_r'], 3)}" for y in ty)
                 + f"  boot_low {_f(r['boot_lower_r'], 3)}  p {_f(r['p_rc'], 3)}")
    L += ["```", ""]
    return "\n".join(L)


# ----------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Edge Discovery Lab F3 run")
    ap.add_argument("--data", default="../data")
    ap.add_argument("--out", default="../research/f3")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 1)))
    ap.add_argument("--tests-summary", default="")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if (out / "report.json").exists():
        print("REFUSED: research/f3/report.json exists; F3 runs once (any rerun is a new counted trial "
              "and must be decided by the owner).", flush=True)
        return 2
    cfg = DEFAULT
    df, spec, manifest = load_f1(Path(a.data), cfg.years)
    p3 = prepare_f3(df, spec, cfg)
    print(f"dataset rows {p3.ds.n}, configurations {len(FAMILIES) * len(p3.names)}", flush=True)

    def progress(i, n):
        if i % 10 == 0 or i == n:
            print(f"  permutation {i}/{n}", flush=True)
    res = run_f3(p3, cfg, jobs=a.jobs, progress=progress)
    write_report(p3, res, out, cfg, manifest, a.tests_summary)
    print(f"verdict {res['verdict']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
