"""Synthetic fixtures only; no historical cache or portfolio calculation."""
import copy
import json
import unittest

import numpy as np
import pandas as pd

from backtest_bot.reference import D, ROOT, X
from simple_forex.runner import order, parameters
from research.chart_context_20261104.continuation import ContinuationInputError, continue_trade

ORIGIN = int(pd.Timestamp('2021-01-04T00:00:00Z').value // 1_000_000)
ENTRY = 600


def fixture(direction=1, day='2021-01-04'):
    n = 1440
    origin = int(pd.Timestamp(f'{day}T00:00:00Z').value // 1_000_000)
    px = {f'{side}_{field}': np.full(n, 1.2 + offset + delta)
          for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]
          for field, delta in [('open', 0), ('close', 0), ('high', 0.0001), ('low', -0.0001)]}
    mk = D.Market(origin, origin + n * D.MIN_MS, n, np.ones(n, bool), px,
                  origin + np.arange(n) * D.MIN_MS + 100, 0, np.zeros(n, bool), np.zeros(n, bool))
    cfg = json.loads((ROOT / 'simple_forex/protocol_v03.json').read_text())
    cfg['planned_quote_reward_risk'] = 2
    ref = json.loads((ROOT / 'config/reference_params.json').read_text())
    deadline = int(pd.Timestamp(f'{day} 16:00', tz='Europe/London').value // 1_000_000)
    params = parameters(ref, cfg, deadline, False)
    event = {'direction': direction, 'stop': 1.199 if direction == 1 else 1.201,
             'range_high': 1.1999, 'range_low': 1.2001}
    check = order(mk, ENTRY, event, params, cfg, 100000)
    assert not check['reasons']
    return mk, cfg, params, check, direction


def target(check, params, direction, multiple):
    fee, slip = params['costs']['fee_round_trip_quote'], params['costs']['slip_quote_per_market_execution']
    distance = direction * (check['entry_price'] - check['stop'])
    return check['entry_price'] + direction * (multiple * (distance + fee + slip) + fee)


def favorable(mk, row, price, direction):
    field = 'high' if direction == 1 else 'low'
    mid = price + 0.00005 * direction
    for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]:
        mk.px[f'{side}_{field}'][row] = mid + offset


def stop_touch(mk, row, price, direction):
    field = 'low' if direction == 1 else 'high'
    mid = price + 0.00005 * direction
    for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]:
        mk.px[f'{side}_{field}'][row] = mid + offset


def actual_trade(mk, cfg, params, check, direction):
    path = X.structural_path(mk, ENTRY, direction, check['stop'], check['target'], params)
    assert path['reason'] == 'TP'
    return {'entry_utc': D.iso(mk.t(ENTRY)), 'exit_utc': D.iso(path['closed_at_ms']),
            'closed_at_ms': path['closed_at_ms'], 'exit_reason': 'TP', 'direction': direction,
            'entry_price': check['entry_price'], 'stop': check['stop'], 'target': check['target'],
            'qty_eur': check['qty_eur'], 'planned_risk_eur': check['planned_risk_eur'],
            'net_eur': check['qty_eur'] * path['net_unit']}


class ContinuationChecks(unittest.TestCase):
    def test_same_original_tp_minute_reaches4R_for_long_and_short(self):
        for direction in (1, -1):
            mk, cfg, params, check, direction = fixture(direction)
            favorable(mk, 601, target(check, params, direction, 4) + direction * params['costs']['tick_quote'], direction)
            trade = actual_trade(mk, cfg, params, check, direction)
            before = copy.deepcopy((trade, params, cfg))
            result = continue_trade(mk, trade, params, cfg)
            for name in ('3R', '4R'):
                out = result['thresholds'][name]
                self.assertTrue(out['reached'])
                self.assertEqual(out['time_relation'], 'SAME_M1_AS_2R')
                self.assertEqual(out['event_row_open_ms'], mk.t(601))
                self.assertEqual(out['model_closed_at_ms'], mk.t(602))
            self.assertFalse(result['thresholds']['5R']['reached'])
            self.assertEqual((trade, params, cfg), before)
            json.dumps(result, allow_nan=False)

    def test_stop_before3R_ignores_prices_after_stop(self):
        mk, cfg, params, check, direction = fixture()
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        stop_touch(mk, 603, check['stop'], direction)
        trade = actual_trade(mk, cfg, params, check, direction)
        before = continue_trade(mk, trade, params, cfg)
        for values in mk.px.values():
            values[604:] *= 3
        after = continue_trade(mk, trade, params, cfg)
        self.assertEqual(before, after)
        self.assertEqual(before['thresholds']['3R']['status'], 'STOP_BEFORE_THRESHOLD')
        self.assertEqual(before['thresholds']['3R']['time_relation'], 'LATER_M1_AFTER_2R')

    def test_gap_is_unknown_even_if_future_prices_exceed5R(self):
        mk, cfg, params, check, direction = fixture()
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        trade = actual_trade(mk, cfg, params, check, direction)
        mk.present[603] = False
        for values in mk.px.values():
            values[604:] *= 3
        result = continue_trade(mk, trade, params, cfg)
        for out in result['thresholds'].values():
            self.assertIsNone(out['reached'])
            self.assertEqual(out['status'], 'UNKNOWN_DATA_GAP')
            self.assertEqual(out['event_row_open_ms'], mk.t(603))
            self.assertIsNone(out['model_closed_at_ms'])
        json.dumps(result, allow_nan=False)

    def test_reached3R_remains_true_when4R_and5R_become_unknown(self):
        mk, cfg, params, check, direction = fixture()
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        favorable(mk, 602, target(check, params, direction, 3) + params['costs']['tick_quote'], direction)
        mk.present[603] = False
        result = continue_trade(mk, actual_trade(mk, cfg, params, check, direction), params, cfg)
        self.assertTrue(result['thresholds']['3R']['reached'])
        self.assertEqual(result['thresholds']['3R']['time_relation'], 'LATER_M1_AFTER_2R')
        self.assertIsNone(result['thresholds']['4R']['reached'])
        self.assertIsNone(result['thresholds']['5R']['reached'])

    def test_post_tp2_stop_and3R_same_minute_keeps_ambiguity(self):
        mk, cfg, params, check, direction = fixture()
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        stop_touch(mk, 602, check['stop'], direction)
        favorable(mk, 602, target(check, params, direction, 3) + params['costs']['tick_quote'], direction)
        result = continue_trade(mk, actual_trade(mk, cfg, params, check, direction), params, cfg)
        out = result['thresholds']['3R']
        self.assertFalse(out['reached'])
        self.assertTrue(out['stop_and_target_same_M1'])
        self.assertEqual(out['status'], 'STOP_BEFORE_THRESHOLD')

    def test_deadline_open_has_priority_over_large_deadline_high(self):
        mk, cfg, params, check, direction = fixture()
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        favorable(mk, 960, target(check, params, direction, 5) + params['costs']['tick_quote'], direction)
        result = continue_trade(mk, actual_trade(mk, cfg, params, check, direction), params, cfg)
        for out in result['thresholds'].values():
            self.assertFalse(out['reached'])
            self.assertEqual(out['status'], 'EXPIRED_AT_DEADLINE')
            self.assertEqual(out['event_row_open_ms'], mk.t(960))
            self.assertEqual(out['model_closed_at_ms'], mk.t(960))

    def test_missing_deadline_quote_stays_unknown(self):
        mk, cfg, params, check, direction = fixture()
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        mk.present[960] = False
        result = continue_trade(mk, actual_trade(mk, cfg, params, check, direction), params, cfg)
        self.assertIsNone(result['thresholds']['3R']['reached'])
        self.assertEqual(result['thresholds']['3R']['event_row_open_ms'], mk.t(960))

    def test_target_without_required_one_tick_is_not_a_hit(self):
        mk, cfg, params, check, direction = fixture()
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        favorable(mk, 602, target(check, params, direction, 3), direction)
        result = continue_trade(mk, actual_trade(mk, cfg, params, check, direction), params, cfg)
        self.assertFalse(result['thresholds']['3R']['reached'])

    def test_rejects_wrong_source_target_and_wrong_horizon(self):
        mk, cfg, params, check, direction = fixture()
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        trade = actual_trade(mk, cfg, params, check, direction)
        for field, value in [('exit_reason', 'TIME'), ('target', check['target'] + 0.001),
                             ('closed_at_ms', mk.t(603)), ('net_eur', trade['net_eur'] + 1)]:
            bad = {**trade, field: value}
            with self.assertRaises(ContinuationInputError):
                continue_trade(mk, bad, params, cfg)
        wrong = copy.deepcopy(params)
        wrong['exit']['max_holding_minutes'] = 60
        with self.assertRaises(ContinuationInputError):
            continue_trade(mk, trade, wrong, cfg)

    def test_summer_hard16_london_is15_utc(self):
        mk, cfg, params, check, direction = fixture(day='2021-03-30')
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        result = continue_trade(mk, actual_trade(mk, cfg, params, check, direction), params, cfg)
        self.assertEqual(result['deadline_ms'], mk.t(900))
        self.assertEqual(result['thresholds']['3R']['model_closed_at_ms'], mk.t(900))

    def test_original2R_stop_target_ambiguity_invalidates_forged_tp(self):
        mk, cfg, params, check, direction = fixture()
        favorable(mk, 601, check['target'] + params['costs']['tick_quote'], direction)
        trade = actual_trade(mk, cfg, params, check, direction)
        stop_touch(mk, 601, check['stop'], direction)
        with self.assertRaises(ContinuationInputError):
            continue_trade(mk, trade, params, cfg)


if __name__ == '__main__':
    unittest.main()
