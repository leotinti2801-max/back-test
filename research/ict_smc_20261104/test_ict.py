import unittest
import json
import numpy as np
from backtest_bot.reference import D, ROOT
from simple_forex import runner as core
from strategy import ICT
from engine import order, simulate, _simulate

ORIGIN = 1609718400000


def market():
    n = 1440
    px = {f'{side}_{field}': np.full(n, 1.2 + offset + delta)
        for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]
        for field, delta in [('open', 0), ('close', 0), ('high', 0.0001), ('low', -0.0001)]}
    return D.Market(ORIGIN, ORIGIN + n * D.MIN_MS, n, np.ones(n, bool), px,
        ORIGIN + np.arange(n) * D.MIN_MS + 100, 0, np.zeros(n, bool), np.zeros(n, bool))


def bar(mk, minute, o, h, lo, c):
    assert lo <= min(o, c) <= max(o, c) <= h
    for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]:
        for field, value in [('open', o), ('high', h), ('low', lo), ('close', c)]:
            mk.px[side + '_' + field][minute:minute + 5] = value + offset


def fixture():
    mk = market()
    bar(mk, 480, 1.2, 1.205, 1.199, 1.2)
    bar(mk, 520, 1.2, 1.2008, 1.1999, 1.2)
    bar(mk, 540, 1.2, 1.2000, 1.1988, 1.1998)
    bar(mk, 545, 1.2002, 1.20095, 1.2002, 1.2009)
    bar(mk, 550, 1.20015, 1.2003, 1.2, 1.20015)
    bar(mk, 555, 1.20015, 1.2003, 1.2, 1.20015)
    return mk


def cfg():
    return json.loads((ROOT / 'simple_forex/protocol_v04.json').read_text())


def ref():
    return json.loads((ROOT / 'config/reference_params.json').read_text())


class ICTChecks(unittest.TestCase):
    def test_sweep_mss_fvg_return_are_strictly_separate_closed_bars(self):
        mk = fixture()
        raw, _ = ICT(mk).signals(mk, '2021-01-04')
        entered = next(r for r in raw if r['reason'] == 'BREAKOUT')
        self.assertEqual(entered['decision_ms'], mk.t(555))
        p = entered['setup']
        self.assertLess(p['sweep_known_at_ms'], p['mss_known_at_ms'])
        self.assertLess(p['mss_known_at_ms'], entered['decision_ms'])
        self.assertLessEqual(p['mss_pivot_known_at_ms'], p['sweep_known_at_ms'])
        self.assertAlmostEqual(entered['fvg_low'], 1.2001)
        self.assertAlmostEqual(entered['fvg_high'], 1.2002)

    def test_future_suffix_cannot_change_prior_setups(self):
        mk = fixture()
        cutoff = mk.t(555)
        before, _ = ICT(mk).signals(mk, '2021-01-04')
        for values in mk.px.values():
            values[555:] *= 4
        after, _ = ICT(mk).signals(mk, '2021-01-04')
        self.assertEqual([r for r in before if r['decision_ms'] <= cutoff],
                         [r for r in after if r['decision_ms'] <= cutoff])

    def test_mirrored_bearish_setup_and_return_expiration(self):
        mk = fixture()
        original = {k: v.copy() for k, v in mk.px.items()}
        for side, counterpart in [('mid', 'mid'), ('bid', 'ask'), ('ask', 'bid')]:
            for field, opposite in [('open', 'open'), ('close', 'close'), ('high', 'low'), ('low', 'high')]:
                mk.px[side + '_' + field] = 2.4 - original[counterpart + '_' + opposite]
        raw, _ = ICT(mk).signals(mk, '2021-01-04')
        entry = next(r for r in raw if r['reason'] == 'BREAKOUT')
        self.assertEqual(entry['direction'], -1)
        self.assertEqual(entry['decision_ms'], mk.t(555))
        mk = fixture()
        for minute in range(550, 585, 5):
            bar(mk, minute, 1.2006, 1.2007, 1.2004, 1.2006)
        raw, _ = ICT(mk).signals(mk, '2021-01-04')
        self.assertEqual(next(r for r in raw if r['decision_ms'] == mk.t(585))['reason'], 'SETUP_EXPIRED_RETURN')
        self.assertFalse(any(r['reason'] == 'BREAKOUT' for r in raw))

    def test_gapped_doji_cannot_be_directional_displacement_at_zero_atr(self):
        mk = fixture()
        bar(mk, 545, 1.2009, 1.20095, 1.2002, 1.2009)
        model = ICT(mk)
        model.values['atr14'][108] = 0
        raw, _ = model.signals(mk, '2021-01-04')
        self.assertIn('DISPLACEMENT_NON_DIRECTIONAL', next(r for r in raw if r['reason'] == 'FIRST_MSS_REJECTED')['rejection_reasons'])

    def test_stop_touch_in_return_bar_invalidates_before_entry(self):
        mk = fixture()
        bar(mk, 550, 1.20015, 1.2003, 1.1985, 1.20015)
        raw, _ = ICT(mk).signals(mk, '2021-01-04')
        self.assertEqual(next(r for r in raw if r['decision_ms'] == mk.t(555))['reason'], 'SETUP_STOP_INVALIDATED')
        self.assertFalse(any(r['reason'] == 'BREAKOUT' for r in raw))

    def test_both_sides_sweep_and_first_mss_without_fvg_are_rejected(self):
        mk = fixture()
        bar(mk, 540, 1.2, 1.206, 1.1988, 1.1998)
        raw, _ = ICT(mk).signals(mk, '2021-01-04')
        self.assertEqual(next(r for r in raw if r['decision_ms'] == mk.t(545))['reason'], 'SWEEP_BOTH_SIDES_AMBIGUOUS')
        mk = fixture()
        bar(mk, 545, 1.2000, 1.20095, 1.2000, 1.2009)
        raw, _ = ICT(mk).signals(mk, '2021-01-04')
        rejected = next(r for r in raw if r['reason'] == 'FIRST_MSS_REJECTED')
        self.assertIn('NO_DIRECTIONAL_FVG', rejected['rejection_reasons'])
        self.assertFalse(any(r['reason'] == 'BREAKOUT' for r in raw))

    def test_previous_atr_missing_is_not_silently_replaced(self):
        mk = fixture()
        model = ICT(mk)
        model.values['atr14'][108] = np.nan
        raw, _ = model.signals(mk, '2021-01-04')
        self.assertIn('ATR_PREVIOUS_UNKNOWN', next(r for r in raw if r['reason'] == 'FIRST_MSS_REJECTED')['rejection_reasons'])

    def test_signal_gap_cancels_session_and_exposure_gap_halts_portfolio(self):
        mk = fixture()
        mk.present[556] = False
        model = ICT(mk)
        raw, _ = model.signals(mk, '2021-01-04')
        self.assertEqual(raw[-1]['reason'], 'SIGNAL_GAP_SESSION_CANCELLED')
        summary, trades, _, _ = simulate(mk, cfg(), ref(), mk.origin_ms, mk.end_ms, signal_source=model.signals)
        self.assertIsNone(summary['net_eur'])
        self.assertEqual(trades, [])
        self.assertEqual(summary['halt']['at_utc'], D.iso(mk.t(556)))
        self.assertLess(summary['halt']['known_partial_cash_eur'], 0)

    def test_order_checks_real_quote_and_structural_reward_both_directions(self):
        mk, config = market(), cfg()
        params = core.parameters(ref(), config, mk.t(960), False)
        for d in [1, -1]:
            event = {'direction': d, 'stop': 1.199 if d == 1 else 1.201,
                'structural_target': 1.203 if d == 1 else 1.197,
                'fvg_low': 1.1999, 'fvg_high': 1.2002, 'setup': {}}
            result = order(mk, 600, event, params, config, 100000)
            self.assertEqual(result['reasons'], [])
            self.assertGreaterEqual(result['planned_net_quote_R'], 2)
            self.assertLessEqual(result['planned_risk_eur'], 125)
            event['structural_target'] = 1.2002 if d == 1 else 1.1998
            self.assertIn('STRUCTURAL_TARGET_BELOW_2R', order(mk, 600, event, params, config, 100000)['reasons'])
            event['fvg_low'], event['fvg_high'] = 1.21, 1.22
            self.assertIn('ENTRY_QUOTE_OUTSIDE_FVG', order(mk, 600, event, params, config, 100000)['reasons'])
        self.assertIs(_simulate.__code__, core.simulate.__code__)
        self.assertIs(core.simulate.__globals__['order'], core.order)


if __name__ == '__main__':
    unittest.main()
