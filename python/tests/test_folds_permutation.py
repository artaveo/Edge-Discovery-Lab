"""Folds (embargo, no train moment inside a test year) and the B1 day-block
permutation (roadmap Section 8)."""
import numpy as np
import pandas as pd

from edgelab.config import DEFAULT
from edgelab.data import year_of_day
from edgelab.models import Dataset, day_block_permutation, fold_masks, permuted_targets, target_keys, year_start_day


def _all_days():
    d = pd.bdate_range("2020-07-01", "2022-12-31")
    return ((d - pd.Timestamp("1970-01-01")) // pd.Timedelta(days=1)).to_numpy().astype(np.int64)


def test_folds_are_expanding_with_embargo():
    days = np.repeat(_all_days(), 3)                     # 3 moments per day
    year = year_of_day(days)
    expected_train = {2021: {2020}, 2022: {2020, 2021}}
    assert [ty for _, ty in DEFAULT.folds] == [2021, 2022]          # two out-of-fold years
    for train_years, test_year in DEFAULT.folds:
        tr, te = fold_masks(days, train_years, test_year, DEFAULT)
        assert set(year[tr].tolist()) == expected_train[test_year]
        assert (year[te] == test_year).all() and te.sum() == (year == test_year).sum()
        assert not (tr & te).any()
        # no train moment inside (or after the start of) the test year
        assert (year[tr] < test_year).all()
        start = year_start_day(test_year)
        # 1-day embargo: nothing dated on the last day before the test year
        assert days[tr].max() < start - DEFAULT.embargo_days
        assert (start - 1) in days and (start - 1) not in days[tr]      # Dec 31 is embargoed
        # every other train-year day is used
        pre = (year < test_year) & (days < start - DEFAULT.embargo_days)
        assert np.array_equal(tr, pre)


def test_embargo_drops_exactly_the_last_calendar_day():
    d0 = year_start_day(2021)
    days = np.array([d0 - 3, d0 - 2, d0 - 1, d0, d0 + 1])   # Dec 29, 30, 31, Jan 1, 2
    tr, te = fold_masks(days, (2020,), 2021, DEFAULT)
    assert tr.tolist() == [True, True, False, False, False]
    assert te.tolist() == [False, False, False, True, True]
    tr2, _ = fold_masks(days, (2020,), 2021, DEFAULT.with_(embargo_days=0))
    assert tr2.tolist() == [True, True, True, False, False]


def _toy(seed=0, n_days=40):
    rng = np.random.default_rng(seed)
    base = year_start_day(2021) + 1
    day, slot = [], []
    for k in range(n_days):
        s = np.sort(rng.choice(np.arange(10, 250), size=rng.integers(20, 60), replace=False))
        day += [base + k] * len(s)
        slot += s.tolist()
    return np.array(day, dtype=np.int64), np.array(slot, dtype=np.int64)


def test_day_block_shuffle_keeps_days_together_and_slots():
    day, slot = _toy()
    mask = np.ones(len(day), dtype=bool)
    src, mapping = day_block_permutation(day, slot, mask, np.random.default_rng(1))
    # the mapping is a permutation of the days that is not the identity
    ud = np.unique(day)
    assert sorted(mapping.keys()) == ud.tolist() and sorted(mapping.values()) == ud.tolist()
    moved = sum(mapping[d] != d for d in ud.tolist())
    assert moved >= len(ud) * 0.8
    ok = src >= 0
    assert ok.mean() > 0.1
    # every row of a receiving day gets its target from one single source day
    for d in ud:
        rows = (day == d) & ok
        assert set(day[src[rows]].tolist()) <= {mapping[int(d)]}
    # time of day is kept exactly
    assert np.array_equal(slot[src[ok]], slot[ok])
    # a row whose slot does not exist on the source day gets no target
    for i in np.flatnonzero(~ok):
        sd = mapping[int(day[i])]
        assert not ((day == sd) & (slot == slot[i])).any()


def test_day_block_shuffle_is_deterministic_and_seed_dependent():
    day, slot = _toy()
    mask = np.ones(len(day), dtype=bool)
    a, ma = day_block_permutation(day, slot, mask, np.random.default_rng([20260930, 1, 0, 0]))
    b, mb = day_block_permutation(day, slot, mask, np.random.default_rng([20260930, 1, 0, 0]))
    c, mc = day_block_permutation(day, slot, mask, np.random.default_rng([20260930, 1, 1, 0]))
    assert np.array_equal(a, b) and ma == mb
    assert ma != mc


def test_permutation_stays_inside_the_train_mask():
    day, slot = _toy(n_days=30)
    n = len(day)
    rng = np.random.default_rng(3)
    y = {k: rng.normal(size=n) for k in target_keys(DEFAULT)}
    X = {"x": rng.normal(size=n)}
    ds = Dataset(X=X, day=day, slot=slot, t=np.zeros(n), y=y)
    train = day < day.min() + 20                       # first 20 days are "train"
    yp = permuted_targets(ds, train, np.random.default_rng(5), DEFAULT)
    for k in target_keys(DEFAULT):
        # rows outside the train mask are untouched
        assert np.array_equal(yp[k][~train], y[k][~train])
        # inside, values are either NaN or come from a train row with the same slot
        vals = yp[k][train]
        fin = np.isfinite(vals)
        pool = y[k][train]
        assert np.isin(vals[fin], pool).all()
    # and all target columns use the same day mapping (row-wise consistent)
    src_rows = [np.flatnonzero(np.isclose(y["long_H60"], v))[0]
                for v in yp["long_H60"][train] if np.isfinite(v)]
    other = yp["short_EOD"][train][np.isfinite(yp["long_H60"][train])]
    assert np.allclose(y["short_EOD"][src_rows], other)
    # the shuffled train targets differ from the real ones
    assert not np.allclose(np.nan_to_num(yp["long_H60"][train]), y["long_H60"][train])
