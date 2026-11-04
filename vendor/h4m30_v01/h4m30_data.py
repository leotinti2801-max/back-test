"""OPTIMUS H4M30_STRUCTURE V01 - M1 grid, bars, pivots and ATR (spec H4_M30_V02 sections 2-4).

Pure functions except frame_from_verified_bytes (unpickles bytes whose SHA256 was checked first).
Conventions:
  * M1 index = minute open in UTC; a minute is present only if the cache has a row for it.
  * Bars are anchored on UTC (H4: 00,04,..,20; M30: :00/:30), closed left, labelled right
    (available at their close). A bar is complete only if all its M1 are present (240 / 30).
  * Structure uses mid prices. Missing minutes are never filled; incomplete bars carry NaN.
  * Pivot: strict high/low against two complete consecutive bars on each side;
    pivot_time = close of the centre bar, known_at = close of the second right bar.
  * ATR14: arithmetic mean (math.fsum) of 14 true ranges on 15 complete consecutive bars;
    unknown (NaN) otherwise. Not Wilder.
Every reduction that feeds a decision is exact (max/min) or order independent (math.fsum), so
results do not depend on numpy SIMD paths or platform.
"""
import hashlib
import io
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_MS = 60_000
M30_MS = 30 * MIN_MS
H4_MS = 240 * MIN_MS
DAY_MS = 1440 * MIN_MS
SIDES = ("bid", "ask", "mid")
FIELDS = ("open", "high", "low", "close")
PRICE_COLS = tuple(f"{s}_{f}" for s in SIDES for f in FIELDS)
REQUIRED_COLS = PRICE_COLS + ("first_ts", "tick_count")


class DataError(ValueError):
    """Raised before any strategy calculation when the data identity or schema is not acceptable."""


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def iso(ms):
    """Exact UTC ISO-8601 text of an integer epoch-millisecond value."""
    ms = int(ms)
    sec, rem = divmod(ms, 1000)
    days, s = divmod(sec, 86400)
    d = np.datetime64(days, "D").astype(object)
    hh, r = divmod(s, 3600)
    mm, ss = divmod(r, 60)
    base = f"{d.year:04d}-{d.month:02d}-{d.day:02d}T{hh:02d}:{mm:02d}:{ss:02d}"
    return base + (f".{rem:03d}Z" if rem else "Z")


def utc_date(ms):
    return iso(int(ms) // DAY_MS * DAY_MS)[:10]


def frame_from_verified_bytes(raw, expected_sha256, expected_bytes=None):
    """Unpickle the exact bytes whose SHA256 (and size) were verified. A pickle can execute code:
    nothing is unpickled unless the identity matches."""
    actual = sha256_bytes(raw)
    if actual != expected_sha256:
        raise DataError(f"DATA_SHA256_MISMATCH: got {actual}, nothing unpickled")
    if expected_bytes is not None and len(raw) != int(expected_bytes):
        raise DataError(f"DATA_SIZE_MISMATCH: got {len(raw)} bytes, nothing unpickled")
    df = pd.read_pickle(io.BytesIO(raw))
    validate_frame(df)
    return df


def index_ms(df):
    idx = pd.DatetimeIndex(df.index)
    return idx.as_unit("ns").asi8 // 1_000_000


def validate_frame(df):
    """Schema and consistency checks (explicit exceptions, active under python -O).
    Returns a dict of descriptive data-quality measures (no repair is ever made)."""
    if not isinstance(df, pd.DataFrame):
        raise DataError("M1 cache is not a pandas DataFrame")
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise DataError(f"M1 cache columns missing: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None or str(df.index.tz) != "UTC":
        raise DataError("M1 index must be a UTC timezone-aware DatetimeIndex")
    if not (df.index.is_monotonic_increasing and df.index.is_unique):
        raise DataError("M1 index must be strictly increasing and unique")
    t = index_ms(df)
    if len(t) and np.any(t % MIN_MS):
        raise DataError("M1 index must be aligned on whole UTC minutes (minute open)")
    px = df[list(PRICE_COLS)].to_numpy(dtype=float)
    if not (np.isfinite(px).all() and (px > 0).all()):
        raise DataError("prices must be finite and strictly positive")
    for s in SIDES:
        h, lo = df[f"{s}_high"].to_numpy(float), df[f"{s}_low"].to_numpy(float)
        o, c = df[f"{s}_open"].to_numpy(float), df[f"{s}_close"].to_numpy(float)
        if not ((h >= lo).all() and (h >= o).all() and (h >= c).all() and (lo <= o).all() and (lo <= c).all()):
            raise DataError(f"{s} OHLC inconsistent (high/low do not bound open/close)")
    for f in ("open", "close"):
        b, a, m = (df[f"{s}_{f}"].to_numpy(float) for s in SIDES)
        if not ((a >= b).all() and (m >= b).all() and (m <= a).all()):
            raise DataError(f"{f}: requires bid <= mid <= ask on the same quote")
    first = df["first_ts"].to_numpy(dtype=float)
    if not (np.isfinite(first).all() and (first >= t).all() and (first < t + MIN_MS).all()):
        raise DataError("first_ts must be epoch milliseconds inside its own minute")
    if not (df["tick_count"].to_numpy() > 0).all():
        raise DataError("tick_count must be > 0 on every present minute")
    dev_open = np.abs(df["mid_open"].to_numpy(float) - (df["bid_open"].to_numpy(float) + df["ask_open"].to_numpy(float)) / 2)
    dev_close = np.abs(df["mid_close"].to_numpy(float) - (df["bid_close"].to_numpy(float) + df["ask_close"].to_numpy(float)) / 2)
    return {"rows": int(len(df)), "first_minute_utc": iso(t[0]) if len(t) else None,
            "last_minute_utc": iso(t[-1]) if len(t) else None,
            "max_abs_mid_open_minus_bid_ask_half_sum": float(dev_open.max()) if len(t) else None,
            "max_abs_mid_close_minus_bid_ask_half_sum": float(dev_close.max()) if len(t) else None}


@dataclass
class Market:
    """Calendar minute grid [origin_ms, end_ms) with NaN where the cache has no row."""
    origin_ms: int
    end_ms: int
    n: int
    present: np.ndarray
    px: dict
    first_ts: np.ndarray
    quality_rows_removed: int
    quality_minutes: np.ndarray
    closure_minutes: np.ndarray

    def t(self, i):
        return self.origin_ms + int(i) * MIN_MS

    def idx(self, ms):
        return (int(ms) - self.origin_ms) // MIN_MS


def build_market(df, origin_ms, end_ms, quality=(), closures=()):
    """Grid of the minutes in [origin_ms, end_ms). origin and end must be H4 aligned (00:00 UTC
    origin). Minutes inside a supplied quality interval are treated as absent even if a row exists
    (the interval status is reported, never repaired). `closures` are market closures supplied WITH
    a cited source (run specification); they are never inferred from holes. A row inside a supplied
    closure contradicts the evidence and is refused."""
    origin_ms, end_ms = int(origin_ms), int(end_ms)
    if origin_ms % DAY_MS or end_ms % H4_MS or not origin_ms < end_ms:
        raise DataError("grid origin must be 00:00 UTC and end H4 aligned with origin < end")
    n = (end_ms - origin_ms) // MIN_MS
    t = index_ms(df)
    sel = (t >= origin_ms) & (t < end_ms)
    qmask = np.zeros(n, dtype=bool)
    removed = 0
    for q in quality:
        a = max(0, (q["start_ms"] - origin_ms) // MIN_MS)
        b = min(n, (q["end_ms"] - origin_ms) // MIN_MS)
        if a < b:
            qmask[a:b] = True
        inside = sel & (t >= q["start_ms"]) & (t < q["end_ms"])
        removed += int(inside.sum())
        sel &= ~((t >= q["start_ms"]) & (t < q["end_ms"]))
    cmask = np.zeros(n, dtype=bool)
    for q in closures:
        a = max(0, (q["start_ms"] - origin_ms) // MIN_MS)
        b = min(n, (q["end_ms"] - origin_ms) // MIN_MS)
        if a < b:
            cmask[a:b] = True
        if np.any(sel & (t >= q["start_ms"]) & (t < q["end_ms"])):
            raise DataError(f"quotes present inside a supplied closure interval ({q['source']}): evidence contradicted")
    ii = (t[sel] - origin_ms) // MIN_MS
    present = np.zeros(n, dtype=bool)
    present[ii] = True
    px = {}
    for c in PRICE_COLS:
        arr = np.full(n, np.nan)
        arr[ii] = df[c].to_numpy(dtype=float)[sel]
        px[c] = arr
    first = np.full(n, np.nan)
    first[ii] = df["first_ts"].to_numpy(dtype=float)[sel]
    return Market(origin_ms, end_ms, n, present, px, first, removed, qmask, cmask)


@dataclass
class Bars:
    tf: str
    minutes: int
    period_ms: int
    origin_ms: int
    n: int
    m1_count: np.ndarray
    complete: np.ndarray
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    bid_low: np.ndarray
    ask_high: np.ndarray
    bid_high: np.ndarray
    ask_low: np.ndarray

    def open_ms(self, s):
        return self.origin_ms + int(s) * self.period_ms

    def close_ms(self, s):
        return self.origin_ms + (int(s) + 1) * self.period_ms

    def slot_of_close(self, ms):
        return (int(ms) - self.origin_ms) // self.period_ms - 1


def make_bars(market, minutes, tf):
    """Aggregate the grid into bars of `minutes` M1. Values are NaN for incomplete bars."""
    k = int(minutes)
    if market.n % k:
        raise DataError("grid length must be a multiple of the bar length")
    nb = market.n // k
    pres = market.present.reshape(nb, k)
    count = pres.sum(axis=1)
    complete = count == k

    def agg(col, how):
        out = np.full(nb, np.nan)
        if not complete.any():
            return out
        sub = market.px[col].reshape(nb, k)[complete]
        if how == "first":
            v = sub[:, 0]
        elif how == "last":
            v = sub[:, k - 1]
        elif how == "max":
            v = sub.max(axis=1)
        else:
            v = sub.min(axis=1)
        out[complete] = v
        return out

    return Bars(tf, k, k * MIN_MS, market.origin_ms, nb, count.astype(np.int64), complete,
                agg("mid_open", "first"), agg("mid_high", "max"), agg("mid_low", "min"),
                agg("mid_close", "last"), agg("bid_low", "min"), agg("ask_high", "max"),
                agg("bid_high", "max"), agg("ask_low", "min"))


@dataclass(frozen=True)
class Pivot:
    pid: str
    tf: str
    kind: str          # "HIGH" or "LOW"
    center: int
    pivot_time_ms: int
    known_at_ms: int
    price: float       # mid high (HIGH) or mid low (LOW) of the centre bar
    bid_high: float
    ask_low: float


def find_pivots(bars):
    """Strict pivots on five complete consecutive bars; returned sorted by (known_at, kind)."""
    out = []
    c, h, lo = bars.complete, bars.high, bars.low
    for s in range(2, bars.n - 2):
        if not (c[s - 2] and c[s - 1] and c[s] and c[s + 1] and c[s + 2]):
            continue
        pt, ka = bars.close_ms(s), bars.close_ms(s + 2)
        if h[s] > h[s - 2] and h[s] > h[s - 1] and h[s] > h[s + 1] and h[s] > h[s + 2]:
            out.append(Pivot(f"{bars.tf}H@{pt}", bars.tf, "HIGH", s, pt, ka, float(h[s]),
                             float(bars.bid_high[s]), float(bars.ask_low[s])))
        if lo[s] < lo[s - 2] and lo[s] < lo[s - 1] and lo[s] < lo[s + 1] and lo[s] < lo[s + 2]:
            out.append(Pivot(f"{bars.tf}L@{pt}", bars.tf, "LOW", s, pt, ka, float(lo[s]),
                             float(bars.bid_high[s]), float(bars.ask_low[s])))
    out.sort(key=lambda p: (p.known_at_ms, p.kind))
    return out


def true_ranges(bars):
    tr = np.full(bars.n, np.nan)
    c = bars.complete
    for s in range(1, bars.n):
        if c[s] and c[s - 1]:
            pc = bars.close[s - 1]
            tr[s] = max(bars.high[s] - bars.low[s], abs(bars.high[s] - pc), abs(bars.low[s] - pc))
    return tr


def atr_at_close(bars, period=14):
    """atr[s] = mean of the true ranges of bars s-period+1..s; needs bars s-period..s complete."""
    tr = true_ranges(bars)
    out = np.full(bars.n, np.nan)
    c = bars.complete
    run = 0
    for s in range(bars.n):
        run = run + 1 if c[s] else 0
        if run >= period + 1:
            out[s] = math.fsum(float(x) for x in tr[s - period + 1:s + 1]) / period
    return out
