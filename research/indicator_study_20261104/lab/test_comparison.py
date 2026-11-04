"""Verify that the opt-in filter cancels an entry before quote/account handling."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from backtest_bot.reference import ROOT, D
from simple_forex.runner import simulate
from test_features import market
from trend_filter import filtered_signals


class FilterIntegrationCheck(unittest.TestCase):
    def test_filter_refusal_needs_no_quote_and_does_not_use_entry_quota(self):
        mk = market(1)
        mk.present[600] = False
        cfg = json.loads((ROOT / 'simple_forex/protocol_v03.json').read_text())
        cfg['max_entries_per_day'] = 1
        reference = json.loads((ROOT / 'config/reference_params.json').read_text())
        m5 = D.make_bars(mk, 5, 'M5')
        fast, slow = np.ones(m5.n), np.full(m5.n, 2.0)
        fast[m5.slot_of_close(mk.t(800))] = 3
        feature = SimpleNamespace(m5=m5, values={'ema20': fast, 'ema50': slow})
        events = [{'decision_ms': mk.t(i), 'reason': 'BREAKOUT', 'direction': 1,
                   'stop': 1.19, 'range_high': 1.199, 'range_low': 1.18} for i in [600, 800]]
        with patch('trend_filter.range_signals', return_value=(events, {'deadline_i': 960})):
            summary, trades, decisions, _ = simulate(mk, cfg, reference, mk.origin_ms, mk.end_ms,
                signal_source=filtered_signals(feature))
        self.assertIsNone(summary['halt'])
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['entry_utc'], D.iso(mk.t(800)))
        self.assertEqual(decisions[0]['reason'], 'FILTER_REFUSED_EMA_DIRECTION')
        self.assertEqual(decisions[0]['account_checks_status'], 'NOT_EVALUATED_AFTER_FILTER_REJECTION')
        self.assertEqual(decisions[1]['reason'], 'ENTERED')


if __name__ == '__main__':
    unittest.main()
