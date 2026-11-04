"""Behavior checks for the new session/holding controls and data uncertainty."""
import json
import unittest

import numpy as np

from backtest_bot.reference import D, ROOT
from simple_forex import runner as frozen
from simple_forex.strategy_rearmed import signals as original_signals
import engine
from signals import signals


ORIGIN = 1609718400000  # Monday 4 January 2021, 00:00 UTC.


def market():
    n = 1440
    px = {f'{side}_{field}': np.full(n, 1.2 + offset + delta)
        for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]
        for field, delta in [('open', 0), ('close', 0), ('high', 0.0001), ('low', -0.0001)]}
    return D.Market(ORIGIN, ORIGIN + n * D.MIN_MS, n, np.ones(n, bool), px,
        ORIGIN + np.arange(n) * D.MIN_MS + 100, 0, np.zeros(n, bool), np.zeros(n, bool))


def config():
    return json.loads((ROOT / 'simple_forex/protocol_v03.json').read_text())


def reference():
    return json.loads((ROOT / 'config/reference_params.json').read_text())


def source(times):
    def events(mk, day, tick):
        return [{'decision_ms': mk.t(i), 'reason': 'BREAKOUT', 'direction': 1,
                 'range_high': 1.199, 'range_low': 1.18, 'stop': 1.19} for i in times], {'deadline_i': 1020}
    return events


class ResearchControls(unittest.TestCase):
    def test_default_signal_equals_frozen_and_clone_does_not_patch_globals(self):
        mk = market()
        self.assertEqual(signals(mk, '2021-01-04'), original_signals(mk, '2021-01-04'))
        self.assertIs(engine._simulate.__code__, frozen.simulate.__code__)
        self.assertEqual(engine._simulate.__defaults__, frozen.simulate.__defaults__)
        self.assertIs(frozen.simulate.__globals__['parameters'], frozen.parameters)
        self.assertIsNot(engine._simulate.__globals__, frozen.simulate.__globals__)

    def test_m1_uses_closed_bar_and_rearms_only_after_interior_close(self):
        mk = market()
        mk.px['mid_close'][540:544] = [1.201, 1.201, 1.2, 1.199]
        raw, _ = signals(mk, '2021-01-04', minutes=1)
        crosses = [r for r in raw if r['reason'] == 'BREAKOUT']
        self.assertEqual([r['decision_ms'] for r in crosses[:2]], [mk.t(541), mk.t(544)])
        self.assertEqual([r['direction'] for r in crosses[:2]], [1, -1])
        past = [r for r in raw if r['decision_ms'] <= mk.t(544)]
        for values in mk.px.values():
            values[544:] *= 3
        after, _ = signals(mk, '2021-01-04', minutes=1)
        self.assertEqual(past, [r for r in after if r['decision_ms'] <= mk.t(544)])

    def test_sixty_minute_exit_frees_the_position_at_exact_next_signal(self):
        mk, cfg = market(), config()
        cfg['research_max_holding_minutes'] = 60
        short = engine.simulate(mk, cfg, reference(), mk.origin_ms, mk.end_ms, signal_source=source([600, 660]))
        original = frozen.simulate(mk, cfg, reference(), mk.origin_ms, mk.end_ms, signal_source=source([600, 660]))
        self.assertEqual(len(short[1]), 2)
        self.assertEqual(short[1][0]['exit_utc'], D.iso(mk.t(660)))
        self.assertEqual(short[1][1]['entry_utc'], D.iso(mk.t(660)))
        self.assertEqual(len(original[1]), 1)
        self.assertEqual(original[2][1]['refusal_reasons'], ['POSITION_OPEN'])
        self.assertEqual(frozen.parameters(reference(), cfg, mk.t(1020), False)['exit']['max_holding_minutes'], 1440)

    def test_missing_exposure_still_halts_with_unknown_total(self):
        mk, cfg = market(), config()
        cfg['research_max_holding_minutes'] = 60
        mk.present[601] = False
        summary, trades, _, _ = engine.simulate(mk, cfg, reference(), mk.origin_ms, mk.end_ms,
            signal_source=source([600]))
        self.assertIsNone(summary['net_eur'])
        self.assertEqual(trades, [])
        self.assertEqual(summary['halt']['at_utc'], D.iso(mk.t(601)))
        self.assertLess(summary['halt']['known_partial_cash_eur'], 0)

    def test_extra_capacity_does_not_remove_pause_after_two_actual_losses(self):
        mk, cfg = market(), config()
        cfg.update(research_max_holding_minutes=60, risk_budget_per_trade_eur=62.5, max_entries_per_day=8)
        summary, trades, events, _ = engine.simulate(mk, cfg, reference(), mk.origin_ms, mk.end_ms,
            signal_source=source([600, 661, 722]))
        self.assertEqual(len(trades), 2)
        self.assertTrue(all(t['net_eur'] < 0 for t in trades))
        self.assertLessEqual(sum(t['planned_risk_eur'] for t in trades), 500)
        self.assertEqual(next(e for e in events if e.get('decision_ms') == mk.t(722))['refusal_reasons'], ['PAUSE_AFTER_TWO_LOSSES'])

    def test_durations_sessions_and_unknown_signal_keep_calendar_minutes(self):
        mk = market()
        _, session = signals(mk, '2021-01-04', entry_end='16:00', hard_exit='17:00')
        self.assertEqual(session['deadline_i'], 1020)
        mk.present[551] = False
        raw, _ = signals(mk, '2021-01-04', minutes=1)
        self.assertEqual(raw[-1]['reason'], 'SIGNAL_DATA_INCOMPLETE_SESSION_CANCELLED')
        self.assertEqual(raw[-1]['decision_ms'], mk.t(552))
        with self.assertRaises(ValueError):
            signals(mk, '2021-01-04', entry_end='17:00', hard_exit='16:00')


if __name__ == '__main__':
    unittest.main()
