import copy
import json
import unittest
from pathlib import Path

import pandas as pd

from backtest_bot.reference import D, ROOT
from simple_forex.runner import order, parameters, simulate
from simple_forex.strategy import signals
from test_research import ORIGIN, REF, market

CFG = json.loads((ROOT / 'simple_forex/protocol_v01.json').read_text())


def quote(mk, i, mid):
    for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]:
        for field, extra in [('open', 0), ('close', 0), ('high', 0.0001), ('low', -0.0001)]:
            mk.px[f'{side}_{field}'][i] = mid + offset + extra


def long_signal(mk, base=0):
    quote(mk, base + 544, 1.2004)
    quote(mk, base + 545, 1.2004)


class SimpleForexTests(unittest.TestCase):
    def test_no_breakout_means_no_trade_without_fictitious_orders(self):
        mk = market()
        result = simulate(mk, CFG, REF, ORIGIN, mk.end_ms)
        self.assertEqual(result[0]['closed_trades'], 0)
        self.assertEqual(result[0]['net_eur'], 0)
        self.assertTrue(result[0]['event_counts']['NO_BREAKOUT'])

    def test_wick_does_not_create_a_closed_bar_breakout(self):
        mk = market()
        mk.px['mid_high'][544] = 1.203
        events, _ = signals(mk, '2021-01-04')
        self.assertFalse(any(e['reason'] == 'BREAKOUT' for e in events))

    def test_only_first_closed_breakout_per_direction_is_consumed(self):
        mk = market()
        long_signal(mk)
        quote(mk, 549, 1.2005)
        quote(mk, 554, 1.1995)
        events, _ = signals(mk, '2021-01-04')
        entries = [e for e in events if e['reason'] == 'BREAKOUT']
        self.assertEqual([e['direction'] for e in entries], [1, -1])
        self.assertEqual(D.iso(entries[0]['decision_ms']), '2021-01-04T09:05:00Z')
        self.assertTrue(any(e['reason'] == 'DIRECTION_ALREADY_CONSUMED' for e in events))

    def test_incomplete_range_does_not_invent_levels(self):
        mk = market()
        mk.present[500] = False
        long_signal(mk)
        events, session = signals(mk, '2021-01-04')
        self.assertEqual(events[0]['reason'], 'RANGE_M1_MISSING')
        self.assertNotIn('range_high', session)

    def test_signal_gap_cancels_later_new_signals(self):
        mk = market()
        mk.present[541] = False
        quote(mk, 559, 1.201)
        events, _ = signals(mk, '2021-01-04')
        self.assertEqual(events[-1]['reason'], 'SIGNAL_M5_INCOMPLETE_SESSION_CANCELLED')
        self.assertFalse(any(e['reason'] == 'BREAKOUT' for e in events))

    def test_future_prices_and_future_gaps_cannot_erase_past_signal(self):
        mk = market()
        long_signal(mk)
        before, _ = signals(mk, '2021-01-04')
        cutoff = mk.t(550)
        for values in mk.px.values():
            values[550:] *= 3
        mk.present[555] = False
        after, _ = signals(mk, '2021-01-04')
        self.assertEqual([e for e in before if e['decision_ms'] < cutoff],
                         [e for e in after if e['decision_ms'] < cutoff])

    def test_future_end_of_grid_cannot_erase_morning_signal(self):
        mk = market()
        long_signal(mk)
        full, _ = signals(mk, '2021-01-04')
        mk.n, mk.end_ms = 550, mk.t(550)
        truncated, _ = signals(mk, '2021-01-04')
        self.assertEqual([e for e in full if e['decision_ms'] <= mk.t(550)],
                         [e for e in truncated if e['decision_ms'] <= mk.t(550)])
        self.assertTrue(any(e['reason'] == 'BREAKOUT' for e in truncated))

    def test_london_clock_uses_summer_time(self):
        mk = market()
        summer = int(pd.Timestamp('2021-07-05T00:00:00Z').value // 1_000_000)
        mk.origin_ms, mk.end_ms = summer, summer + D.DAY_MS
        mk.first_ts += summer - ORIGIN
        quote(mk, 484, 1.2004)
        events, _ = signals(mk, '2021-07-05')
        entry = next(e for e in events if e['reason'] == 'BREAKOUT')
        self.assertEqual(D.iso(entry['decision_ms']), '2021-07-05T08:05:00Z')

    def test_order_costs_ratio_and_risk_step(self):
        for direction, mid, stop in [(1, 1.2004, 1.19984), (-1, 1.1995, 1.20016)]:
            mk = market()
            quote(mk, 545, mid)
            event = {'direction': direction, 'stop': stop, 'range_high': 1.2001, 'range_low': 1.1999}
            params = parameters(REF, CFG, mk.t(960), False)
            check = order(mk, 545, event, params, CFG, 100000)
            self.assertEqual(check['reasons'], [])
            self.assertLessEqual(check['planned_risk_eur'], 250)
            self.assertEqual(check['qty_eur'] % 2000, 0)
            risk = direction * (check['entry_price'] - stop) + 0.00006
            gain = direction * (check['target'] - check['entry_price']) - 0.00005
            self.assertAlmostEqual(gain / risk, 2.0)

    def test_entry_reversal_is_refused_instead_of_chasing(self):
        mk = market()
        long_signal(mk)
        quote(mk, 545, 1.2)
        summary, trades, events, _ = simulate(mk, CFG, REF, ORIGIN, mk.end_ms)
        self.assertEqual(trades, [])
        refusal = next(e for e in events if e['reason'] == 'REFUSED')
        self.assertIn('ENTRY_NO_LONGER_BEYOND_RANGE', refusal['refusal_reasons'])

    def test_missing_entry_or_exposure_stops_with_unknown_total(self):
        for missing, expected in [(545, 'ENTRY_QUOTE_MISSING'), (550, 'UNRESOLVED_EXECUTION')]:
            mk = market(2)
            long_signal(mk)
            mk.present[missing] = False
            summary, trades, _, _ = simulate(mk, CFG, REF, ORIGIN, mk.end_ms)
            self.assertIsNone(summary['net_eur'])
            self.assertEqual(summary['halt']['reason'], expected)
            self.assertEqual(trades, [])
            if missing == 550:
                self.assertLess(summary['halt']['known_partial_cash_eur'], 0)
                self.assertEqual(summary['halt']['at_utc'], D.iso(mk.t(missing)))
                self.assertEqual(summary['halt']['entry_at_utc'], D.iso(mk.t(545)))

    def test_two_attempts_daily_budget_and_pause_from_actual_exit(self):
        mk = market(2)
        for base in [0, 1440]:
            long_signal(mk, base)
            quote(mk, base + 554, 1.1995)
            quote(mk, base + 555, 1.1995)
            quote(mk, base + 560, 1.2005)
        summary, trades, events, _ = simulate(mk, CFG, REF, ORIGIN, mk.end_ms)
        self.assertEqual(len(trades), 2)
        self.assertTrue(all(t['net_eur'] < 0 for t in trades))
        self.assertLessEqual(sum(t['planned_risk_eur'] for t in trades), 500)
        refusals = [e for e in events if 'PAUSE_AFTER_TWO_LOSSES' in e.get('refusal_reasons', [])]
        self.assertEqual(len(refusals), 2)
        self.assertEqual(summary['halt'], None)


if __name__ == '__main__':
    unittest.main()
