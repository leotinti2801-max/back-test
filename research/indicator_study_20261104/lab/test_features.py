"""Causal and data-quality checks for the research annotations, not PnL tests."""
import unittest

import numpy as np
import pandas as pd

from backtest_bot.reference import D
from features import Features, previous_window


def ms(text):
    return int(pd.Timestamp(text).value // 1_000_000)


def market(days=8):
    n, origin = days * 1440, ms('2021-01-04T00:00:00Z')
    price = 1.2 + 0.001 * np.sin(np.arange(n) / 100)
    px = {side + '_' + field: price + offset + delta
          for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]
          for field, delta in [('open', 0), ('close', 0), ('high', 0.0001), ('low', -0.0001)]}
    return D.Market(origin, origin + n * D.MIN_MS, n, np.ones(n, bool), px,
                    origin + np.arange(n) * D.MIN_MS + 100, 0,
                    np.zeros(n, bool), np.zeros(n, bool))


class FeatureChecks(unittest.TestCase):
    def test_mutating_future_quotes_cannot_change_snapshot(self):
        mk = market()
        t = mk.t(4 * 1440 + 600)
        before = Features(mk).snapshot(t, 1, 1.201, 1.204, 1.199)
        self.assertGreater(before['confirmed_H1_pivots_available'], 0)
        for values in mk.px.values():
            values[mk.idx(t):] *= 3
        after = Features(mk).snapshot(t, 1, 1.201, 1.204, 1.199)
        self.assertEqual(before, after)

    def test_h1_pivot_is_unknown_until_second_right_bar_closes(self):
        mk = market()
        lab = Features(mk)
        pivot = lab.pivots[0]
        self.assertEqual(pivot.known_at_ms, lab.h1.close_ms(pivot.center + 2))
        before = lab.snapshot(pivot.known_at_ms - 5 * D.MIN_MS, 1)
        after = lab.snapshot(pivot.known_at_ms, 1)
        self.assertEqual(after['confirmed_H1_pivots_available'], before['confirmed_H1_pivots_available'] + 1)
        mk.present[pivot.center * 60] = False
        damaged = Features(mk)
        self.assertFalse(any(p.center == pivot.center for p in damaged.pivots))

    def test_gap_resets_indicator_seed_and_warmup(self):
        mk = market(1)
        mk.present[300] = False
        lab = Features(mk)
        self.assertIsNone(lab.snapshot(mk.t(305), 1)['ema20'])
        self.assertIsNone(lab.snapshot(mk.t(400), 1)['ema20'])
        self.assertIsNotNone(lab.snapshot(mk.t(405), 1)['ema20'])
        self.assertIsNone(lab.snapshot(mk.t(550), 1)['ema50'])
        self.assertIsNotNone(lab.snapshot(mk.t(555), 1)['ema50'])

    def test_partial_daily_extrema_never_become_qualified_levels(self):
        mk = market()
        t = mk.t(2 * 1440 + 600)
        start, end = previous_window(t, 'NY_DAY')
        mk.present[mk.idx(start) + 42] = False
        window = Features(mk).window(t, 'NY_DAY')
        self.assertFalse(window['complete'])
        self.assertEqual(window['observed_m1'], 1439)
        self.assertIsNotNone(window['observed_high'])
        self.assertEqual(window['levels'], [])

    def test_previous_day_skips_weekend_without_silently_skipping_missing_weekdays(self):
        start, end = previous_window(ms('2021-01-11T10:00:00Z'), 'NY_DAY')
        self.assertEqual(D.iso(start), '2021-01-07T22:00:00Z')
        self.assertEqual(D.iso(end), '2021-01-08T22:00:00Z')
        start, end = previous_window(ms('2021-01-11T10:00:00Z'), 'LONDON_SESSION')
        self.assertEqual(D.iso(start), '2021-01-08T08:00:00Z')
        self.assertEqual(D.iso(end), '2021-01-08T16:00:00Z')

    def test_local_boundaries_follow_dst_in_each_timezone(self):
        start, end = previous_window(ms('2021-03-15T10:00:00Z'), 'NY_DAY')
        self.assertEqual(D.iso(end), '2021-03-12T22:00:00Z')
        start, end = previous_window(ms('2021-03-16T10:00:00Z'), 'NY_DAY')
        self.assertEqual(D.iso(end), '2021-03-15T21:00:00Z')
        start, end = previous_window(ms('2021-03-30T10:00:00Z'), 'LONDON_SESSION')
        self.assertEqual(D.iso(start), '2021-03-29T07:00:00Z')
        self.assertEqual(D.iso(end), '2021-03-29T15:00:00Z')

    def test_opposing_level_ahead_of_exit_quote_may_be_below_paid_entry(self):
        mk = market()
        lab = Features(mk)
        t = mk.t(3 * 1440 + 600)
        # Isolate the distinction between the chart midpoint and an executable exit.
        lab.pivots = []
        ref = mk.px['mid_close'][mk.idx(t) - 1]
        levels = [{'name': 'behind_entry', 'kind': 'HIGH', 'mid': ref + 0.0002,
                   'bid': ref + 0.00015, 'ask': ref + 0.00025, 'known_at_ms': t - D.MIN_MS},
                  {'name': 'valid', 'kind': 'HIGH', 'mid': ref + 0.0004,
                   'bid': ref + 0.00035, 'ask': ref + 0.00045, 'known_at_ms': t - D.MIN_MS}]
        lab.window = lambda timestamp, kind: {'complete': True, 'status': 'COMPLETE',
            'observed_m1': 1440, 'expected_m1': 1440, 'observed_high': ref,
            'observed_low': ref, 'levels': levels if kind == 'NY_DAY' else []}
        row = lab.snapshot(t, 1, ref + 0.00025, ref + 0.0005, ref - 0.0005)
        self.assertEqual(row['nearest_resistance']['name'], 'behind_entry')
        self.assertEqual(row['nearest_opposing_executable_level']['name'], 'behind_entry')
        self.assertTrue(row['known_level_before_or_at_planned_target'])
        self.assertLess(row['level_distance_over_planned_stop'], 0)
        self.assertGreater(row['exit_close_to_level_over_planned_stop'], 0)
        lab.window = lambda timestamp, kind: {'complete': True, 'status': 'COMPLETE',
            'observed_m1': 1440, 'expected_m1': 1440, 'observed_high': ref,
            'observed_low': ref, 'levels': [levels[1]] if kind == 'NY_DAY' else []}
        row = lab.snapshot(t, 1, ref + 0.00025, levels[1]['bid'], ref - 0.0005)
        self.assertTrue(row['known_level_before_or_at_planned_target'])
        self.assertAlmostEqual(row['level_distance_over_planned_stop'], 0.0001 / 0.00075)

    def test_short_obstacle_uses_ask_and_includes_equality_with_target(self):
        mk = market()
        lab = Features(mk)
        lab.pivots = []
        t = mk.t(3 * 1440 + 600)
        ref = mk.px['mid_close'][mk.idx(t) - 1]
        level = {'name': 'support', 'kind': 'LOW', 'mid': ref - 0.0001,
                 'bid': ref - 0.00015, 'ask': ref - 0.00005, 'known_at_ms': t - D.MIN_MS}
        lab.window = lambda timestamp, kind: {'complete': True, 'status': 'COMPLETE',
            'observed_m1': 1440, 'expected_m1': 1440, 'observed_high': ref,
            'observed_low': ref, 'levels': [level] if kind == 'NY_DAY' else []}
        row = lab.snapshot(t, -1, ref - 0.00007, level['ask'], ref + 0.0005)
        self.assertEqual(row['nearest_opposing_executable_level']['name'], 'support')
        self.assertTrue(row['known_level_before_or_at_planned_target'])
        self.assertLess(row['level_distance_over_planned_stop'], 0)


if __name__ == '__main__':
    unittest.main()
