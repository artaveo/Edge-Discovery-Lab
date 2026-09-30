"""Features: brute-force equality, the look-ahead test and ATR scaling (roadmap Section 8).

The brute-force reference below is written independently of ``features.py``: for
each tested moment it slices the raw M1 frame to the bars closed at or before t
and recomputes every feature from its textual definition with plain pandas/loops.
"""
import numpy as np
import pandas as pd
import pytest

from edgelab.config import DEFAULT
from edgelab.data import build_bars, wilder_atr
from edgelab.features import ATR_SCALED, FEATURES, compute_features, m5_atr
from edgelab.window import decision_moments, resume_times

CFG = DEFAULT
ONE = pd.Timedelta(minutes=1)


# ----------------------------------------------------------------------------- data

def make_series(n_days=36, seed=5):
    """Random-walk M1 bars on weekdays, 01:00-22:59, with wide opening spreads,
    random gaps (missing bars) and a few late-opening days."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2019-02-04", periods=n_days)
    frames = []
    p = 1300.0
    for k, d in enumerate(days):
        start = "01:00" if k % 7 else "02:13"
        t = pd.date_range(f"{d.date()} {start}", f"{d.date()} 22:59", freq="1min")
        keep = rng.random(len(t)) > 0.03                      # ~3 % missing bars
        if k % 5 == 2:
            keep &= ~((t >= f"{d.date()} 12:00") & (t < f"{d.date()} 12:20"))   # a 20-min gap
        t = t[keep]
        n = len(t)
        steps = rng.normal(0, 0.25, n)
        c = p + np.cumsum(steps)
        o = np.r_[p, c[:-1]] + rng.normal(0, 0.02, n)
        h = np.maximum(o, c) + np.abs(rng.normal(0, 0.1, n))
        l = np.minimum(o, c) - np.abs(rng.normal(0, 0.1, n))
        sp = rng.integers(15, 30, n)
        sp[:rng.integers(3, 30)] = 90
        if k % 9 == 4:
            sp[: n // 2] = 70                                  # spreads never normalise early
        frames.append(pd.DataFrame({"time": t, "open": o.round(2), "high": h.round(2),
                                    "low": l.round(2), "close": c.round(2),
                                    "tick_volume": rng.integers(1, 200, n), "spread_pts": sp}))
        p = c[-1] + rng.normal(0, 0.5)
    df = pd.concat(frames, ignore_index=True)
    df["high"] = df[["open", "high", "low", "close"]].max(axis=1)
    df["low"] = df[["open", "high", "low", "close"]].min(axis=1)
    return df


def vectorised(df, cfg=CFG):
    bars = build_bars(df)
    res = resume_times(bars, cfg)
    j = decision_moments(bars, res, (), cfg)
    atr5 = m5_atr(bars, cfg)
    F = compute_features(bars, res, j, atr5, cfg)
    F.index = pd.DatetimeIndex(bars.tc5[j].astype("datetime64[m]"))
    return F, atr5[j], bars, j


# ----------------------------------------------------------------------------- brute force

class Brute:
    def __init__(self, df, cfg=CFG):
        self.cfg = cfg
        self.df = df.sort_values("time").reset_index(drop=True).copy()
        self.df["tclose"] = self.df["time"] + ONE
        self.df["date"] = self.df["time"].dt.normalize()
        self.dates = list(self.df["date"].drop_duplicates())
        # M5 bars and their Wilder ATR over the whole sample. The recursion only looks
        # backwards, so these values are what a trader had at each M5 close; they are used
        # for the same-time-of-day history of *previous* days. The ATR of the moment itself
        # is recomputed from the truncated frame in ``features``.
        full = self.m5(self.df)
        self.atr_full = pd.Series(self.wilder(full["high"], full["low"], full["close"]),
                                  index=full["tclose"])
        self._day_m5 = {}
        self._cache = {}

    # ---- helpers on the frame truncated at t
    @staticmethod
    def m5(past):
        g = past.groupby(past["time"].dt.floor("5min"))
        m = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                          "close": g["close"].last(), "tv": g["tick_volume"].sum()})
        m["tclose"] = m.index + pd.Timedelta(minutes=5)
        return m

    @staticmethod
    def wilder(h, l, c, n=14):
        h, l, c = list(h), list(l), list(c)
        tr = []
        for i in range(len(h)):
            if i == 0:
                tr.append(h[0] - l[0])
            else:
                tr.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
        out = [np.nan] * len(h)
        if len(h) >= n:
            a = sum(tr[:n]) / n
            out[n - 1] = a
            for i in range(n, len(h)):
                a = (a * (n - 1) + tr[i]) / n
                out[i] = a
        return out

    def past(self, t):
        return self.df[self.df["tclose"] <= t]

    def close_asof(self, t):
        p = self.past(t)
        return p["close"].iloc[-1] if len(p) else np.nan

    def resume(self, date):
        k = self.dates.index(date)
        day = self.df[self.df["date"] == date]
        if k == 0:
            return date + pd.Timedelta(hours=16, minutes=30)
        prev = self.df[self.df["date"] == self.dates[k - 1]]
        mod = prev["time"] - self.dates[k - 1]
        ref = prev[(mod >= pd.Timedelta(hours=10)) & (mod < pd.Timedelta(hours=21, minutes=30))]["spread_pts"]
        thr = 1.5 * np.median(ref)
        sp = list(day["spread_pts"])
        tc = list(day["tclose"])
        deadline = date + pd.Timedelta(hours=16, minutes=30)
        for i in range(4, len(sp)):
            if all(s <= thr for s in sp[i - 4:i + 1]):
                return tc[i] if tc[i] <= deadline else deadline
        return deadline

    def m5_value_on_day_at_clock(self, date, clock, fn):
        """fn(t') at the latest M5 close t' of ``date`` with t' <= date + clock (NaN if none)."""
        if date not in self._day_m5:
            self._day_m5[date] = self.m5(self.df[self.df["date"] == date])
        m = self._day_m5[date]
        m = m[m["tclose"] <= date + clock]
        if not len(m):
            return np.nan
        return fn(m["tclose"].iloc[-1])

    def atr_at(self, t):
        return float(self.atr_full.loc[t])

    def rv30_at(self, t):
        key = ("rv", t)
        if key not in self._cache:
            self._cache[key] = self._rv30(t)
        return self._cache[key]

    def _rv30(self, t):
        c = self.past(t)["close"].to_numpy()
        if len(c) < 31:
            return np.nan
        r = np.diff(np.log(c[-31:]))
        return float(np.sqrt(np.mean(r ** 2)))

    def tv15_at(self, t):
        key = ("tv", t)
        if key not in self._cache:
            self._cache[key] = self._tv15(t)
        return self._cache[key]

    def _tv15(self, t):
        p = self.past(t)
        return float(p[p["tclose"] > t - pd.Timedelta(minutes=15)]["tick_volume"].sum())

    def hist(self, date, clock, fn, how):
        k = self.dates.index(date)
        vals = [self.m5_value_on_day_at_clock(d, clock, fn) for d in self.dates[max(0, k - 20):k]]
        vals = [v for v in vals if np.isfinite(v)]
        if len(vals) < 10:
            return np.nan
        return float(np.mean(vals) if how == "mean" else np.median(vals))

    def daily(self, upto_date):
        d = self.df[self.df["date"] <= upto_date].groupby("date")
        return pd.DataFrame({"open": d["open"].first(), "high": d["high"].max(),
                             "low": d["low"].min(), "close": d["close"].last()})

    # ---- all features at t
    def features(self, t):
        date = t.normalize()
        clock = t - date
        past = self.past(t)
        C = past["close"].iloc[-1]
        m5 = self.m5(past)
        atr = self.wilder(m5["high"], m5["low"], m5["close"])[-1]
        today = past[past["date"] == date]
        f = {}
        for k in (5, 15, 60, 240):
            f[f"r{k}"] = (C - self.close_asof(t - pd.Timedelta(minutes=k))) / atr
        f["r_day"] = 100 * np.log(C / today["open"].iloc[0])
        f["atr_rel20"] = atr / self.hist(date, clock, self.atr_at, "mean")
        w = past[past["tclose"] > t - pd.Timedelta(minutes=60)]
        f["range60"] = (w["high"].max() - w["low"].min()) / atr
        f["rv30_rel"] = self.rv30_at(t) / self.hist(date, clock, self.rv30_at, "median")
        hi, lo = today["high"].max(), today["low"].min()
        f["pos_day"] = (C - lo) / (hi - lo) if hi > lo else 0.5
        k = self.dates.index(date)
        if k > 0:
            prev = self.df[self.df["date"] == self.dates[k - 1]]
            f["d_pdh"] = (C - prev["high"].max()) / atr
            f["d_pdl"] = (C - prev["low"].min()) / atr
        else:
            f["d_pdh"] = f["d_pdl"] = np.nan
        res = self.resume(date)
        a_start = res if res < date + pd.Timedelta(hours=8) else today["tclose"].iloc[0]
        a_end = min(date + pd.Timedelta(hours=8), t)
        asia = today[(today["tclose"] >= a_start) & (today["tclose"] <= a_end)]
        f["d_asia_hi"] = (C - asia["high"].max()) / atr if len(asia) else np.nan
        f["d_asia_lo"] = (C - asia["low"].min()) / atr if len(asia) else np.nan
        f["d_open"] = (C - today["open"].iloc[0]) / atr
        # structure
        closes = list(m5["close"])
        run = 0
        for i in range(len(closes) - 1, 0, -1):
            d = np.sign(closes[i] - closes[i - 1])
            if d == 0 or (run != 0 and np.sign(run) != d):
                break
            run += d
        f["consec"] = float(run)
        m5d = m5[m5.index.normalize() == date]
        hs, ls = list(m5d["high"]), list(m5d["low"])
        ih = max(i for i, v in enumerate(hs) if v == max(hs))
        il = max(i for i, v in enumerate(ls) if v == min(ls))
        f["bars_since_high"] = float(len(hs) - 1 - ih)
        f["bars_since_low"] = float(len(ls) - 1 - il)
        last12 = m5.iloc[-12:]
        if len(last12) == 12:
            den = last12["high"].max() - last12["low"].min()
            f["overlap12"] = (last12["high"] - last12["low"]).sum() / den if den > 0 else np.nan
        else:
            f["overlap12"] = np.nan
        # activity
        f["tv_rel"] = self.tv15_at(t) / self.hist(date, clock, self.tv15_at, "median")
        prev20 = self.dates[max(0, k - 20):k]
        if len(prev20) >= 10:
            f["spread_rel"] = past["spread_pts"].iloc[-1] / np.median(
                self.df[self.df["date"].isin(prev20)]["spread_pts"])
        else:
            f["spread_rel"] = np.nan
        # calendar
        f["min_since_resume"] = (t - res) / ONE
        hm = clock / ONE
        f["hour_bucket"] = float(sum(hm >= b for b in (480, 600, 780, 990, 1080, 1290)))
        f["weekday"] = float(t.weekday())
        # previous day
        if k > 0:
            dd = self.daily(self.dates[k - 1])
            atr_d = self.wilder(dd["high"], dd["low"], dd["close"])[-1]
            f["pd_ret"] = (dd["close"].iloc[-1] - dd["open"].iloc[-1]) / atr_d
            rng = (dd["high"] - dd["low"]).to_numpy()
            f["pd_range_rel"] = rng[-1] / np.median(rng[-20:]) if len(rng) >= 10 else np.nan
        else:
            f["pd_ret"] = f["pd_range_rel"] = np.nan
        return pd.Series(f)[list(FEATURES)].astype(float), atr


# ----------------------------------------------------------------------------- tests

@pytest.fixture(scope="module")
def series():
    return make_series()


@pytest.fixture(scope="module")
def vec(series):
    return vectorised(series)


def test_feature_list_is_frozen():
    assert len(FEATURES) == 25 and len(set(FEATURES)) == 25


def test_bruteforce_equality(series, vec):
    F, atr, _, _ = vec
    brute = Brute(series)
    rng = np.random.default_rng(11)
    # moments from every part of the sample: warm-up days, first moments after resume, late moments
    idx = sorted(set(rng.choice(len(F), 140, replace=False).tolist()) | {0, 1, len(F) - 1})
    first_of_day = np.flatnonzero(np.r_[True, F.index.normalize()[1:] != F.index.normalize()[:-1]])
    idx = sorted(set(idx) | set(first_of_day[::3].tolist()))
    n_finite = 0
    for i in idx:
        t = F.index[i]
        bf, bf_atr = brute.features(t)
        assert bf_atr == pytest.approx(atr[i], rel=1e-10, abs=1e-12) or (np.isnan(bf_atr) and np.isnan(atr[i]))
        got = F.iloc[i]
        for name in FEATURES:
            a, b = got[name], bf[name]
            if np.isnan(b):
                assert np.isnan(a), f"{name} at {t}: vectorised {a}, brute force NaN"
            else:
                n_finite += 1
                assert a == pytest.approx(b, rel=1e-9, abs=1e-9), f"{name} at {t}: {a} vs {b}"
    assert n_finite > 100 * 20          # the comparison really covered complete feature rows


def test_features_complete_after_warmup(vec):
    F, _, _, _ = vec
    days = F.index.normalize().unique()
    # the longest warm-up is the daily Wilder ATR(14) behind pd_ret (needs 14 days)
    assert F[F.index.normalize() < days[14]]["pd_ret"].isna().all()
    late = F[F.index.normalize() >= days[15]]
    assert late.notna().all(axis=1).mean() > 0.99


def test_lookahead_mutating_future_bars_changes_nothing(series, vec):
    F, atr, _, _ = vec
    rng = np.random.default_rng(99)
    for cut in (F.index[len(F) // 2], F.index[int(len(F) * 0.8)] , F.index[len(F) // 3]):
        df2 = series.copy()
        fut = df2["time"] + ONE > cut                 # bars not completed at t = cut
        n = int(fut.sum())
        shift = rng.normal(0, 25, n)
        for col in ("open", "high", "low", "close"):
            df2.loc[fut, col] = df2.loc[fut, col] * rng.uniform(0.8, 1.2) + shift
        df2.loc[fut, "high"] = df2.loc[fut, ["open", "high", "low", "close"]].max(axis=1) + 3
        df2.loc[fut, "low"] = df2.loc[fut, ["open", "high", "low", "close"]].min(axis=1) - 3
        df2.loc[fut, "spread_pts"] = rng.integers(1, 500, n)
        df2.loc[fut, "tick_volume"] = rng.integers(1, 5000, n)
        drop = fut & (rng.random(len(df2)) < 0.2)     # and delete some future bars
        df2 = df2.loc[~drop].reset_index(drop=True)
        F2, atr2, _, _ = vectorised(df2)
        a = F[F.index <= cut]
        b = F2.reindex(a.index)
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        assert np.array_equal(atr[: len(a)], atr2[: len(a)], equal_nan=True)
        # sanity: the mutation did change features after the cut
        after = F.index[(F.index > cut)].intersection(F2.index)
        assert not F.loc[after].equals(F2.loc[after])


def test_atr_scaling_invariance(series, vec):
    F, atr, _, _ = vec
    df2 = series.copy()
    k, a = 2.5, 400.0                                 # affine price change a + k * p
    for col in ("open", "high", "low", "close"):
        df2[col] = a + k * df2[col]
    F2, atr2, _, _ = vectorised(df2)
    ok = np.isfinite(atr)
    assert np.allclose(atr2[ok], k * atr[ok], rtol=1e-9)
    for name in ATR_SCALED + ("pos_day", "overlap12", "atr_rel20", "consec", "bars_since_high",
                              "bars_since_low", "min_since_resume", "tv_rel", "spread_rel"):
        np.testing.assert_allclose(F2[name].to_numpy(), F[name].to_numpy(), rtol=1e-8, atol=1e-8,
                                   equal_nan=True, err_msg=name)
    # a pure level shift (k = 1) leaves every ATR-unit feature unchanged too, but moves r_day
    df3 = series.copy()
    for col in ("open", "high", "low", "close"):
        df3[col] = df3[col] + 100.0
    F3, _, _, _ = vectorised(df3)
    for name in ATR_SCALED:
        np.testing.assert_allclose(F3[name].to_numpy(), F[name].to_numpy(), rtol=1e-8, atol=1e-8,
                                   equal_nan=True, err_msg=name)
    assert not np.allclose(F3["r_day"].dropna(), F["r_day"].dropna())


def test_wilder_atr_small_hand_case():
    h = [10, 12, 11, 13, 12]
    l = [8, 9, 9, 10, 11]
    c = [9, 11, 10, 12, 11.5]
    # TR = [2, 3, 2, 3, 1]; ATR(3): [nan, nan, 7/3, (7/3*2+3)/3, ((7/3*2+3)/3*2+1)/3]
    a3 = 7 / 3
    a4 = (a3 * 2 + 3) / 3
    a5 = (a4 * 2 + 1) / 3
    got = wilder_atr(h, l, c, 3)
    assert np.isnan(got[:2]).all()
    assert got[2:] == pytest.approx([a3, a4, a5])
