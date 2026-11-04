"""V02 signal generation. Only closed, fully observed bars enter structure.

Fixed-R targets are determined from the actual open quote and frozen immediately.
The impulse context uses the last scheduled H4, never a stale complete candle.
"""
import copy
import math
from dataclasses import dataclass

import numpy as np

from .reference import B, D, E, X


@dataclass
class Pending:
    setup_id: str
    direction: int
    created_ms: int
    zone_lo: float
    zone_hi: float
    stop: float
    expiry_ms: int
    atr: float
    target: float | None = None
    target_known_at_ms: int | None = None


def impulse_records(h4, fraction):
    records = []
    for s in range(h4.n):
        rec = B.BiasRecord(s, h4.close_ms(s), bool(h4.complete[s]), int(h4.m1_count[s]),
                           float(h4.close[s]) if h4.complete[s] else None)
        rec.state = B.SUSPENDED
        if h4.complete[s]:
            delta = float(h4.close[s] - h4.open[s])
            width = float(h4.high[s] - h4.low[s])
            rec.state = B.NEUTRAL
            if width > 0 and abs(delta) >= fraction * width:
                rec.state = B.BULL if delta > 0 else B.BEAR if delta < 0 else B.NEUTRAL
        records.append(rec)
    return records


def make_params(reference, controls, candidate, stress=False, stress_spec=None):
    p = copy.deepcopy(reference)
    p['breakout']['body_atr_min'] = candidate['body_atr_min']
    p['risk']['min_reward_risk'] = candidate['reward_risk']
    p['account']['risk_budget_eur_per_position'] = controls['risk_budget_eur']
    p['account']['capital_eur'] = controls['capital_eur']
    p['entry']['window_utc_start_minute'] = controls['entry_start_utc_minute']
    p['entry']['window_utc_end_minute_exclusive'] = controls['entry_end_utc_minute']
    p['exit']['max_holding_minutes'] = controls['max_holding_minutes']
    p['exit']['hard_exit_utc_minute'] = controls['hard_exit_utc_minute']
    if stress:
        p['costs']['fee_round_trip_quote'] *= stress_spec['fee_multiplier']
        p['costs']['slip_quote_per_market_execution'] *= stress_spec['slip_multiplier']
    return p


def build_context(market, params, controls, candidate, structures=None):
    if structures is None:
        return E.build_context(market, params)
    m30, h4, p30, p4, atr, structure_bias = structures
    recs = structure_bias if candidate['bias'] == 'structure' else impulse_records(
        h4, controls['h4_impulse_min_body_fraction'])
    timeline = B.BiasTimeline(market.origin_ms, recs)
    bos = E.breakout_events(m30, p30, atr, timeline, params)
    return E.Context(market, m30, h4, p30, p4, atr, recs, timeline, bos)


def shared_structures(market, params):
    m30, h4 = D.make_bars(market, 30, 'M30'), D.make_bars(market, 240, 'H4')
    p30, p4 = D.find_pivots(m30), D.find_pivots(h4)
    return m30, h4, p30, p4, D.atr_at_close(m30, 14), B.compute_bias(h4, p4)


def preknown_target(ctx, event, tick):
    """Most recently confirmed external pivot, unpenetrated since confirmation.

    Unknown minutes in the observation interval disqualify the candidate; the
    pivot just broken is excluded. All slices end at the breakout close.
    """
    d, mk, t = event.direction, ctx.market, event.close_ms
    eligible = [p for p in ctx.m30_pivots if p.kind == ('HIGH' if d == 1 else 'LOW')
                and p.known_at_ms <= t and p.pid != event.level_pid
                and (p.price > event.zone_hi if d == 1 else p.price < event.zone_lo)]
    for p in sorted(eligible, key=lambda p: (p.known_at_ms, p.pivot_time_ms), reverse=True):
        a, b = mk.idx(p.known_at_ms), mk.idx(t)
        if a < 0 or not mk.present[a:b].all():
            continue
        target = p.bid_high if d == 1 else p.ask_low
        observed = mk.px['bid_high' if d == 1 else 'ask_low'][a:b]
        if np.any(observed >= target + tick) if d == 1 else np.any(observed <= target - tick):
            continue
        return float(target), int(p.known_at_ms)
    return None, None


def create_pending(ctx, event, candidate, params):
    if event.static_reasons:
        return None
    target, known = (None, None)
    if candidate['target'] == 'known_structural':
        target, known = preknown_target(ctx, event, params['costs']['tick_quote'])
        if target is None:
            return None
    buffer = params['risk']['stop_atr_buffer'] * event.atr_ref
    stop = event.poi_bid_low - buffer if event.direction == 1 else event.poi_ask_high + buffer
    return Pending(f'{candidate["name"]}@{event.close_ms}', event.direction, event.close_ms,
                   event.zone_lo, event.zone_hi, float(stop),
                   event.close_ms + 12 * 60 * D.MIN_MS, event.atr_ref, target, known)


def fixed_target(market, entry_i, setup, params, reward_risk):
    d = setup.direction
    costs = params['costs']
    fee, slip = costs['fee_round_trip_quote'], costs['slip_quote_per_market_execution']
    raw = market.px['ask_open' if d == 1 else 'bid_open'][entry_i]
    entry = float(raw + d * slip)
    distance = d * (entry - setup.stop)
    return entry + d * (reward_risk * (distance + fee + slip) + fee)


def entry_check(market, entry_i, setup, params, candidate, balance):
    # Recheck the target's availability; fixed R uses only this opening quote.
    if candidate['target'] == 'fixed':
        setup.target = fixed_target(market, entry_i, setup, params, candidate['reward_risk'])
        setup.target_known_at_ms = market.t(entry_i)
    out = X.evaluate_entry(market, entry_i, setup, params, balance)
    # A floating-point equality at the configured RR must not reject an exact target.
    if out['reward_risk'] is not None and math.isclose(out['reward_risk'], candidate['reward_risk'],
                                                      rel_tol=0, abs_tol=1e-10):
        out['reasons'] = [r for r in out['reasons'] if r != 'REWARD_RISK_BELOW_2']
    if balance <= 0:
        out['reasons'].append('NON_POSITIVE_EQUITY')
    return out
