"""No market cache imported. Cash expectations below are hand-computed per EUR unit."""
import copy
import unittest
import numpy as np
from backtest_bot.reference import D, X, ExecutionPathUnknown, ROOT
import json
from simple_forex.runner import parameters
from path import structural_path
from engine import simulate

ORIGIN = 1609718400000


def market(days=1):
    n = days * 1440
    px = {f'{side}_{field}': np.full(n, 2.0 + offset + delta)
          for side, offset in [('mid', 0), ('bid', -.01), ('ask', .01)]
          for field, delta in [('open', 0), ('close', 0), ('high', .01), ('low', -.01)]}
    return D.Market(ORIGIN, ORIGIN + n * D.MIN_MS, n, np.ones(n, bool), px,
        ORIGIN + np.arange(n) * D.MIN_MS + 100, 0, np.zeros(n, bool), np.zeros(n, bool))


def params(deadline=610):
    return {'costs': {'fee_round_trip_quote': .02, 'slip_quote_per_market_execution': .01,
        'tick_quote': .001, 'spread_multiplier': 1},
        'exit': {'max_holding_minutes': 1440, 'hard_exit_utc_minute': deadline}}


def path(mk, d, scenario, deadline=610):
    return structural_path(mk, 600, d, 1.9 if d == 1 else 2.1,
        2.3 if d == 1 else 1.7, params(deadline), scenario=scenario)


def set_open(mk, i, mid):
    for side, offset in [('mid', 0), ('bid', -.01), ('ask', .01)]:
        for field, delta in [('open', 0), ('close', 0), ('high', .01), ('low', -.01)]:
            mk.px[side + '_' + field][i] = mid + offset + delta


class GapTests(unittest.TestCase):
    def test_one_minute_long_short_three_scenarios_hand_cash(self):
        # Entry commission -.01/2=-.005. Stop exit: (-.13-.01)/2=-.07.
        # Target exit: (.28-.01)/2=.135. TIME exit: (-.04-.01)/2=-.025.
        for d in [1, -1]:
            for scenario, cash in [('S_CONT', -.03), ('S_PESS', -.075), ('S_OPT', .13)]:
                mk = market(); mk.present[601] = False
                result = path(mk, d, scenario)
                self.assertAlmostEqual(result['net_unit'], cash, places=12)
                self.assertEqual(result['closed_at_ms'], mk.t(610 if scenario == 'S_CONT' else 602))
                self.assertFalse(any(t == mk.t(601) for t in result['t']))

    def test_gap_beyond_stop_hand_fx_both_sides(self):
        for d, mid in [(1, 1.81), (-1, 2.19)]:
            for scenario in ['S_CONT', 'S_PESS']:
                mk = market(); mk.present[601] = False; set_open(mk, 602, mid)
                result = path(mk, d, scenario)
                self.assertAlmostEqual(result['net_unit'], -.005 - .24 / mid, places=12)
                self.assertEqual(result['fills'][-1]['fx'], mid)
            mk = market(); mk.present[601] = False; set_open(mk, 602, mid)
            self.assertAlmostEqual(path(mk, d, 'S_OPT')['net_unit'], -.005 + .27 / mid)

    def test_resume_beyond_target_caps_price_and_opt_converts_at_resume(self):
        for d, mid, target in [(1, 2.41, 2.3), (-1, 1.59, 1.7)]:
            for scenario in ['S_CONT', 'S_OPT']:
                mk = market(); mk.present[601] = False; set_open(mk, 602, mid)
                result = path(mk, d, scenario)
                self.assertEqual(result['fills'][-1]['price'], target)
                self.assertAlmostEqual(result['net_unit'], -.005 + .27 / mid, places=12)

    def test_deadline_missing_and_stop_priority_after_resume(self):
        mk = market(); mk.present[601] = False
        result = path(mk, 1, 'S_CONT', deadline=601)
        self.assertEqual(result['reason'], 'TIME')
        self.assertEqual(result['closed_at_ms'], mk.t(602))
        self.assertAlmostEqual(result['net_unit'], -.03)
        self.assertAlmostEqual(path(mk, 1, 'S_PESS', deadline=601)['net_unit'], -.075)
        self.assertAlmostEqual(path(mk, 1, 'S_OPT', deadline=601)['net_unit'], .13)
        mk.px['bid_low'][602], mk.px['bid_high'][602] = 1.8, 2.4
        result = path(mk, 1, 'S_CONT')
        self.assertEqual(result['reason'], 'SL')
        self.assertTrue(result['ambiguous_stop_and_target_same_m1'])
        self.assertAlmostEqual(result['net_unit'], -.075)

    def test_five_accepted_six_and_end_data_unresolved_preserve_entry_fee(self):
        for scenario in ['S_CONT', 'S_PESS', 'S_OPT']:
            mk = market(); mk.present[601:606] = False
            self.assertEqual(path(mk, 1, scenario)['gap_audit'][0]['missing_minutes'], 5)
            mk.present[606] = False
            with self.assertRaises(ExecutionPathUnknown) as caught:
                path(mk, 1, scenario)
            self.assertEqual(caught.exception.event['missing_minutes'], 6)
            self.assertAlmostEqual(caught.exception.event['known_realized_per_unit'], -.005)
            self.assertIsNone(caught.exception.event['total_net_pnl'])
            mk.present[601:] = False
            with self.assertRaises(ExecutionPathUnknown) as caught:
                path(mk, 1, scenario)
            self.assertEqual(caught.exception.event['reason'], 'DATA_END_BEFORE_EXIT')

    def test_multiple_holes_and_future_after_exit_cannot_change_cash(self):
        mk = market(); mk.present[[601, 604]] = False
        original = path(mk, 1, 'S_CONT')
        self.assertEqual(len(original['gap_audit']), 2)
        for values in mk.px.values(): values[611:] *= 10
        self.assertEqual(path(mk, 1, 'S_CONT'), original)


class AccountTests(unittest.TestCase):
    def cfg(self):
        return json.loads((ROOT / 'simple_forex/protocol_v03.json').read_text())

    def ref(self):
        return json.loads((ROOT / 'config/reference_params.json').read_text())

    def source(self, times):
        def signal(mk, day, tick):
            return [{'decision_ms': mk.t(i), 'reason': 'BREAKOUT', 'direction': 1,
                'stop': 1.9, 'range_high': 1.95, 'range_low': 1.85} for i in times], {'deadline_i': 960}
        return signal

    def test_entry_missing_is_refused_without_halt_or_consuming_quota(self):
        mk = market(); mk.present[600] = False
        cfg = self.cfg(); cfg['max_entries_per_day'] = 1
        out = simulate(mk, cfg, self.ref(), mk.origin_ms, mk.end_ms, signal_source=self.source([600, 610]))
        self.assertIsNone(out[0]['halt'])
        self.assertEqual(len(out[1]), 1)
        self.assertEqual(out[2][0]['refusal_reasons'], ['ENTRY_QUOTE_MISSING_REFUSED'])
        self.assertEqual(out[1][0]['entry_utc'], D.iso(mk.t(610)))

    def test_R2_portfolio_total_null_and_known_commission_retained(self):
        mk = market(); mk.present[601:607] = False
        out = simulate(mk, self.cfg(), self.ref(), mk.origin_ms, mk.end_ms,
            signal_source=self.source([600]))
        self.assertIsNone(out[0]['net_eur'])
        self.assertEqual(out[0]['halt']['reason'], 'UNRESOLVED_EXECUTION')
        self.assertEqual(out[1], [])
        self.assertAlmostEqual(out[0]['halt']['known_partial_cash_eur'], -.025)

    def test_future_quotes_do_not_rewrite_past_decisions(self):
        mk = market(); config = self.cfg()
        a = simulate(mk, config, self.ref(), mk.origin_ms, mk.end_ms, signal_source=self.source([600, 610]))
        for values in mk.px.values(): values[700:] *= 3
        b = simulate(mk, config, self.ref(), mk.origin_ms, mk.end_ms, signal_source=self.source([600, 610]))
        past = lambda out: [r for r in out[2] if r.get('decision_ms', mk.end_ms) <= mk.t(610)]
        self.assertEqual(past(a), past(b))

    def daily_source(self, times):
        def signal(mk, day, tick):
            import pandas as pd
            offset = int((pd.Timestamp(str(day), tz='UTC').value // 1000000 - mk.origin_ms) // D.MIN_MS)
            return [{'decision_ms': mk.t(offset + i), 'reason': 'BREAKOUT', 'direction': 1,
                'stop': 1.9, 'range_high': 1.95, 'range_low': 1.85} for i in times], {'deadline_i': offset + 960}
        return signal

    def test_four_entries_and_daily_reset_survive_all_scenarios(self):
        # Five proposed winners/day, one-minute TP closes; exactly four fills/day.
        for scenario in ['S_CONT', 'S_PESS', 'S_OPT']:
            mk = market(2)
            for day in [0, 1]:
                for minute in [600, 605, 610, 615, 620]:
                    for side, value in [('bid', 3), ('mid', 3.01), ('ask', 3.02)]:
                        mk.px[side + '_high'][day * 1440 + minute] = value
            out = simulate(mk, self.cfg(), self.ref(), mk.origin_ms, mk.end_ms,
                signal_source=self.daily_source([600,605,610,615,620]), scenario=scenario)
            self.assertEqual(len(out[1]), 8)
            for date in ['2021-01-04', '2021-01-05']:
                fills = [r for r in out[1] if r['day'] == date]
                self.assertEqual(len(fills), 4)
                self.assertLessEqual(sum(r['planned_risk_eur'] for r in fills), 500)
            self.assertEqual(sum('DAILY_ENTRY_LIMIT' in e.get('refusal_reasons', []) for e in out[2]), 2)

    def test_pause_after_two_losses_and_24h_expiry(self):
        for scenario in ['S_CONT', 'S_PESS', 'S_OPT']:
            mk = market(4)
            out = simulate(mk, self.cfg(), self.ref(), mk.origin_ms, mk.end_ms,
                signal_source=self.daily_source([600]), scenario=scenario)
            self.assertEqual([t['day'] for t in out[1]], ['2021-01-04','2021-01-05','2021-01-07'])
            refused = next(e for e in out[2] if e['day'] == '2021-01-06')
            self.assertEqual(refused['refusal_reasons'], ['PAUSE_AFTER_TWO_LOSSES'])


if __name__ == '__main__':
    unittest.main()
