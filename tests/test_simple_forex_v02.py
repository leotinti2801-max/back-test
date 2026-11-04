import copy
import json
import unittest

from backtest_bot.reference import D, ROOT
from simple_forex.runner import simulate, order, parameters
from simple_forex.strategy_v02 import signals
from simple_forex.strategy_rearmed import signals as fresh_cross
from test_research import ORIGIN, REF, market
from test_simple_forex import quote

CFG = json.loads((ROOT / 'simple_forex/protocol_v02.json').read_text())


def cycles(mk, count, exit_mode=None):
    for j in range(count):
        first = 544 + 15 * j
        quote(mk, first, 1.2006)       # Breakout M5 closes at first+1.
        quote(mk, first + 5, 1.2006)   # Later M5 touches the level and reclaims it.
        quote(mk, first + 6, 1.2006)   # Opening quote for the candidate entry.
        if exit_mode:
            quote(mk, first + 7, 1.204 if exit_mode == 'win' else 1.1992)


class RetestTests(unittest.TestCase):
    def test_frequency_probe_needs_a_fresh_interior_close(self):
        mk = market()
        quote(mk, 544, 1.2006)
        quote(mk, 549, 1.2006)
        quote(mk, 559, 1.2006)
        events, _ = fresh_cross(mk, '2021-01-04')
        candidates = [e for e in events if e['reason'] == 'BREAKOUT']
        self.assertEqual([e['decision_ms'] for e in candidates], [mk.t(545), mk.t(560)])
        self.assertTrue(all(abs(e['stop'] - 1.19984) < 1e-12 for e in candidates))

    def test_frequency_probe_has_no_future_suffix_dependency(self):
        mk = market()
        quote(mk, 544, 1.2006)
        before, _ = fresh_cross(mk, '2021-01-04')
        for values in mk.px.values():
            values[550:] *= 3
        mk.n, mk.end_ms = 550, mk.t(550)
        after, _ = fresh_cross(mk, '2021-01-04')
        self.assertEqual([e for e in before if e['decision_ms'] <= mk.t(550)],
                         [e for e in after if e['decision_ms'] <= mk.t(550)])

    def test_breakout_candle_cannot_confirm_its_own_retest(self):
        mk = market()
        quote(mk, 544, 1.2006)
        for i in range(545, 550):
            quote(mk, i, 1.2006)
        events, _ = signals(mk, '2021-01-04')
        at = {e['decision_ms']: e for e in events}
        self.assertEqual(at[mk.t(545)]['reason'], 'BREAKOUT_ARMED')
        self.assertEqual(at[mk.t(550)]['reason'], 'WAIT_FOR_RETEST')

    def test_retest_is_later_and_stop_uses_only_closed_executable_side(self):
        mk = market()
        cycles(mk, 1)
        events, _ = signals(mk, '2021-01-04')
        entry = next(e for e in events if e['reason'] == 'BREAKOUT')
        self.assertEqual(entry['decision_ms'], mk.t(550))
        self.assertAlmostEqual(entry['stop'], mk.px['bid_low'][545:550].min() - 0.00001)
        mk.px['bid_low'][551] = 0.1
        after, _ = signals(mk, '2021-01-04')
        self.assertEqual(entry, next(e for e in after if e['reason'] == 'BREAKOUT'))

    def test_reclaim_is_consumed_even_if_later_bars_touch_again(self):
        mk = market()
        cycles(mk, 1)
        quote(mk, 554, 1.2006)
        quote(mk, 559, 1.2006)
        events, _ = signals(mk, '2021-01-04')
        self.assertEqual(sum(e['reason'] == 'BREAKOUT' for e in events), 1)

    def test_fresh_inside_close_rearms_more_than_two_signals(self):
        mk = market()
        cycles(mk, 5)
        events, _ = signals(mk, '2021-01-04')
        self.assertEqual(sum(e['reason'] == 'BREAKOUT' for e in events), 5)

    def test_opposite_jump_does_not_rearm_without_inside_close(self):
        mk = market()
        quote(mk, 544, 1.2006)
        quote(mk, 549, 1.1994)
        quote(mk, 554, 1.1993)
        quote(mk, 564, 1.1994)
        quote(mk, 569, 1.1994)
        events, _ = signals(mk, '2021-01-04')
        entries = [e for e in events if e['reason'] == 'BREAKOUT']
        self.assertEqual([(e['decision_ms'], e['direction']) for e in entries], [(mk.t(570), -1)])
        self.assertAlmostEqual(entries[0]['stop'], mk.px['ask_high'][565:570].max() + 0.00001)

    def test_future_suffix_and_grid_end_preserve_past_signal(self):
        mk = market()
        cycles(mk, 1)
        before, _ = signals(mk, '2021-01-04')
        cutoff = mk.t(550)
        for values in mk.px.values():
            values[550:] *= 3
        mk.n, mk.end_ms = 550, mk.t(550)
        after, _ = signals(mk, '2021-01-04')
        self.assertEqual([e for e in before if e['decision_ms'] <= cutoff],
                         [e for e in after if e['decision_ms'] <= cutoff])

    def test_gap_cancels_an_unobservable_retest(self):
        mk = market()
        cycles(mk, 1)
        mk.present[547] = False
        events, _ = signals(mk, '2021-01-04')
        self.assertEqual(events[-1]['reason'], 'SIGNAL_DATA_INCOMPLETE_SESSION_CANCELLED')
        self.assertFalse(any(e['reason'] == 'BREAKOUT' for e in events))

    def test_end_time_exclusive_before_paris_exclusion(self):
        mk = market()
        quote(mk, 859, 1.2006)
        quote(mk, 864, 1.2006)
        events, _ = signals(mk, '2021-01-04')
        self.assertEqual(max(e['decision_ms'] for e in events), mk.t(865))
        self.assertTrue(any(e['reason'] == 'BREAKOUT' and e['decision_ms'] == mk.t(865) for e in events))

    def test_refused_candidate_does_not_use_one_of_four_real_entries(self):
        mk = market()
        cycles(mk, 6, exit_mode='win')
        mk.first_ts[550] = mk.t(550) + 6000
        m, trades, events, _ = simulate(mk, CFG, REF, ORIGIN, mk.end_ms, signal_source=signals)
        self.assertEqual(len(trades), 4)
        self.assertLessEqual(sum(t['planned_risk_eur'] for t in trades), 500)
        self.assertTrue(all(t['planned_risk_eur'] <= 125 for t in trades))
        reasons = [r for e in events for r in e.get('refusal_reasons', [])]
        self.assertIn('FIRST_TICK_LATE', reasons)
        self.assertIn('DAILY_ENTRY_LIMIT', reasons)
        self.assertIsNone(m['halt'])

    def test_positions_do_not_overlap_and_two_losses_still_pause(self):
        for mode, expected in [(None, 1), ('loss', 2)]:
            mk = market()
            cycles(mk, 6, exit_mode=mode)
            m, trades, events, _ = simulate(mk, CFG, REF, ORIGIN, mk.end_ms, signal_source=signals)
            self.assertEqual(len(trades), expected)
            reason = 'POSITION_OPEN' if mode is None else 'PAUSE_AFTER_TWO_LOSSES'
            self.assertTrue(any(reason in e.get('refusal_reasons', []) for e in events))

    def test_all_three_targets_include_costs_at_same_small_risk(self):
        mk = market()
        cycles(mk, 1)
        event = next(e for e in signals(mk, '2021-01-04')[0] if e['reason'] == 'BREAKOUT')
        for rr in [2, 3, 4]:
            cfg = copy.deepcopy(CFG)
            cfg['planned_quote_reward_risk'] = rr
            p = parameters(REF, cfg, mk.t(960), False)
            check = order(mk, 550, event, p, cfg, 100000)
            self.assertEqual(check['reasons'], [])
            self.assertLessEqual(check['planned_risk_eur'], 125)
            gain = check['target'] - check['entry_price'] - 0.00005
            risk = check['entry_price'] - check['stop'] + 0.00006
            self.assertAlmostEqual(gain / risk, rr)


if __name__ == '__main__':
    unittest.main()
