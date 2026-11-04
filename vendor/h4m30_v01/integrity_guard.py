"""Research guard for unresolved M1 execution coverage, V02. NOT EXECUTED.
A contiguous M1 grid is not proof of complete ticks; a missing M1 row is not proof of lost ticks.
This module never resolves a path, it only describes the hole. No market data, network or broker.
"""
import operator

MINUTE_MS = 60_000


class ExecutionPathUnknown(RuntimeError):
    def __init__(self, reason, *, entry_ms=None, previous_ms=None, current_ms=None,
                 missing_minutes=None, gap_class=None):
        self.event = {
            "status": "UNRESOLVED_EXECUTION", "reason": reason, "entry_ms": entry_ms,
            "previous_ms": previous_ms, "current_ms": current_ms,
            "missing_minutes": missing_minutes, "gap_class": gap_class,
            "total_net_pnl": None, "performance_publishable": False,
            "tick_completeness_certified": False,
        }
        super().__init__(reason)

    def attach_known_state(self, realized_per_unit, remaining_fraction, fills):
        # Realized partial cash flows are retained; they are NOT total trade PnL.
        self.event["known_realized_per_unit"] = float(realized_per_unit)
        self.event["remaining_fraction"] = float(remaining_fraction)
        self.event["known_fills"] = [dict(fill) for fill in fills]
        return self


def classify_step(previous, current, closure_evidence=()):
    delta = current - previous
    if delta <= 0:
        return None, "NON_MONOTONIC_OR_DUPLICATE_CLOCK"
    if delta < MINUTE_MS:
        return None, "IRREGULAR_SUBMINUTE_STEP"
    if delta % MINUTE_MS:
        return None, "IRREGULAR_STEP_NOT_WHOLE_MINUTES"
    missing = delta // MINUTE_MS - 1
    lo, hi = previous + MINUTE_MS, current
    for start, end in closure_evidence:
        if start <= lo and end >= hi:
            # A closure explains absent rows but the position still crosses an unobserved interval.
            return missing, "SUPPLIED_CLOSURE_EVIDENCE_COVERS_HOLE_PATH_STILL_UNRESOLVED"
    return missing, "UNCLASSIFIED_MISSING_M1"


def require_next_m1(previous_ms, current_ms, *, entry_ms=None, closure_evidence=()):
    """Only the next observed timestamp is used, never a future gap filter."""
    try:
        if isinstance(previous_ms, bool) or isinstance(current_ms, bool):
            raise TypeError("boolean clock")
        previous = operator.index(previous_ms)
        current = operator.index(current_ms)
    except TypeError:
        raise ExecutionPathUnknown("INVALID_M1_CLOCK", entry_ms=entry_ms)
    if current - previous != MINUTE_MS:
        missing, gap_class = classify_step(previous, current, closure_evidence)
        raise ExecutionPathUnknown(
            "UNRESOLVED_M1_STEP", entry_ms=entry_ms,
            previous_ms=int(previous), current_ms=int(current),
            missing_minutes=missing, gap_class=gap_class)
