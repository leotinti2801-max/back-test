"""OPTIMUS H4M30_STRUCTURE V01 - H4 bias state machine (spec H4_M30_V02 section 3, decision B).

At every H4 close, in this order:
  1. confirm the pivots whose known_at is this close (pivots need five complete consecutive H4);
  2. an incomplete H4 cannot certify the bias at its expected close: state SUSPENDED_MISSING_H4
     (no new entry) until the next complete H4; a hole neither removes nor lifts a lock;
  3. lock: after an invalidation the state is NEUTRAL_LOCKED; the lock is lifted only when a
     confirmed H4 pivot (high OR low) has pivot_time (centre close) > invalidation_time;
  4. candidate from the last two confirmed highs and the last two confirmed lows (by pivot_time):
     BULL if both rise strictly, BEAR if both fall strictly, NEUTRAL otherwise, UNKNOWN if fewer
     than two highs or two lows;
  5. invalidation on the current close: BULL candidate with close < last pivot low, or BEAR
     candidate with close > last pivot high -> new lock dated at this close (state NEUTRAL_LOCKED).
Only BULL and BEAR allow entries (in their own direction).
"""
from dataclasses import dataclass, field

H4_MS = 14_400_000
BULL = "BULL"
BEAR = "BEAR"
NEUTRAL = "NEUTRAL"
NEUTRAL_LOCKED = "NEUTRAL_LOCKED"
UNKNOWN = "UNKNOWN"
SUSPENDED = "SUSPENDED_MISSING_H4"
STATES = (BULL, BEAR, NEUTRAL, NEUTRAL_LOCKED, UNKNOWN, SUSPENDED)
DIRECTION_STATE = {1: BULL, -1: BEAR}


@dataclass
class BiasRecord:
    slot: int
    close_ms: int
    complete: bool
    m1_count: int
    close_mid: object
    newly_confirmed: list = field(default_factory=list)
    h1: object = None
    h2: object = None
    l1: object = None
    l2: object = None
    candidate: object = None
    invalidated_now: bool = False
    lock_released_by: object = None
    lock_active: bool = False
    invalidation_time_ms: object = None
    state: str = UNKNOWN


def _pv(p):
    return None if p is None else (p.pid, p.price)


def compute_bias(h4, pivots):
    """One BiasRecord per H4 slot; record.state applies from record.close_ms (inclusive)."""
    queue = sorted((p for p in pivots if p.tf == "H4"), key=lambda p: (p.known_at_ms, p.kind))
    k, highs, lows = 0, [], []
    lock, inv = False, None
    out = []
    for s in range(h4.n):
        close_ms = h4.close_ms(s)
        rec = BiasRecord(slot=s, close_ms=close_ms, complete=bool(h4.complete[s]), m1_count=int(h4.m1_count[s]),
                         close_mid=float(h4.close[s]) if h4.complete[s] else None)
        while k < len(queue) and queue[k].known_at_ms <= close_ms:
            p = queue[k]
            (highs if p.kind == "HIGH" else lows).append(p)
            rec.newly_confirmed.append(p.pid)
            k += 1
        if not h4.complete[s]:
            rec.state = SUSPENDED
        else:
            if lock:
                newer = [p for p in highs + lows if p.pivot_time_ms > inv]
                if newer:
                    lock = False
                    rec.lock_released_by = min(newer, key=lambda p: (p.known_at_ms, p.pivot_time_ms, p.kind)).pid
            if lock:
                rec.state = NEUTRAL_LOCKED
            else:
                if len(highs) < 2 or len(lows) < 2:
                    cand = UNKNOWN
                else:
                    h1, h2, l1, l2 = highs[-2], highs[-1], lows[-2], lows[-1]
                    rec.h1, rec.h2, rec.l1, rec.l2 = _pv(h1), _pv(h2), _pv(l1), _pv(l2)
                    if h2.price > h1.price and l2.price > l1.price:
                        cand = BULL
                    elif h2.price < h1.price and l2.price < l1.price:
                        cand = BEAR
                    else:
                        cand = NEUTRAL
                rec.candidate = cand
                close = float(h4.close[s])
                if (cand == BULL and close < lows[-1].price) or (cand == BEAR and close > highs[-1].price):
                    lock, inv = True, close_ms
                    rec.invalidated_now = True
                    rec.state = NEUTRAL_LOCKED
                else:
                    rec.state = cand
        rec.lock_active = lock
        rec.invalidation_time_ms = inv if lock else None
        out.append(rec)
    return out


class BiasTimeline:
    """state_at(t): state of the last H4 closed at or before t (UNKNOWN before the first close)."""

    def __init__(self, origin_ms, records):
        self.origin_ms = int(origin_ms)
        self.records = list(records)
        self.states = [r.state for r in self.records]

    def slot_at(self, t_ms):
        return (int(t_ms) - self.origin_ms) // H4_MS - 1

    def state_at(self, t_ms):
        k = self.slot_at(t_ms)
        if k < 0 or not self.states:
            return UNKNOWN
        return self.states[min(k, len(self.states) - 1)]
