"""F2 pre-registration (roadmap Section 11): the frozen model files must match the SHA-256
written in the roadmap, and the H2 thresholds must be the ones of the H1 tree."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRE = ROOT / "research" / "f2" / "prereg"
FILES = ("h1_m3_eod_tree.json", "h1_m3_eod_tree.pkl", "h2_range_rule.json")


def test_frozen_files_match_roadmap_hashes():
    roadmap = (ROOT / "EdgeLab_Roadmap.md").read_text(encoding="utf-8")
    for f in FILES:
        digest = hashlib.sha256((PRE / f).read_bytes()).hexdigest()
        assert digest in roadmap, f"{f} changed after pre-registration"


def test_h2_thresholds_come_from_the_h1_tree():
    h1 = json.loads((PRE / "h1_m3_eod_tree.json").read_text())
    h2 = json.loads((PRE / "h2_range_rule.json").read_text())
    cuts = sorted({c["hi"] for r in h1["rules"] for c in r["conditions"]
                   if c["feature"] == "pd_range_rel" and c["hi"] is not None})
    assert [h2["thresholds"]["small_max"], h2["thresholds"]["medium_max"]] == cuts
    assert h1["train"]["last_day"] == "2021-12-30" and len(h1["rules"]) == 7
