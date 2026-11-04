import unittest
import numpy as np
from statistics_frozen import draw_sessions, bootstrap_metrics, holm_two, inference


def strategy(net=1, n=100, halt=None):
    return {scenario + '/' + cost: {'halt': halt,
        'evaluation': {'trades': [], 'net_eur': net, 'closed_trades': n}}
        for scenario in ['S_CONT', 'S_PESS', 'S_OPT'] for cost in ['base', 'higher_costs']}


class StatisticsTests(unittest.TestCase):
    def test_blocks_non_circular_and_zero_trade_draw_hand_values(self):
        x = draw_sessions(12, draws=8)
        self.assertEqual(x.shape, (8, 12))
        self.assertTrue((x >= 0).all() and (x < 12).all())
        for row in x:
            self.assertTrue((np.diff(row[:5]) == 1).all())
            self.assertTrue((np.diff(row[5:10]) == 1).all())
        totals = [2, 0, -1, 0, 0]
        counts = [1, 0, 1, 0, 0]
        actual = bootstrap_metrics(totals, counts, np.array([[0,1,2,3,4], [1,1,1,1,1]]))
        np.testing.assert_equal(actual, [.5, 0])
        np.testing.assert_equal(draw_sessions(12), draw_sessions(12))

    def test_holm_exact_hand_values_and_strict_cutoff(self):
        self.assertEqual(holm_two({'V03': .01, 'V04': .015}), {'V03': .02, 'V04': .02})
        self.assertEqual(holm_two({'V03': .8, 'V04': .03}), {'V04': .06, 'V03': .8})
        self.assertEqual(holm_two({'V03': .025, 'V04': .04})['V03'], .05)

    def test_r2_any_run_overrides_negative_and_disables_both_p_values(self):
        a, b = strategy(net=-1), strategy()
        a['S_OPT/base']['halt'] = {'reason': 'UNRESOLVED_EXECUTION'}
        out = inference({'V03': a, 'V04': b})
        self.assertEqual(out['verdicts']['V03'], 'NON CONCLUANT')
        self.assertEqual(out['verdicts']['V04'], 'TESTÉ NON VALIDÉ')
        self.assertTrue(all(v['p_adjusted_Holm'] is None for v in out['diagnostics'].values()))

    def test_zero_trade_draws_and_negative_before_sample_size(self):
        out = inference({'V03': strategy(net=-1, n=2), 'V04': strategy(net=1, n=2)})
        self.assertEqual(out['verdicts'], {'V03': 'ARRÊT', 'V04': 'NON CONCLUANT'})
        self.assertEqual(out['diagnostics']['V04']['p_raw_user_rule'], 1)
        self.assertEqual(out['diagnostics']['V03']['p_adjusted_Holm'], 1)

    def test_holm_includes_other_strategy_even_when_it_stops(self):
        from statistics_frozen import sessions
        a, b = strategy(), strategy(net=-1)
        dates = sessions()[:100]
        a['S_CONT/higher_costs']['evaluation']['trades'] = [{'entry_utc': t.isoformat(), 'R': .1} for t in dates]
        b['S_CONT/higher_costs']['evaluation']['trades'] = [{'entry_utc': t.isoformat(), 'R': -.1} for t in dates]
        result = inference({'V03': a, 'V04': b})
        self.assertEqual(result['verdicts']['V03'], 'CANDIDAT À COLLECTE PROSPECTIVE')
        self.assertEqual(result['verdicts']['V04'], 'ARRÊT')
        self.assertEqual(result['diagnostics']['V04']['p_adjusted_Holm'], 1)


if __name__ == '__main__':
    unittest.main()
