"""OPTIMUS H4M30_STRUCTURE V01 - entry checks, sizing and structural trade path (spec sections 6-8).

Conventions shared with the V03 witness engine (backtest_research.py V03, trade_path):
  * entry at the open quote of the M1 that starts at the decision time: long ask_open + SLIP,
    short bid_open - SLIP; FX of entry = mid_open of that row; half FEE at entry, half at exit;
  * long liquidated on the bid, short on the ask; initial stop executed at the worse of the row
    open and the stop, plus SLIP (label SL_GAP when the open is already beyond the stop);
  * structural target = limit: needs a one-tick penetration (TICK) and is filled at the target
    without slippage or price improvement;
  * stop and target both reachable in the same M1: the stop wins (prudent convention, flagged);
  * deadline = min(entry + 240 min, 20:00 UTC of the entry date): exit at the open quote of the
    deadline row with SLIP, never using that row's high/low;
  * a missing M1 during the exposure, or no deadline quote, raises ExecutionPathUnknown
    (integrity_guard.py, unchanged from V03) carrying the known flows and the exposure.
Every EUR flow is converted at the mid_open of its own fill row (V03 flow accounting).
"""
import math

from integrity_guard import ExecutionPathUnknown, require_next_m1

MIN_MS = 60_000
DAY_MS = 86_400_000


def _costs(params):
    c = params["costs"]
    return c["fee_round_trip_quote"], c["slip_quote_per_market_execution"], c["tick_quote"], c["spread_multiplier"]


def size_position(params, risk_unit_eur, balance_eur, fx_entry, entry_price):
    """Quantity in EUR, rounded down to the step; same leverage rule as the V03 witness."""
    a = params["account"]
    q_budget = a["risk_budget_eur_per_position"] / risk_unit_eur
    q_leverage = a["leverage_max"] * balance_eur * fx_entry / entry_price
    q_raw = min(q_budget, q_leverage)
    qty = math.floor(q_raw / a["qty_step_eur"]) * a["qty_step_eur"]
    return float(qty), float(q_budget), float(q_leverage)


def evaluate_entry(market, e_i, setup, params, balance_eur):
    """Deterministic checks at the open of row e_i (= decision time). Every measurable value is
    returned for the journal; `reasons` lists all failed conditions in a fixed order (the first one
    is the refusal label). An empty list means the entry is executable."""
    fee, slip, tick, spread_mult = _costs(params)
    d = setup.direction
    t_e = market.t(e_i)
    px = market.px
    bid_o, ask_o, mid_o = float(px["bid_open"][e_i]), float(px["ask_open"][e_i]), float(px["mid_open"][e_i])
    out = {"entry_row_ms": t_e, "first_tick_delay_ms": float(market.first_ts[e_i]) - t_e,
           "entry_bid_open": bid_o, "entry_ask_open": ask_o, "entry_mid_open": mid_o}
    reasons = []
    if out["first_tick_delay_ms"] > params["entry"]["first_tick_max_delay_ms"]:
        reasons.append("FIRST_TICK_LATE")
    if not (setup.zone_lo <= mid_o <= setup.zone_hi):
        reasons.append("ENTRY_MOVED_OUTSIDE_ZONE")
    target = setup.target
    if (bid_o >= target + tick) if d == 1 else (ask_o <= target - tick):
        reasons.append("TARGET_REVISITED_AT_ENTRY_OPEN")
    raw = ask_o if d == 1 else bid_o
    entry = raw + d * slip
    dist = d * (entry - setup.stop)
    gain_dist = d * (target - entry)
    spread = (ask_o - bid_o) * spread_mult
    friction = spread + fee + 2 * slip
    out.update(entry_raw_price=raw, entry_price=entry, stop=setup.stop, target=target, stop_distance=dist,
               target_distance=gain_dist, spread=spread, friction=friction)
    if not dist > 0:
        reasons.append("STOP_WRONG_SIDE")
    if not gain_dist > 0:
        reasons.append("TARGET_WRONG_SIDE")
    limit = params["risk"]["friction_max_fraction_of_stop"] * dist
    out["friction_limit"] = limit
    if dist > 0 and friction > limit:
        reasons.append("FRICTION_ABOVE_30PCT_OF_STOP")
    risk_q = dist + fee + slip
    gain_q = gain_dist - fee
    out.update(risk_unit_quote=risk_q, gain_unit_quote=gain_q)
    ratio = gain_q / risk_q if (dist > 0 and gain_dist > 0) else None
    out["reward_risk"] = ratio
    if ratio is not None and ratio < params["risk"]["min_reward_risk"]:
        reasons.append("REWARD_RISK_BELOW_2")
    out.update(fx_entry=mid_o, balance_eur=float(balance_eur), risk_unit_eur=None, qty_budget=None,
               qty_leverage=None, qty=None, planned_risk_eur=None)
    if dist > 0:
        rue = risk_q / mid_o
        qty, qb, ql = size_position(params, rue, balance_eur, mid_o, entry)
        out.update(risk_unit_eur=rue, qty_budget=qb, qty_leverage=ql, qty=qty, planned_risk_eur=qty * rue)
        if qty < params["account"]["qty_min_eur"]:
            reasons.append("SIZE_BELOW_MIN")
    out["reasons"] = reasons
    return out


def structural_path(market, e_i, direction, stop, target, params):
    """Per-EUR-unit path of one position entered at the open of row e_i. Returns the closed trade,
    or raises ExecutionPathUnknown (event with known_realized_per_unit, known_fills and exposure)."""
    fee, slip, tick, _ = _costs(params)
    d = int(direction)
    px = market.px
    side = "bid" if d == 1 else "ask"
    t_e = market.t(e_i)
    day0 = t_e // DAY_MS * DAY_MS
    deadline = min(t_e + params["exit"]["max_holding_minutes"] * MIN_MS,
                   day0 + params["exit"]["hard_exit_utc_minute"] * MIN_MS)
    k_i = (deadline - market.origin_ms) // MIN_MS
    if k_i <= e_i:
        raise ValueError("deadline must be after the entry row")
    entry_raw = float(px["ask_open"][e_i] if d == 1 else px["bid_open"][e_i])
    entry = entry_raw + d * slip
    fx_entry = float(px["mid_open"][e_i])
    dist = d * (entry - stop)
    if not dist > 0:
        raise ValueError("stop on the wrong side: refused before the path")
    exposure = {"direction": d, "entry_t_ms": t_e, "entry_price": entry, "entry_raw_price": entry_raw,
                "initial_stop": float(stop), "target": float(target), "distance": dist, "fx_entry": fx_entry,
                "risk_unit_eur": (dist + fee + slip) / fx_entry, "fee": fee, "slip": slip, "deadline_ms": deadline}
    st = {"realized": -0.5 * fee / fx_entry, "remaining": 1.0}
    fills, low, high, mark, times = [], [], [], [], []
    exit_reason = closed_at = None
    ambiguous = False
    prev_ms = t_e
    j = e_i
    while True:
        if j > e_i:
            if j >= market.n or not market.present[j]:
                nxt = j
                while nxt < market.n and not market.present[nxt]:
                    nxt += 1
                if nxt >= market.n:
                    exc = ExecutionPathUnknown("DATA_END_BEFORE_EXIT", entry_ms=t_e, previous_ms=prev_ms,
                                               current_ms=None)
                else:
                    try:
                        require_next_m1(prev_ms, market.t(nxt), entry_ms=t_e)
                        raise AssertionError("a missing minute must raise")
                    except ExecutionPathUnknown as caught:
                        exc = caught
                exc.attach_known_state(st["realized"], st["remaining"], fills)
                exc.event["exposure"] = dict(exposure)
                exc.event["first_unobserved_minute_ms"] = market.t(j)
                raise exc
            prev_ms = market.t(j)
        t_j = market.t(j)
        fx = float(px["mid_open"][j])
        op, hi = float(px[side + "_open"][j]), float(px[side + "_high"][j])
        lo, cl = float(px[side + "_low"][j]), float(px[side + "_close"][j])

        def liquidation(price):
            return st["realized"] + st["remaining"] * (d * (price - entry) - 0.5 * fee - slip) / fx

        def fill(price, reason, raw, market_exit, stop_level=None):
            increment = (d * (price - entry) - 0.5 * fee) / fx
            st["realized"] += increment
            st["remaining"] -= 1.0
            fills.append({"row_t_ms": t_j, "fraction": 1.0, "price": price, "reason": reason, "fx": fx,
                          "fx_source": "mid_open_of_fill_row", "market_exit": market_exit, "raw_price": raw,
                          "stop_level": stop_level, "price_pnl_quote_per_unit": d * (price - entry),
                          "raw_price_pnl_quote_per_unit": d * (raw - entry_raw),
                          "slippage_quote_per_unit": slip + (slip if market_exit else 0.0),
                          "commission_quote_per_unit": 0.5 * fee, "pnl_eur_per_unit": increment,
                          "fx_effect_eur_per_unit": (d * (price - entry) - 0.5 * fee) * (1.0 / fx - 1.0 / fx_entry)})

        open_eq = liquidation(op)
        if j == k_i:
            fill(op - d * slip, "TIME", op, True)
            low.append(min(open_eq, st["realized"]))
            high.append(max(open_eq, st["realized"]))
            mark.append(st["realized"])
            times.append(t_j)
            exit_reason, closed_at = "TIME", t_j
            break
        adverse = lo if d == 1 else hi
        favorable = hi if d == 1 else lo
        stop_hit = (adverse <= stop) if d == 1 else (adverse >= stop)
        target_hit = (favorable >= target + tick) if d == 1 else (favorable <= target - tick)
        if stop_hit:
            raw = min(op, stop) if d == 1 else max(op, stop)
            label = "SL_GAP" if d * (op - stop) < 0 else "SL"
            ambiguous = bool(target_hit)
            fill(raw - d * slip, label, raw, True, stop_level=float(stop))
            low.append(min(open_eq, st["realized"]))
            high.append(max(open_eq, st["realized"]))
            mark.append(st["realized"])
            times.append(t_j)
            exit_reason, closed_at = label, t_j + MIN_MS
            break
        if target_hit:
            worst = liquidation(adverse)
            fill(float(target), "TP", float(target), False)
            low.append(min(worst, st["realized"]))
            high.append(max(open_eq, st["realized"]))
            mark.append(st["realized"])
            times.append(t_j)
            exit_reason, closed_at = "TP", t_j + MIN_MS
            break
        low.append(liquidation(adverse))
        high.append(liquidation(favorable))
        mark.append(liquidation(cl))
        times.append(t_j)
        j += 1
    if abs(st["remaining"]) > 1e-12:
        raise AssertionError("position not fully closed")
    f = fills[-1]
    flow = {"raw_price_pnl_eur": f["raw_price_pnl_quote_per_unit"] / f["fx"],
            "slippage_eur": f["slippage_quote_per_unit"] / f["fx"],
            "commission_eur": 0.5 * fee / fx_entry + f["commission_quote_per_unit"] / f["fx"],
            "fx_effect_eur": f["fx_effect_eur_per_unit"],
            "gap_effect_eur_at_entry_fx": (d * (f["raw_price"] - f["stop_level"]) / fx_entry
                                           if f["reason"] == "SL_GAP" else 0.0)}
    return {"entry_t_ms": t_e, "entry_i": int(e_i), "exit_row_t_ms": f["row_t_ms"], "exit_i": int(j),
            "closed_at_ms": int(closed_at), "deadline_ms": int(deadline), "direction": d,
            "entry_price": entry, "entry_raw_price": entry_raw, "initial_stop": float(stop), "target": float(target),
            "distance": dist, "risk_unit_eur": exposure["risk_unit_eur"], "fx_entry": fx_entry,
            "net_unit": float(st["realized"]), "reason": exit_reason,
            "ambiguous_stop_and_target_same_m1": ambiguous, "fills": fills,
            "worst": low, "best": high, "mark": mark, "t": times, "fee": fee, "slip": slip,
            "entry_commission_eur_per_unit": -0.5 * fee / fx_entry,
            "R_price": f["price_pnl_quote_per_unit"] / dist, "flow_summary_per_unit": flow}
