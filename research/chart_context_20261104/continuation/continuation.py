"""Independent modelled continuations of actual TP2R fills; no portfolio engine.

The caller supplies an actually replayed TP2R trade and its own scenario params.
This module never selects trades, changes the bot or starts a historical run.
"""
import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_bot.reference import D, ROOT, X, ExecutionPathUnknown

THRESHOLDS = (3, 4, 5)


class ContinuationInputError(ValueError):
    """Source trade/parameters do not certify the declared actual TP2R fill."""


def _number(value, name):
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ContinuationInputError(f'{name} must be a finite number') from exc
    if not math.isfinite(result):
        raise ContinuationInputError(f'{name} must be a finite number')
    return result


def _ms(text):
    stamp = pd.Timestamp(text)
    if stamp.tzinfo is None:
        raise ContinuationInputError('Trade timestamps must be timezone-aware')
    return int(stamp.value // 1_000_000)


def _matching(actual, expected, name, tolerance=1e-12):
    if not math.isclose(_number(actual, name), float(expected), rel_tol=0, abs_tol=tolerance):
        raise ContinuationInputError(f'{name} differs from the original scenario: {actual} != {expected}')


def _plain(value):
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _target(entry, stop, direction, multiple, fee, slip):
    distance = direction * (entry - stop)
    return entry + direction * (multiple * (distance + fee + slip) + fee)


def _timing(mk, row_ms, closed_ms, original_row_ms):
    row_ms = int(row_ms)
    if row_ms < original_row_ms:
        raise RuntimeError('A higher target terminal row precedes the certified2R row')
    i = mk.idx(row_ms)
    first = float(mk.first_ts[i]) if 0 <= i < mk.n and mk.present[i] else float('nan')
    return {'event_row_open_ms': row_ms,
            'event_row_end_exclusive_ms': row_ms + D.MIN_MS,
            'model_closed_at_ms': int(closed_ms) if closed_ms is not None else None,
            'row_first_quote_ms_not_fill_time': int(first) if math.isfinite(first) else None,
            'time_relation': 'SAME_M1_AS_2R' if row_ms == original_row_ms else 'LATER_M1_AFTER_2R',
            'time_relation_refers_to': 'Terminal observation, or first unobserved row for unknown paths',
            'exact_intraminute_fill_order_verified': False}


def continue_trade(mk, trade, params, cfg):
    """Return JSON-safe3/4/5R outcomes for one certified actual TP2R trade.

    True/False/None distinguish a modelled hit, resolved non-hit and unknown.
    Each threshold is an independent hold-instead-of-2R experiment from the SAME
    entry, not a reopening after2R. No trade or params object is modified.
    """
    if trade.get('exit_reason') != 'TP':
        raise ContinuationInputError('Only actual TP exits are eligible')
    if _number(cfg.get('planned_quote_reward_risk'), 'cfg planned R') != 2:
        raise ContinuationInputError('Source portfolio configuration must target2R')
    if cfg.get('hard_exit') != '16:00' or cfg.get('timezone', 'Europe/London') != 'Europe/London':
        raise ContinuationInputError('This predeclared study ends at16:00 Europe/London')
    direction = int(trade['direction'])
    if direction not in (-1, 1):
        raise ContinuationInputError('direction must be -1 or1')
    entry_ms = _ms(trade['entry_utc'])
    if entry_ms % D.MIN_MS:
        raise ContinuationInputError('Entry must be aligned on a whole M1')
    entry_i = mk.idx(entry_ms)
    if not 0 <= entry_i < mk.n or not mk.present[entry_i]:
        raise ContinuationInputError('Original entry quote is unavailable')
    entry = _number(trade['entry_price'], 'entry_price')
    stop = _number(trade['stop'], 'stop')
    qty = _number(trade['qty_eur'], 'qty_eur')
    if qty <= 0 or direction * (entry - stop) <= 0:
        raise ContinuationInputError('Positive quantity and correctly sided initial stop required')
    fee = _number(params['costs']['fee_round_trip_quote'], 'fee')
    slip = _number(params['costs']['slip_quote_per_market_execution'], 'slip')
    tick = _number(params['costs']['tick_quote'], 'tick')
    if fee < 0 or slip < 0 or tick <= 0:
        raise ContinuationInputError('Costs must be nonnegative and tick positive')
    day = pd.Timestamp(entry_ms, unit='ms', tz='UTC').tz_convert('Europe/London').date()
    hard_ms = _ms(pd.Timestamp(f'{day} 16:00', tz='Europe/London').tz_convert('UTC'))
    effective = min(entry_ms + int(params['exit']['max_holding_minutes']) * D.MIN_MS,
                    entry_ms // D.DAY_MS * D.DAY_MS + int(params['exit']['hard_exit_utc_minute']) * D.MIN_MS)
    if effective != hard_ms or hard_ms <= entry_ms:
        raise ContinuationInputError('Parameters do not preserve the declared16London horizon')
    target2 = _target(entry, stop, direction, 2, fee, slip)
    _matching(trade['target'], target2, 'original2R target')
    closed_ms = int(trade['closed_at_ms']) if trade.get('closed_at_ms') is not None else _ms(trade['exit_utc'])
    if trade.get('exit_utc'):
        _matching(_ms(trade['exit_utc']), closed_ms, 'original close timestamp', 0)
    try:
        original = X.structural_path(mk, entry_i, direction, stop, target2, params)
    except ExecutionPathUnknown as exc:
        raise ContinuationInputError('Recorded TP2R cannot be certified with the supplied path') from exc
    if original['reason'] != 'TP' or int(original['closed_at_ms']) != closed_ms:
        raise ContinuationInputError('Recorded exit is not the supplied path actual TP2R')
    _matching(original['entry_price'], entry, 'original executed entry')
    if trade.get('planned_risk_eur') not in (None, ''):
        _matching(trade['planned_risk_eur'], qty * original['risk_unit_eur'], 'original planned risk', 1e-7)
    if trade.get('net_eur') not in (None, ''):
        _matching(trade['net_eur'], qty * original['net_unit'], 'original realized cash', 1e-7)
    original_row_ms = int(original['exit_row_t_ms'])
    result = {
        'study': 'V03_2R_ACTUAL_TP_CONTINUATION_20261104_V01',
        'entry_utc': D.iso(entry_ms), 'direction': direction, 'entry_price': entry,
        'initial_stop': stop, 'qty_eur_unchanged': qty,
        'fee_round_trip_quote': fee, 'slip_per_market_execution_quote': slip, 'tick_quote': tick,
        'deadline_ms': hard_ms, 'R_definition': 'Planned net quote R; not exactly realized EUR cash R',
        'original_2R': {'target': target2, 'validated_actual_TP': True,
                        'exit_row_open_ms': original_row_ms,
                        'model_closed_at_ms': closed_ms,
                        'actual_net_eur': qty * original['net_unit']},
        'hypothetical_only': True, 'positions_may_overlap_between_source_trades': True,
        'portfolio_equity_must_not_be_aggregated': True,
        'stop_target_same_M1_policy': 'STOP_FIRST_MODEL_CONVENTION_NOT_PROVEN_TICK_ORDER',
        'thresholds': {},
    }
    for multiple in THRESHOLDS:
        target = _target(entry, stop, direction, multiple, fee, slip)
        outcome = {'planned_net_quote_R': multiple, 'target': target,
                   'stop_unchanged': stop, 'quantity_unchanged': qty}
        try:
            path = X.structural_path(mk, entry_i, direction, stop, target, params)
        except ExecutionPathUnknown as exc:
            first_missing = int(exc.event['first_unobserved_minute_ms'])
            if first_missing <= original_row_ms:
                raise RuntimeError('Unknown higher path precedes the certified2R observation') from exc
            outcome.update(status='UNKNOWN_DATA_GAP', reached=None, exit_reason=None,
                           stop_and_target_same_M1=None, unknown_event=_plain(exc.event),
                           **_timing(mk, first_missing, None, original_row_ms))
        else:
            reason, row_ms = path['reason'], int(path['exit_row_t_ms'])
            if int(path['closed_at_ms']) < closed_ms:
                raise RuntimeError('Higher path closes before certified2R model close')
            if reason in ('SL', 'SL_GAP') and row_ms <= original_row_ms:
                raise RuntimeError('Stop conflicts with the certified2R stop-first fill')
            status = ('REACHED_BEFORE_STOP_OR_DEADLINE' if reason == 'TP' else
                      'EXPIRED_AT_DEADLINE' if reason == 'TIME' else 'STOP_BEFORE_THRESHOLD')
            outcome.update(status=status, reached=reason == 'TP', exit_reason=reason,
                           stop_and_target_same_M1=bool(path['ambiguous_stop_and_target_same_m1']),
                           unknown_event=None,
                           **_timing(mk, row_ms, path['closed_at_ms'], original_row_ms))
        result['thresholds'][f'{multiple}R'] = outcome
    for lower, upper in ((3, 4), (4, 5)):
        left, right = result['thresholds'][f'{lower}R'], result['thresholds'][f'{upper}R']
        if right['reached'] is True and (left['reached'] is not True or left['event_row_open_ms'] > right['event_row_open_ms']):
            raise RuntimeError('Threshold reachability/order is not monotone')
    return _plain(result)


def source_identity():
    """Hashes for the parent runner to freeze before any historical calculation."""
    here = Path(__file__).resolve().parent
    files = [*sorted(here.glob('*.py')), here / 'PLAN_BEFORE_HISTORY.json',
             ROOT / 'simple_forex/runner.py', ROOT / 'simple_forex/strategy_rearmed.py',
             ROOT / 'simple_forex/protocol_v03.json', ROOT / 'src/backtest_bot/reference.py',
             ROOT / 'vendor/h4m30_v01/h4m30_execution.py',
             ROOT / 'vendor/h4m30_v01/integrity_guard.py']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
