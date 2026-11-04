"""OPTIMUS H4M30_STRUCTURE V01 - event engine (spec H4_M30_V02 sections 4-9).

One simulation = one configuration on one window [start, end), preceded by a warm-up that starts
at the grid origin. The engine walks every minute boundary t (the M1 [t-1min, t) has just closed)
in a fixed order, documented in CAHIER_CONFORMITE.md (point I-04):
  A. close a position whose closed_at <= t (balance, USER_RULES streak and pause);
  B. H4 close at t: bias state; an active setup whose direction no longer matches a known state
     expires (SUSPENDED_MISSING_H4 does not expire it but blocks decisions);
  C. setup expiry when t >= creation + 24 x 30 min;
  D. the M1 that just closed: target revisit, first return and decision (entry at t), or, if the
     M1 is missing, hidden-event analysis (unknown state, or halt if an entry could have existed);
  E. M30 close at t: zone invalidation, breakouts (setup creation/replacement), M30 pivots
     confirmed at t (target arming).
Unknown handling (spec section 4): a missing M1 after a setup's creation may hide its first return
or a target revisit -> the setup state becomes UNKNOWN (period coverage PARTIAL), unless the minute
lies in a market closure supplied with a cited source in the run specification (never inferred). The branch halts
(result unknown) as soon as an entry could have opened without its existence being determinable:
hidden first return with an otherwise executable entry, missing entry row, or an executable entry
from a setup whose state is UNKNOWN. A gap during an exposure halts as UNRESOLVED_EXECUTION.
No market data is read here; no network, broker or order.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np

import h4m30_bias as B
import h4m30_data as D
import h4m30_execution as X
from integrity_guard import ExecutionPathUnknown

MIN_MS = D.MIN_MS
M30_MS = D.M30_MS
H4_MS = D.H4_MS
DAY_MS = D.DAY_MS


# ----------------------------------------------------------------------------- context
@dataclass
class BosEvent:
    seq: int
    slot: int
    open_ms: int
    close_ms: int
    direction: int
    level_pid: str
    level_price: float
    level_pivot_time_ms: int
    level_known_at_ms: int
    bar_open: float
    bar_close: float
    body: float
    atr_ref: float
    bias_state: str
    poi_slot: object
    zone_lo: object
    zone_hi: object
    poi_bid_low: object
    poi_ask_high: object
    static_reasons: list
    caveats: list


@dataclass
class Context:
    market: object
    m30: object
    h4: object
    m30_pivots: list
    h4_pivots: list
    atr: object
    bias_records: list
    bias: object
    bos: list


def breakout_events(m30, pivots, atr, bias, params):
    """Deterministic level crossings (spec section 4 and decision D). The level of a direction is the
    last M30 pivot of that kind with known_at <= bar open. It is consumed by the first COMPLETE M30
    close strictly beyond it, admissible or not. Dynamic conditions (position, pause) are applied by
    the simulation."""
    lookback = params["poi"]["lookback_m30"]
    body_min = params["breakout"]["body_atr_min"]
    queues = {1: [p for p in pivots if p.kind == "HIGH"], -1: [p for p in pivots if p.kind == "LOW"]}
    for q in queues.values():
        q.sort(key=lambda p: (p.known_at_ms, p.pivot_time_ms))
    ptr = {1: 0, -1: 0}
    cur = {1: None, -1: None}
    consumed = set()
    incomplete_seen = set()
    events = []
    for b in range(m30.n):
        open_ms = m30.open_ms(b)
        close_ms = open_ms + m30.period_ms
        for d in (1, -1):
            q = queues[d]
            while ptr[d] < len(q) and q[ptr[d]].known_at_ms <= open_ms:
                cur[d] = q[ptr[d]]
                ptr[d] += 1
        for d in (1, -1):
            lvl = cur[d]
            if lvl is None or lvl.pid in consumed:
                continue
            if not m30.complete[b]:
                incomplete_seen.add(lvl.pid)
                continue
            c, o = float(m30.close[b]), float(m30.open[b])
            if not ((c > lvl.price) if d == 1 else (c < lvl.price)):
                continue
            consumed.add(lvl.pid)
            reasons = []
            state = bias.state_at(close_ms)
            if state != B.DIRECTION_STATE[d]:
                reasons.append("BIAS_" + state)
            if not ((c > o) if d == 1 else (c < o)):
                reasons.append("CANDLE_NOT_IN_BREAKOUT_DIRECTION")
            atr_ref = float(atr[b - 1]) if b >= 1 else float("nan")
            body = abs(c - o)
            if not math.isfinite(atr_ref):
                reasons.append("ATR_UNKNOWN_AT_BAR_OPEN")
            elif body < body_min * atr_ref:
                reasons.append("BODY_BELOW_1_ATR")
            poi = None
            if b < lookback or not all(bool(x) for x in m30.complete[b - lookback:b]):
                reasons.append("POI_WINDOW_INCOMPLETE")
            else:
                for j in range(b - 1, b - lookback - 1, -1):
                    oj, cj = float(m30.open[j]), float(m30.close[j])
                    if (cj < oj) if d == 1 else (cj > oj):
                        poi = j
                        break
                if poi is None:
                    reasons.append("NO_OPPOSITE_CANDLE_IN_POI_WINDOW")
            caveats = ["INCOMPLETE_M30_BETWEEN_LEVEL_AVAILABILITY_AND_CROSSING"] if lvl.pid in incomplete_seen else []
            events.append(BosEvent(
                seq=len(events), slot=b, open_ms=open_ms, close_ms=close_ms, direction=d, level_pid=lvl.pid,
                level_price=lvl.price, level_pivot_time_ms=lvl.pivot_time_ms, level_known_at_ms=lvl.known_at_ms,
                bar_open=o, bar_close=c, body=body, atr_ref=atr_ref, bias_state=state,
                poi_slot=poi, zone_lo=None if poi is None else float(m30.low[poi]),
                zone_hi=None if poi is None else float(m30.high[poi]),
                poi_bid_low=None if poi is None else float(m30.bid_low[poi]),
                poi_ask_high=None if poi is None else float(m30.ask_high[poi]),
                static_reasons=reasons, caveats=caveats))
    return events


def build_context(market, params, bias_records=None):
    """All deterministic structures of a market grid. `bias_records` lets controls supply an H4
    state sequence directly (pure-function design); the launcher never passes it."""
    m30 = D.make_bars(market, params["clock"]["m30_required_m1"], "M30")
    h4 = D.make_bars(market, params["clock"]["h4_required_m1"], "H4")
    p30 = D.find_pivots(m30)
    p4 = D.find_pivots(h4)
    atr = D.atr_at_close(m30, params["atr"]["period"])
    recs = B.compute_bias(h4, p4) if bias_records is None else list(bias_records)
    timeline = B.BiasTimeline(market.origin_ms, recs)
    bos = breakout_events(m30, p30, atr, timeline, params)
    return Context(market, m30, h4, p30, p4, atr, recs, timeline, bos)


# ----------------------------------------------------------------------------- simulation state
@dataclass
class Setup:
    setup_id: str
    direction: int
    created_ms: int
    bos: object
    zone_lo: float
    zone_hi: float
    stop: float
    expiry_ms: int
    target: object = None
    target_pid: object = None
    target_pivot_time_ms: object = None
    target_known_at_ms: object = None
    uncertain_since_ms: object = None
    uncertain_reasons: list = field(default_factory=list)
    hidden_minutes: int = 0


PARIS = ZoneInfo("Europe/Paris")


def paris_minute(t_ms):
    dt = datetime.fromtimestamp(int(t_ms) // 1000, tz=PARIS)
    return dt.hour * 60 + dt.minute, dt.strftime("%Y-%m-%dT%H:%M:%S%z")


class Simulation:
    def __init__(self, ctx, params, start_ms, end_ms):
        if not (ctx.market.origin_ms <= start_ms < end_ms == ctx.market.end_ms):
            raise ValueError("window must lie inside the grid and end exactly at the grid end "
                             "(no data at or after the window end is ever loaded)")
        self.ctx, self.p = ctx, params
        self.mk = ctx.market
        self.start_ms, self.end_ms = int(start_ms), int(end_ms)
        self.user = params["user_rules"]
        self.fee = params["costs"]["fee_round_trip_quote"]
        self.tick = params["costs"]["tick_quote"]
        self.capital = params["account"]["capital_eur"]
        self.balance = self.capital
        self.setup = None
        self.pos = None
        self.last_entry_day = None
        self.streak = 0
        self.pause_start = self.pause_end = None
        self.warm_uncertain_until = self.mk.origin_ms
        self.halt = None
        self.setup_events, self.decisions, self.trades = [], [], []
        self.unknown_minutes_by_day = {}
        self.unknown_decisions_by_day = {}
        self.counters = {}
        self._n_setups = 0
        self.unresolved_exposure = None
        self.bos_by_close = {}
        for ev in ctx.bos:
            self.bos_by_close.setdefault(ev.close_ms, []).append(ev)
        self.pivots_by_known = {}
        for p in ctx.m30_pivots:
            self.pivots_by_known.setdefault(p.known_at_ms, []).append(p)

    # ------------------------------------------------------------------ journal helpers
    def count(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1

    def in_window(self, t):
        return self.start_ms <= t < self.end_ms

    def log(self, t, event, s=None, **kw):
        row = {"seq": len(self.setup_events), "t_ms": int(t), "event": event,
               "setup_id": None if s is None else s.setup_id, "direction": None if s is None else s.direction,
               "in_window": self.in_window(t)}
        if s is not None:
            row.update(zone_lo=s.zone_lo, zone_hi=s.zone_hi, stop=s.stop, target=s.target,
                       target_pid=s.target_pid, target_known_at_ms=s.target_known_at_ms,
                       expiry_ms=s.expiry_ms, state_known=s.uncertain_since_ms is None,
                       uncertain_since_ms=s.uncertain_since_ms)
        row.update(kw)
        self.setup_events.append(row)
        self.count("EVENT_" + event)
        return row

    def end_setup(self, t, status, **kw):
        s = self.setup
        self.log(t, "SETUP_END", s, status=status, **kw)
        self.count("SETUP_END_" + status + ("" if s.uncertain_since_ms is None else "_STATE_UNKNOWN"))
        self.setup = None

    def mark_uncertain(self, s, t, reason):
        day = int(t - MIN_MS) // DAY_MS
        self.unknown_minutes_by_day[day] = self.unknown_minutes_by_day.get(day, 0) + 1
        s.hidden_minutes += 1
        if reason not in s.uncertain_reasons:
            s.uncertain_reasons.append(reason)
        if s.uncertain_since_ms is None:
            s.uncertain_since_ms = int(t)
            self.log(t, "SETUP_STATE_UNKNOWN", s, reasons=[reason], first_unobserved_minute_ms=int(t - MIN_MS))

    def do_halt(self, t, reason, **detail):
        self.halt = {"at_ms": int(t), "reason": reason, **detail}
        self.count("HALT_" + reason)
        if self.setup is not None:
            self.end_setup(t, "HALTED_" + reason)

    def balance_for(self, t):
        return self.balance if self.in_window(t) else self.capital

    # ------------------------------------------------------------------ decision helpers
    def decision_checks(self, t, s):
        reasons = []
        tod = (int(t) % DAY_MS) // MIN_MS
        e = self.p["entry"]
        if not (e["window_utc_start_minute"] <= tod < e["window_utc_end_minute_exclusive"]):
            reasons.append("FIRST_RETURN_OUTSIDE_ENTRY_WINDOW")
        pm, ptxt = paris_minute(t)
        if self.user is not None:
            if self.user["no_new_entry_paris_start_minute"] <= pm < self.user["no_new_entry_paris_end_minute_exclusive"]:
                reasons.append("PARIS_NO_ENTRY_15_30_17_00")
            if self.pause_start is not None and self.pause_start <= t < self.pause_end:
                reasons.append("PAUSE_AFTER_TWO_NET_LOSSES")
        state = self.ctx.bias.state_at(t)
        if state != B.DIRECTION_STATE[s.direction]:
            reasons.append("H4_BIAS_" + state)
        if t >= s.expiry_ms:
            reasons.append("SETUP_EXPIRED")
        if self.pos is not None:
            reasons.append("POSITION_OPEN")
        if self.last_entry_day is not None and self.last_entry_day == int(t) // DAY_MS:
            reasons.append("DAILY_ENTRY_LIMIT_REACHED")
        return reasons, state, ptxt

    def new_decision(self, s, kind, i, t):
        mk = self.mk
        dec = {"decision_id": f"{s.setup_id}-D{sum(1 for x in self.decisions if x['setup_id'] == s.setup_id) + 1}",
               "setup_id": s.setup_id, "kind": kind, "direction": s.direction,
               "return_m1_open_ms": int(t - MIN_MS), "decision_at_ms": int(t), "in_window": self.in_window(t),
               "m1_present": bool(mk.present[i]),
               "m1_mid_low": float(mk.px["mid_low"][i]) if mk.present[i] else None,
               "m1_mid_high": float(mk.px["mid_high"][i]) if mk.present[i] else None,
               "m1_mid_close": float(mk.px["mid_close"][i]) if mk.present[i] else None,
               "zone_lo": s.zone_lo, "zone_hi": s.zone_hi, "target": s.target,
               "target_known_at_ms": s.target_known_at_ms, "setup_state_known": s.uncertain_since_ms is None}
        self.decisions.append(dec)
        return dec

    def finish(self, dec, outcome, reasons=(), known=True):
        dec["outcome"] = outcome
        dec["reasons"] = list(reasons)
        dec["decision_known"] = bool(known)
        self.count("DECISION_" + outcome)
        if not known:
            day = dec["decision_at_ms"] // DAY_MS
            self.unknown_decisions_by_day[day] = self.unknown_decisions_by_day.get(day, 0) + 1

    def warm_unknown(self, t, horizon_ms):
        """Warm-up unknown: an uncounted position may have existed until horizon_ms. Any setup created
        before that time inherits an unknown state (no halt: warm-up trades are not counted)."""
        self.warm_uncertain_until = max(self.warm_uncertain_until, int(horizon_ms))
        self.count("WARMUP_UNKNOWN_EXPOSURE")

    def potential_horizon(self, t):
        day0 = int(t) // DAY_MS * DAY_MS
        return min(int(t) + self.p["exit"]["max_holding_minutes"] * MIN_MS,
                   day0 + self.p["exit"]["hard_exit_utc_minute"] * MIN_MS) + MIN_MS

    # ------------------------------------------------------------------ minute processing
    def visible(self, i, t):
        s, mk, d = self.setup, self.mk, self.setup.direction
        m = t - MIN_MS
        if s.target is not None and s.target_known_at_ms <= m:
            revisit = (mk.px["bid_high"][i] >= s.target + self.tick) if d == 1 else \
                      (mk.px["ask_low"][i] <= s.target - self.tick)
            if revisit:
                self.end_setup(t, "TARGET_REVISITED_BEFORE_ENTRY", revisit_m1_open_ms=int(m))
                return
        if not (mk.px["mid_low"][i] <= s.zone_hi and mk.px["mid_high"][i] >= s.zone_lo):
            return
        dec = self.new_decision(s, "VISIBLE_FIRST_RETURN", i, t)
        known = s.uncertain_since_ms is None
        if s.target is None or s.target_known_at_ms > m:
            self.finish(dec, "TARGET_NOT_KNOWN_AT_FIRST_RETURN", known=known)
            self.end_setup(t, "TARGET_NOT_KNOWN_AT_FIRST_RETURN", decision_id=dec["decision_id"])
            return
        if not (s.zone_lo <= mk.px["mid_close"][i] <= s.zone_hi):
            self.finish(dec, "RETURN_M1_CLOSED_OUTSIDE_ZONE", known=known)
            self.end_setup(t, "FIRST_RETURN_REFUSED", decision_id=dec["decision_id"])
            return
        reasons, state, ptxt = self.decision_checks(t, s)
        dec.update(h4_bias_state=state, paris_local_time=ptxt)
        if reasons:
            self.finish(dec, reasons[0], reasons, known=known)
            self.end_setup(t, "FIRST_RETURN_REFUSED", decision_id=dec["decision_id"])
            return
        e = i + 1
        if e >= mk.n or not mk.present[e]:
            dec["entry_row_present"] = False
            self.finish(dec, "ENTRY_UNKNOWN_ENTRY_ROW_MISSING", known=False)
            if self.in_window(t):
                self.do_halt(t, "ENTRY_UNKNOWN_ENTRY_ROW_MISSING", setup_id=s.setup_id, decision_id=dec["decision_id"])
            else:
                self.warm_unknown(t, self.potential_horizon(t))
                self.end_setup(t, "WARMUP_ENTRY_UNKNOWN", decision_id=dec["decision_id"])
            return
        chk = X.evaluate_entry(mk, e, s, self.p, self.balance_for(t))
        dec.update({k: v for k, v in chk.items() if k != "reasons"}, entry_row_present=True)
        if chk["reasons"]:
            outcome = "SKIPPED_SIZE_BELOW_MIN" if chk["reasons"][0] == "SIZE_BELOW_MIN" else chk["reasons"][0]
            self.finish(dec, outcome, chk["reasons"], known=known)
            self.end_setup(t, "FIRST_RETURN_REFUSED", decision_id=dec["decision_id"])
            return
        if not known:
            self.finish(dec, "ENTRY_UNKNOWN_SETUP_STATE_UNKNOWN", ["SETUP_MAY_HAVE_BEEN_CONSUMED_EARLIER"], known=False)
            if self.in_window(t):
                self.do_halt(t, "ENTRY_FROM_SETUP_WITH_UNKNOWN_STATE", setup_id=s.setup_id,
                             decision_id=dec["decision_id"], uncertain_since_ms=s.uncertain_since_ms,
                             uncertain_reasons=list(s.uncertain_reasons), potential_qty=chk["qty"],
                             potential_planned_risk_eur=chk["planned_risk_eur"])
            else:
                self.warm_unknown(t, self.potential_horizon(t))
                self.end_setup(t, "WARMUP_ENTRY_UNKNOWN", decision_id=dec["decision_id"])
            return
        self.enter(dec, s, e, chk, t)

    def hidden(self, i, t):
        """Missing M1 [t-1min, t) while a setup is alive: it may hide the first return or a revisit."""
        s, mk = self.setup, self.mk
        m = t - MIN_MS
        if mk.closure_minutes[i]:
            self.count("MISSING_M1_INSIDE_SUPPLIED_CLOSURE")
            return
        possible, why, chk = False, None, None
        if s.target is not None and s.target_known_at_ms <= m:
            reasons, state, ptxt = self.decision_checks(t, s)
            if not reasons:
                e = i + 1
                if e >= mk.n or not mk.present[e]:
                    possible, why = True, "ENTRY_ROW_ALSO_MISSING"
                else:
                    chk = X.evaluate_entry(mk, e, s, self.p, self.balance_for(t))
                    if not chk["reasons"]:
                        possible, why = True, "ENTRY_CONDITIONS_MET_AT_NEXT_OPEN"
        if possible:
            dec = self.new_decision(s, "HIDDEN_RETURN_POSSIBLE", i, t)
            if chk is not None:
                dec.update({k: v for k, v in chk.items() if k != "reasons"}, entry_row_present=True)
            else:
                dec["entry_row_present"] = False
            self.finish(dec, "ENTRY_UNKNOWN_HIDDEN_FIRST_RETURN", [why], known=False)
            if self.in_window(t):
                self.do_halt(t, "HIDDEN_FIRST_RETURN_COULD_HAVE_ENTERED", setup_id=s.setup_id,
                             decision_id=dec["decision_id"], unobserved_minute_ms=int(m), why=why)
                return
            self.warm_unknown(t, self.potential_horizon(t))
        self.mark_uncertain(s, t, "MISSING_M1_MAY_HIDE_FIRST_RETURN_OR_TARGET_REVISIT")

    def enter(self, dec, s, e, chk, t):
        counted = self.in_window(t)
        try:
            tr = X.structural_path(self.mk, e, s.direction, s.stop, s.target, self.p)
        except ExecutionPathUnknown as exc:
            self.finish(dec, "ENTERED_PATH_UNRESOLVED", known=True)
            q = chk["qty"]
            ev = exc.event
            known = ev.get("known_realized_per_unit")
            if counted:
                self.unresolved_exposure = {
                    "status": "UNRESOLVED_EXECUTION", "setup_id": s.setup_id, "decision_id": dec["decision_id"],
                    "entry_t_ms": int(t), "qty": q, "planned_risk_eur": chk["planned_risk_eur"],
                    "balance_before_eur": self.balance, "known_realized_eur_entry_commission": None if known is None else q * known,
                    "remaining_fraction": ev.get("remaining_fraction"), "total_pnl_eur": None, "event": ev}
                self.last_entry_day = int(t) // DAY_MS
                self.do_halt(t, "UNRESOLVED_EXECUTION", setup_id=s.setup_id, decision_id=dec["decision_id"],
                             gap_reason=ev.get("reason"), first_unobserved_minute_ms=ev.get("first_unobserved_minute_ms"))
            else:
                self.warm_unknown(t, self.potential_horizon(t))
                self.end_setup(t, "WARMUP_ENTERED_PATH_UNRESOLVED", decision_id=dec["decision_id"])
            return
        self.finish(dec, "ENTERED" if counted else "ENTERED_WARMUP_NOT_COUNTED", known=True)
        self.pos = {"trade": tr, "qty": chk["qty"], "planned_risk_eur": chk["planned_risk_eur"], "counted": counted,
                    "setup_id": s.setup_id, "decision_id": dec["decision_id"], "closed_at_ms": tr["closed_at_ms"],
                    "balance_before": self.balance_for(t)}
        self.last_entry_day = int(t) // DAY_MS
        self.end_setup(t, "ENTERED", decision_id=dec["decision_id"])

    def close_position(self):
        pos, tr = self.pos, self.pos["trade"]
        q = pos["qty"]
        net = q * tr["net_unit"]
        rec = {"trade_id": f"T{len(self.trades) + 1}", "counted": pos["counted"], "setup_id": pos["setup_id"],
               "decision_id": pos["decision_id"], "qty": q, "planned_risk_eur": pos["planned_risk_eur"],
               "net_eur": net, "R": net / pos["planned_risk_eur"], "balance_before": pos["balance_before"],
               "trade": tr}
        if pos["counted"]:
            self.balance += net
            rec["balance_after"] = self.balance
            if self.user is not None:
                if net < 0:
                    self.streak += 1
                elif net > 0:
                    self.streak = 0
                if self.streak >= self.user["pause_after_consecutive_net_losses"]:
                    self.pause_start = tr["closed_at_ms"]
                    self.pause_end = self.pause_start + self.user["pause_minutes"] * MIN_MS
                    self.log(self.pause_start, "PAUSE_START", None, pause_end_ms=self.pause_end, streak=self.streak)
                    if self.setup is not None:
                        self.end_setup(self.pause_start, "CANCELLED_PAUSE_START")
        else:
            rec["balance_after"] = None
        self.trades.append(rec)
        self.pos = None

    def handle_bos(self, ev, t):
        dyn = []
        if self.pos is not None:
            dyn.append("BOS_IGNORED_POSITION_OPEN")
        if self.user is not None and self.pause_start is not None and self.pause_start <= t < self.pause_end:
            dyn.append("BOS_IGNORED_PAUSE")
        reasons = dyn + list(ev.static_reasons)
        info = dict(bos_seq=ev.seq, level_pid=ev.level_pid, level_price=ev.level_price,
                    level_known_at_ms=ev.level_known_at_ms, bar_open_ms=ev.open_ms, bar_open_mid=ev.bar_open,
                    bar_close_mid=ev.bar_close, body=ev.body, atr_ref=ev.atr_ref,
                    body_over_atr=(ev.body / ev.atr_ref) if (math.isfinite(ev.atr_ref) and ev.atr_ref > 0) else None,
                    h4_bias_state=ev.bias_state, poi_slot_close_ms=None if ev.poi_slot is None else self.ctx.m30.close_ms(ev.poi_slot),
                    poi_zone_lo=ev.zone_lo, poi_zone_hi=ev.zone_hi, poi_bid_low=ev.poi_bid_low,
                    poi_ask_high=ev.poi_ask_high, caveats=list(ev.caveats))
        if reasons:
            self.log(t, "LEVEL_CROSSED_NO_SETUP", None, direction=ev.direction, reasons=reasons, **info)
            return
        if self.setup is not None:
            self.end_setup(t, "REPLACED_BY_NEW_BREAKOUT", replaced_by_bos_seq=ev.seq)
        self._n_setups += 1
        buf = self.p["risk"]["stop_atr_buffer"] * ev.atr_ref
        stop = ev.poi_bid_low - buf if ev.direction == 1 else ev.poi_ask_high + buf
        s = Setup(setup_id=f"S{self._n_setups}", direction=ev.direction, created_ms=int(t), bos=ev,
                  zone_lo=ev.zone_lo, zone_hi=ev.zone_hi, stop=stop,
                  expiry_ms=int(t) + self.p["setup"]["expiry_m30_intervals"] * M30_MS)
        self.setup = s
        self.log(t, "SETUP_CREATED", s, direction=ev.direction, reasons=[], **info)
        if t < self.warm_uncertain_until:
            self.mark_uncertain(s, t + MIN_MS, "WARMUP_UNCOUNTED_EXPOSURE_STATE_UNKNOWN")

    def arm_target(self, p, t):
        s = self.setup
        if s is None or s.target is not None or s.created_ms >= t:
            return
        if p.kind != ("HIGH" if s.direction == 1 else "LOW") or p.pivot_time_ms < s.created_ms:
            return
        beyond = (p.price > s.zone_hi) if s.direction == 1 else (p.price < s.zone_lo)
        if not beyond:
            self.log(t, "TARGET_CANDIDATE_NOT_BEYOND_ZONE", s, candidate_pid=p.pid, candidate_price=p.price)
            return
        s.target = p.bid_high if s.direction == 1 else p.ask_low
        s.target_pid, s.target_pivot_time_ms, s.target_known_at_ms = p.pid, p.pivot_time_ms, p.known_at_ms
        self.log(t, "TARGET_ARMED", s, target_pivot_time_ms=p.pivot_time_ms, target_pivot_mid=p.price)

    # ------------------------------------------------------------------ main loop
    def run(self):
        mk, ctx = self.mk, self.ctx
        origin = mk.origin_ms
        t = origin + MIN_MS
        while t < self.end_ms and self.halt is None:
            i = (t - origin) // MIN_MS - 1
            if self.pos is not None and t >= self.pos["closed_at_ms"]:
                self.close_position()
            if self.pause_end is not None and t >= self.pause_end:
                self.log(self.pause_end, "PAUSE_END", None, streak_before_reset=self.streak)
                self.streak = 0
                self.pause_start = self.pause_end = None
            rel = t - origin
            if rel % H4_MS == 0 and self.setup is not None:
                st = ctx.bias.state_at(t)
                if st != B.SUSPENDED and st != B.DIRECTION_STATE[self.setup.direction]:
                    self.end_setup(t, "EXPIRED_BIAS_CHANGE", h4_bias_state=st)
            if self.setup is not None and t >= self.setup.expiry_ms:
                self.end_setup(t, "EXPIRED_12H")
            if self.setup is not None and self.pos is None and t - MIN_MS >= self.setup.created_ms:
                if mk.present[i]:
                    self.visible(i, t)
                else:
                    self.hidden(i, t)
                if self.halt is not None:
                    break
            if rel % M30_MS == 0:
                b = rel // M30_MS - 1
                s = self.setup
                if s is not None and s.created_ms < t:
                    if ctx.m30.complete[b]:
                        c = float(ctx.m30.close[b])
                        if (c < s.zone_lo) if s.direction == 1 else (c > s.zone_hi):
                            self.end_setup(t, "INVALIDATED_M30_CLOSE_BEYOND_ZONE", m30_close_mid=c)
                    else:
                        a = b * 30
                        hole = ~mk.present[a:a + 30] & ~mk.closure_minutes[a:a + 30]
                        if hole.any():
                            self.mark_uncertain(s, t, "INCOMPLETE_M30_MAY_HIDE_ZONE_INVALIDATION")
                for ev in self.bos_by_close.get(t, ()):
                    self.handle_bos(ev, t)
                for p in self.pivots_by_known.get(t, ()):
                    self.arm_target(p, t)
            t += MIN_MS
        if self.halt is None:
            if self.pos is not None and self.pos["closed_at_ms"] <= self.end_ms:
                self.close_position()
            if self.pos is not None:
                self.do_halt(self.end_ms, "EXPOSURE_OPEN_AT_PERIOD_END")
            if self.setup is not None:
                self.end_setup(self.end_ms, "OPEN_AT_PERIOD_END")
        return self


def run_cell(market, params, start_ms, end_ms, ctx=None):
    ctx = build_context(market, params) if ctx is None else ctx
    return Simulation(ctx, params, start_ms, end_ms).run()
