"""Causality and execution-boundary tests for the chart-context experiment."""
import json
import unittest
from unittest.mock import patch
import numpy as np

from backtest_bot.reference import D, ROOT
from simple_forex import runner as core
from context import ChartContext, room_check, simulate, _simulate


ORIGIN = 1609718400000


def market(days=4):
    n = days * 1440
    price = 1.2 + 0.001 * np.sin(np.arange(n) / 120)
    px = {f'{side}_{field}': price + offset + delta
        for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]
        for field, delta in [('open', 0), ('close', 0), ('high', 0.0001), ('low', -0.0001)]}
    return D.Market(ORIGIN, ORIGIN + n * D.MIN_MS, n, np.ones(n, bool), px,
        ORIGIN + np.arange(n) * D.MIN_MS + 100, 0, np.zeros(n, bool), np.zeros(n, bool))


class CausalContext(unittest.TestCase):
    def test_future_suffix_cannot_change_closed_context_or_levels(self):
        mk = market()
        t = mk.t(2 * 1440 + 545)
        before = ChartContext(mk).snapshot(t, 1)
        self.assertTrue(before['levels'])
        for values in mk.px.values():
            values[mk.idx(t):] *= 4
        self.assertEqual(before, ChartContext(mk).snapshot(t, 1))

    def test_missing_last_expected_h1_is_unknown_without_fallback(self):
        mk = market()
        t = mk.t(2 * 1440 + 545)
        mk.present[2 * 1440 + 8 * 60] = False
        row = ChartContext(mk).snapshot(t, 1)
        self.assertEqual(row['H1_known_at_ms'], mk.t(2 * 1440 + 540))
        self.assertFalse(row['H1_complete'])
        self.assertIsNone(row['H1_body'])
        self.assertIn('H1_DATA_UNKNOWN', row['reasons'])

    def test_adx_gap_resets_warmup_and_pivot_confirmation_is_delayed(self):
        mk = market()
        mk.present[600] = False
        lab = ChartContext(mk)
        self.assertIsNone(lab.snapshot(mk.t(610), 1)['ADX14_M5'])
        pivot = next(p for p in lab.pivots if p.known_at_ms > mk.t(610))
        self.assertNotIn(pivot.pid, [p['id'] for p in lab.snapshot(pivot.known_at_ms - 5 * D.MIN_MS,
            1 if pivot.kind == 'HIGH' else -1)['levels']])
        self.assertIn(pivot.pid, [p['id'] for p in lab.snapshot(pivot.known_at_ms,
            1 if pivot.kind == 'HIGH' else -1)['levels']])

    def test_freshness_gap_is_unknown_but_observed_visit_is_known(self):
        mk = market()
        lab = ChartContext(mk)
        pivot = lab.pivots[0]
        d = 1 if pivot.kind == 'HIGH' else -1
        i = mk.idx(pivot.known_at_ms)
        t = mk.t(i + 10)
        field = 'bid_high' if d == 1 else 'ask_low'
        level = pivot.bid_high if d == 1 else pivot.ask_low
        mk.px[field][i:i + 10] = level - d * 0.001
        mk.present[i + 1] = False
        row = ChartContext(mk).snapshot(t, d)
        self.assertEqual(next(p for p in row['levels'] if p['id'] == pivot.pid)['freshness'], 'UNKNOWN_SINCE_CONFIRMATION')
        mk.px[field][i + 2] = level
        row = ChartContext(mk).snapshot(t, d)
        self.assertEqual(next(p for p in row['levels'] if p['id'] == pivot.pid)['freshness'], 'VISITED')

    def test_execution_guard_same_side_equality_unknown_and_visited(self):
        levels = [{'executable_price': 1.2001, 'freshness': 'INTACT_OBSERVED'}]
        self.assertIn('H1_LEVEL_BEFORE_OR_AT_TARGET', room_check(levels, 1, 1.2, 1.2001)[1])
        self.assertIn('H1_LEVEL_BEFORE_OR_AT_TARGET', room_check(levels, -1, 1.2002, 1.2)[1])
        self.assertFalse(room_check(levels, 1, 1.2002, 1.203)[1])
        levels[0]['freshness'] = 'UNKNOWN_SINCE_CONFIRMATION'
        self.assertEqual(room_check(levels, 1, 1.2, 1.203)[1], ['H1_LEVEL_FRESHNESS_UNKNOWN'])
        levels[0]['freshness'] = 'VISITED'
        self.assertEqual(room_check(levels, 1, 1.2, 1.203)[1], [])

    def test_level_rejection_does_not_consume_entry_quota_and_core_is_unchanged(self):
        mk = market(1)
        cfg = json.loads((ROOT / 'simple_forex/protocol_v03.json').read_text())
        cfg.update(planned_quote_reward_risk=2, research_level_veto=True, max_entries_per_day=1)
        reference = json.loads((ROOT / 'config/reference_params.json').read_text())
        raw = [{'decision_ms': mk.t(i), 'reason': 'BREAKOUT', 'direction': 1,
            'range_high': 1.19, 'range_low': 1.18, 'stop': 1.18} for i in [600, 660]]
        lab = ChartContext(mk)
        def info(t, direction):
            return {'reasons': [], 'levels': [{'executable_price': 1.201, 'freshness': 'INTACT_OBSERVED'}] if t == mk.t(600) else []}
        with patch('context.original_signals', return_value=(raw, {'deadline_i': 960})), patch.object(lab, 'snapshot', side_effect=info):
            summary, trades, decisions, _ = simulate(mk, cfg, reference, mk.origin_ms, mk.end_ms,
                signal_source=lab.signal_source)
        self.assertIsNone(summary['halt'])
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['entry_utc'], D.iso(mk.t(660)))
        self.assertIn('H1_LEVEL_BEFORE_OR_AT_TARGET', decisions[0]['refusal_reasons'])
        self.assertIs(_simulate.__code__, core.simulate.__code__)
        self.assertIs(core.simulate.__globals__['order'], core.order)


if __name__ == '__main__':
    unittest.main()
