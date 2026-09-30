"""F2 pre-registration: freeze the H1 model and the H2 rule as files (EdgeLab_Roadmap.md, F2 section).

H1 = the second M3-EOD tree of F1 exactly as it was fitted in F1: fold 2, train
2020-07-01 .. 2021-12-30 (Dec 31 embargoed), the tree whose out-of-fold test year was 2022.
It is refitted here with the frozen F1 config (deterministic, random_state=0) and must match
research/f1/report.json rule by rule; nothing about it is changed.

H2 = the shared branch of both F1 trees, with the exact thresholds of the second tree.

Uses only F1 data (2020-07 .. 2022). Run from python/:
    python ../research/f2/prereg/freeze_models.py
"""
import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import sklearn
from sklearn.tree import DecisionTreeRegressor

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "python"))
from edgelab.config import DEFAULT  # noqa: E402
from edgelab.data import day_to_date, load_f1  # noqa: E402
from edgelab.models import _tree_leaf_conds, fit_m3, fold_masks  # noqa: E402
from edgelab.report import prepare  # noqa: E402

cfg = DEFAULT
rep = json.loads((ROOT / "research/f1/report.json").read_text())
assert rep["config_fingerprint"] == cfg.fingerprint()
(train_years, test_year) = cfg.folds[1]
assert tuple(train_years) == (2020, 2021) and test_year == 2022

df, spec, _ = load_f1(ROOT / "data", cfg.years)
prep = prepare(df, spec, cfg)
ds = prep.ds
tr, _ = fold_masks(ds.day, train_years, test_year, cfg)
yl, ys = ds.y["long_EOD"], ds.y["short_EOD"]
m_tr = tr & np.isfinite(yl) & np.isfinite(ys)
feats = list(ds.X)
X = {f: v[m_tr] for f, v in ds.X.items()}

# the exact F1 fitting call, then the same tree object for the file
rules = fit_m3(X, yl[m_tr], ys[m_tr], ds.day[m_tr], "EOD", cfg, None)
for k, r in enumerate(rules):
    r.rid = f"M3-EOD-{test_year}-{k:03d}"
got = [r.as_dict() for r in rules]
want = rep["rules"]["M3_EOD"][str(test_year)]
assert json.dumps(got, sort_keys=True) == json.dumps(want, sort_keys=True), "tree differs from the F1 report"

A = np.column_stack([X[f] for f in feats])
tree = DecisionTreeRegressor(max_depth=cfg.m3_max_depth, min_samples_leaf=cfg.m3_min_leaf, random_state=0)
tree.fit(A, yl[m_tr])
assert set(_tree_leaf_conds(tree, feats)) == {r["train"]["leaf"] for r in want}
t = tree.tree_
days_tr = ds.day[m_tr]
h1 = {
    "id": "F2-H1", "model": "M3 EOD tree, F1 fold 2 (test year 2022)",
    "authoritative": "rules (applied to float64 features exactly as in F1 models.rules_direction); "
                     "the sklearn arrays and the pickle are kept for inspection",
    "train": {"first_day": day_to_date(days_tr.min()), "last_day": day_to_date(days_tr.max()),
              "moments": int(m_tr.sum()), "days": int(len(np.unique(days_tr))),
              "target": "net long USD/oz to EOD (last M1 close <= 21:30)"},
    "config_fingerprint": cfg.fingerprint(),
    "sklearn_version": sklearn.__version__,
    "trading_rule": "every decision moment with all features finite and a valid EOD target: "
                    "LONG if a LONG rule fires, SHORT if a SHORT rule fires (leaves are disjoint), exit EOD",
    "rules": want,
    "sklearn_tree": {
        "feature_names": feats,
        "children_left": t.children_left.tolist(), "children_right": t.children_right.tolist(),
        "feature": t.feature.tolist(), "threshold": t.threshold.tolist(),
        "value": t.value[:, 0, 0].tolist(), "n_node_samples": t.n_node_samples.tolist(),
    },
}
# H2: the common branch. Thresholds = the two pd_range_rel cuts of the second tree.
cuts = sorted({c["hi"] for r in want for c in r["conditions"] if c["feature"] == "pd_range_rel" and c["hi"] is not None})
assert len(cuts) == 2, cuts
lo, hi = cuts
h2 = {
    "id": "F2-H2", "feature": "pd_range_rel",
    "definition": "previous trading day's range (high - low) / median daily range of the 20 trading days "
                  "before it (edgelab.features, unchanged)",
    "thresholds": {"small_max": lo, "medium_max": hi},
    "rule": {"pd_range_rel <= small_max": "NO TRADE",
             "small_max < pd_range_rel <= medium_max": "LONG",
             "medium_max < pd_range_rel": "SHORT"},
    "entry": "the day's first decision moment (first M5 close >= ResumeTime(d)); long pays spread(t), "
             "short pays spread at exit; commission 2 x 0.000016 x Bid_close(t)",
    "exit": "EOD: last M1 close <= 21:30 (F1 targets.py)",
    "trades_per_day": 1,
    "source": "F1 fold-2 M3 EOD tree (rules M3-EOD-2022-002 / -003 and -000 / -001 region), thresholds copied exactly",
}
(OUT / "h1_m3_eod_tree.json").write_text(json.dumps(h1, indent=1), encoding="utf-8")
(OUT / "h1_m3_eod_tree.pkl").write_bytes(pickle.dumps({"tree": tree, "feature_names": feats}, protocol=4))
(OUT / "h2_range_rule.json").write_text(json.dumps(h2, indent=1), encoding="utf-8")
for f in ("h1_m3_eod_tree.json", "h1_m3_eod_tree.pkl", "h2_range_rule.json"):
    print(f, hashlib.sha256((OUT / f).read_bytes()).hexdigest())
print("train", h1["train"])
print("H2 thresholds", repr(lo), repr(hi))
