# Edge Discovery Lab — instructions for Claude

Read `EdgeLab_Roadmap.md` first. Its Section 0.3 non-negotiables (broker server time, no look-ahead, real costs, every trial counted, rules frozen before results, data discipline with 2025 locked) override anything below.

## Strategy-design workflow (mandatory)

When the owner asks to design, define, analyze or test a new strategy, setup, hypothesis or phase (for example "let's design a new strategy", "next phase", "F7"), follow these stages in order. Load each listed skill with the Skill tool at its stage; do not rely on memory of its content. Do not skip a stage or a skill. If a skill does not apply, say so in one line and why.

Each stage ends with a short written result that the owner sees before the next stage starts. Stages 1–3 produce no performance numbers.

### Stage 0 — Pivot: find a structurally different idea
- `strategy-pivot-designer`: start from the history of failed phases (LSR, BTB, ORB, F1 `F1_WEAK`, F2 `F2_FAIL`, F3 `F3_STOP`, F5 `F5_STOP`, F6 reverted). Diagnose why they stalled (cost defeat, thin edge, single instrument, price-only features) and propose ideas that differ in structure, not only in parameters. Use `references/strategy_archetypes.md` and `references/pivot_techniques.md`.
- `ml4t-causal-identification`: for each candidate, name the economic mechanism (who loses money to this edge, and why it persists).
- Output: 2–4 candidate hypotheses, each in one sentence, with its mechanism.

### Stage 1 — Critical review before any pre-registration
- `edge-strategy-reviewer`: score each candidate on criteria C1–C8 (`references/review_criteria.md`, `references/overfitting_checklist.md`, `assets/bias_checklist.yaml`). Give PASS / REVISE / REJECT. Run the script when a draft YAML exists; otherwise apply the rubric by hand and show the scores.
- `ml4t-transaction-costs`: estimate whether the expected move survives spread + commission with a safety margin, using the roadmap's cost model (Section 3.3).
- `backtest-expert`: check sample size (expected trades per year) and that the rules can be written with zero discretion.
- Output: one candidate the owner chooses to pre-register, or a recommendation to stop.

### Stage 2 — Design the test (pre-registration in the roadmap)
- `ml4t-lookahead-bias`, `ml4t-data-leakage`, `ml4t-point-in-time`: every feature and label uses only data known at decision time.
- `ml4t-survivorship-bias`: required whenever the universe has more than one instrument.
- `ml4t-walk-forward-cv`, `ml4t-purging-embargo`, `ml4t-cpcv`: choose the split; purge overlapping labels and embargo.
- `ml4t-triple-barrier` and `ml4t-meta-labels`: consider when the setup has stop / target / time exits or a filter on a primary signal.
- `ml4t-backtest-overfitting`, `ml4t-deflated-sharpe`: fix the number of configurations, the multiple-testing correction (Holm as in earlier phases, plus Deflated Sharpe and PBO), and the pass thresholds before any run.
- `ml4t-regime-awareness`, `ml4t-non-stationarity`: predeclare at most a few regime splits.
- `residual-edge-analyzer`: predeclare the baseline(s) the result must beat (for example buy-and-hold, random entry with the same exits).
- Output: a new roadmap section in the existing style (pre-registered, frozen), committed before Step A.

### Stage 3 — Step A: code and blocking tests
- `ml4t-cost-model`, `ml4t-run-backtest`: costs and engine contracts match the pre-registration.
- `ml4t-lookahead-bias`: include a blocking test that fails if any feature uses a future bar.
- No result on real data is computed in this stage.

### Stage 4 — Step B: one run and the verdict
- Run once, exactly as pre-registered. Any change after seeing numbers is a new, counted trial.
- `ml4t-deflated-sharpe`, `ml4t-backtest-overfitting`: report DSR and PBO next to the pre-registered statistic.
- `residual-edge-analyzer`: alpha against the predeclared baselines, with HAC t-stat and rolling stability.
- `backtest-expert`: run `scripts/evaluate_backtest.py` on the summary metrics and report its `decision` and `blocking_reasons`.
- `ml4t-sensitivity-analysis`: plateau versus spike around the chosen parameters.
- Output: a verdict in the roadmap's style (`F<n>_PASS` / `F<n>_WEAK` / `F<n>_STOP`), stated plainly.

### Stage 5 — After the verdict
- On a stop: append the `backtest-expert` evaluation to the pivot iteration history and return to Stage 0 only if the owner asks.
- On a pass: the locked holdout (2025) is used once, only with the owner's explicit authorization.

## Environment notes
- Local Python is Windows ARM64; numpy / scipy / statsmodels have no wheels here. The tradermonty skill scripts (stdlib + PyYAML) run locally. Code that needs numpy, pandas or scipy (ml4t examples, DSR, PBO, analysis) runs in a cloud session, as the earlier analysis phases did.
- Commits go straight to `main`.
