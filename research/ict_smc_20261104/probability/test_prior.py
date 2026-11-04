"""Causal probability diagnostics; synthetic trades only, no market backtest."""
import copy
import math
import unittest

from prior import CalibrationUnavailableError, summarize_prior, wilson_interval


class PriorDiagnosticsTests(unittest.TestCase):
    def test_empty_history_is_not_a_tradeable_fifty_percent_forecast(self):
        result = summarize_prior([], 1000)
        self.assertEqual(result['prior_n'], 0)
        self.assertEqual(result['laplace_win_probability_diagnostic'], 0.5)
        self.assertIsNone(result['empirical_win_fraction'])
        self.assertIsNone(result['wilson95_lower_descriptive'])
        self.assertFalse(result['probability_tradeable'])
        self.assertEqual(result['risk_multiplier'], 1.0)

    def test_future_and_unresolved_results_cannot_change_prior(self):
        known = [{'closed_at_ms': 10, 'net_eur': 50}, {'closed_at_ms': 20, 'net_eur': -20}]
        before = summarize_prior(known, 30)
        future = [{'closed_at_ms': 31, 'net_eur': 'not yet known'},
                  {'closed_at_ms': None, 'net_eur': None}]
        self.assertEqual(before, summarize_prior(known + future, 30))
        future[0]['net_eur'] = 10 ** 12
        self.assertEqual(before, summarize_prior(known + future, 30))

    def test_close_at_entry_is_included_using_declared_event_order(self):
        result = summarize_prior([{'closed_at_ms': 30, 'net_eur': 1},
                                  {'closed_at_ms': 31, 'net_eur': -1}], 30)
        self.assertEqual(result['prior_n'], 1)
        self.assertEqual(result['prior_wins'], 1)

    def test_zero_net_is_breakeven_and_nonwin_without_being_a_loss(self):
        trades = [{'closed_at_ms': i, 'net_eur': net} for i, net in enumerate([100, 50, -75, 0])]
        result = summarize_prior(trades, 10)
        self.assertEqual((result['prior_wins'], result['prior_losses'], result['prior_breakevens']), (2, 1, 1))
        self.assertEqual(result['laplace_win_probability_diagnostic'], 0.5)
        self.assertEqual(result['observed_mean_net_eur'], 18.75)

    def test_nominal_wilson_bounds_match_known_balanced_case_and_extremes(self):
        low, high = wilson_interval(50, 100)
        self.assertAlmostEqual(low, 0.4038315303659956)
        self.assertAlmostEqual(high, 0.5961684696340044)
        self.assertEqual(wilson_interval(0, 0), (None, None))
        self.assertAlmostEqual(wilson_interval(0, 1)[0], 0)
        self.assertAlmostEqual(wilson_interval(1, 1)[1], 1)

    def test_many_past_wins_cannot_unlock_larger_risk_or_a_calibration_flag(self):
        trades = [{'closed_at_ms': i, 'net_eur': 1} for i in range(200)]
        result = summarize_prior(trades, 1000)
        self.assertTrue(result['minimum_prior_trades_met'])
        self.assertGreater(result['wilson95_lower_descriptive'], 0.98)
        self.assertFalse(result['probability_tradeable'])
        self.assertEqual(result['risk_multiplier'], 1.0)
        with self.assertRaises(CalibrationUnavailableError):
            summarize_prior(trades, 1000, independent_calibration_verified=True)

    def test_input_is_not_mutated_and_order_does_not_change_result(self):
        trades = [{'closed_at_ms': 10, 'net_eur': '3'}, {'closed_at_ms': 20, 'net_eur': '-2'}]
        original = copy.deepcopy(trades)
        self.assertEqual(summarize_prior(trades, 30), summarize_prior(list(reversed(trades)), 30))
        self.assertEqual(trades, original)

    def test_bad_prior_outcome_and_fractional_timestamps_are_rejected(self):
        for net in [float('nan'), float('inf'), None]:
            with self.assertRaises(ValueError):
                summarize_prior([{'closed_at_ms': 10, 'net_eur': net}], 20)
        for entry in [True, 1.2, '1.2', float('inf')]:
            with self.assertRaises(ValueError):
                summarize_prior([], entry)
        for wins, total in [(2, 1), (-1, 5), (True, 2), (1, 1.5)]:
            with self.assertRaises(ValueError):
                wilson_interval(wins, total)


if __name__ == '__main__':
    unittest.main()
