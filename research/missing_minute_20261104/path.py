"""Local copy of frozen structural_path; changes restricted to R1/R2. See PROVENANCE.json."""
from backtest_bot.reference import X, ExecutionPathUnknown
_costs = X._costs
MIN_MS = 60000
DAY_MS = 86400000

def structural_path(market, e_i, direction, stop, target, params, *, scenario='S_CONT', gap_sink=None):
    """Per-EUR-unit path of one position entered at the open of row e_i. Returns the closed trade,
    or raises ExecutionPathUnknown (event with known_realized_per_unit, known_fills and exposure)."""
    if scenario not in ('S_CONT', 'S_PESS', 'S_OPT'):
        raise ValueError('Unknown frozen scenario')
    gap_sink = [] if gap_sink is None else gap_sink
    trade_gaps = []
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
        forced_gap = None
        if j > e_i:
            if j >= market.n or not market.present[j]:
                nxt = j
                while nxt < market.n and not market.present[nxt]:
                    nxt += 1
                record = {'entry_ms': t_e, 'first_missing_ms': market.t(j),
                          'last_missing_ms': market.t(nxt - 1), 'missing_minutes': nxt - j,
                          'resume_ms': market.t(nxt) if nxt < market.n else None,
                          'scenario': scenario, 'resolution': 'R2_UNRESOLVED' if nxt >= market.n or nxt - j > 5 else 'R1',
                          'deadline_in_gap': market.t(j) <= deadline < market.t(nxt)}
                gap_sink.append(record)
                trade_gaps.append(record)
                if nxt >= market.n:
                    exc = ExecutionPathUnknown("DATA_END_BEFORE_EXIT", entry_ms=t_e, previous_ms=prev_ms,
                                               current_ms=None)
                elif nxt - j > 5:
                    exc = ExecutionPathUnknown('UNRESOLVED_M1_STEP', entry_ms=t_e, previous_ms=prev_ms,
                        current_ms=market.t(nxt), missing_minutes=nxt - j, gap_class='R2_OVER_5_MINUTES')
                else:
                    exc = None
                if exc is not None:
                    exc.attach_known_state(st["realized"], st["remaining"], fills)
                    exc.event["exposure"] = dict(exposure)
                    exc.event["first_unobserved_minute_ms"] = market.t(j)
                    exc.event['gap_audit'] = list(trade_gaps)
                    raise exc
                j = nxt  # No price, mark or imputed envelope is produced inside the gap.
                forced_gap = record
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
        if forced_gap is not None and scenario in ('S_PESS', 'S_OPT'):
            raw = (min(op, stop) if d == 1 else max(op, stop)) if scenario == 'S_PESS' else float(target)
            fill(raw - d * slip if scenario == 'S_PESS' else raw, 'R1_' + scenario,
                 raw, scenario == 'S_PESS', stop_level=float(stop) if scenario == 'S_PESS' else None)
            low.append(min(open_eq, st['realized']))
            high.append(max(open_eq, st['realized']))
            mark.append(st['realized'])
            times.append(t_j)
            exit_reason, closed_at = 'R1_' + scenario, t_j
            forced_gap.update(exit_reason=exit_reason, exit_row_ms=t_j, closed_at_ms=t_j)
            break
        if j >= k_i:
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
    for gap in trade_gaps:
        gap.update(trade_exit_reason=exit_reason, trade_closed_at_ms=int(closed_at))
    flow = {"raw_price_pnl_eur": f["raw_price_pnl_quote_per_unit"] / f["fx"],
            "slippage_eur": f["slippage_quote_per_unit"] / f["fx"],
            "commission_eur": 0.5 * fee / fx_entry + f["commission_quote_per_unit"] / f["fx"],
            "fx_effect_eur": f["fx_effect_eur_per_unit"],
            "gap_effect_eur_at_entry_fx": (d * (f["raw_price"] - f["stop_level"]) / fx_entry
                                           if f["reason"] == "SL_GAP" or
                                           (f['reason'] == 'R1_S_PESS' and d * (f['raw_price'] - stop) < 0) else 0.0)}
    return {"entry_t_ms": t_e, "entry_i": int(e_i), "exit_row_t_ms": f["row_t_ms"], "exit_i": int(j),
            "closed_at_ms": int(closed_at), "deadline_ms": int(deadline), "direction": d,
            "entry_price": entry, "entry_raw_price": entry_raw, "initial_stop": float(stop), "target": float(target),
            "distance": dist, "risk_unit_eur": exposure["risk_unit_eur"], "fx_entry": fx_entry,
            "net_unit": float(st["realized"]), "reason": exit_reason,
            "ambiguous_stop_and_target_same_m1": ambiguous, "fills": fills,
            "worst": low, "best": high, "mark": mark, "t": times, "fee": fee, "slip": slip,
            "entry_commission_eur_per_unit": -0.5 * fee / fx_entry,
            "R_price": f["price_pnl_quote_per_unit"] / dist, "flow_summary_per_unit": flow,
            'gap_audit': trade_gaps}
