import copy
import json
import pickle
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from backtest_bot.data import CacheReader
from backtest_bot.reference import B, D, ROOT, X, ExecutionPathUnknown
from backtest_bot.research import select_development
from backtest_bot.simulation import allowed_time, run_period
from backtest_bot.strategy import (Pending, entry_check, fixed_target, impulse_records,
                                   make_params, preknown_target, build_context, shared_structures)


SPEC = json.loads((ROOT / 'config/research_v02.json').read_text())
REF = json.loads((ROOT / 'config/reference_params.json').read_text())
C = SPEC['fixed_controls']
CANDIDATE = SPEC['candidates'][2]
P = make_params(REF, C, CANDIDATE)
ORIGIN = int(pd.Timestamp('2021-01-04T00:00:00Z').value // 1_000_000)


def market(days=1):
    n = days * 1440
    px = {}
    for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]:
        for field, delta in [('open', 0), ('close', 0), ('high', 0.0001), ('low', -0.0001)]:
            px[f'{side}_{field}'] = np.full(n, 1.2 + offset + delta)
    first = ORIGIN + np.arange(n, dtype=np.int64) * D.MIN_MS + 100
    return D.Market(ORIGIN, ORIGIN + n * D.MIN_MS, n, np.ones(n, bool), px, first,
                    0, np.zeros(n, bool), np.zeros(n, bool))


def pending(d=1):
    return Pending('test', d, ORIGIN + 600 * D.MIN_MS, 1.1998, 1.2002,
                   1.199 if d == 1 else 1.201, ORIGIN + 1200 * D.MIN_MS, 0.001)


def context(mk):
    events = []
    for day in range(mk.n // 1440):
        for minute in (600, 780):
            t = ORIGIN + (day * 1440 + minute) * D.MIN_MS
            events.append(SimpleNamespace(
                direction=1, close_ms=t, static_reasons=[], zone_lo=1.1998, zone_hi=1.2002,
                poi_bid_low=1.1991, poi_ask_high=1.2003, atr_ref=0.001,
            ))
    return SimpleNamespace(market=mk, bos=events, bias=SimpleNamespace(state_at=lambda t: B.BULL),
                           m30=D.make_bars(mk, 30, 'M30'))


class CausalityAndExecutionTests(unittest.TestCase):
    def test_fixed_target_net_ratio_and_budget_both_directions(self):
        for d in (1, -1):
            mk, setup = market(), pending(d)
            check = entry_check(mk, 601, setup, P, CANDIDATE, 100000)
            self.assertEqual(check['reasons'], [])
            self.assertAlmostEqual(check['reward_risk'], 2.0)
            self.assertLessEqual(check['planned_risk_eur'], 250)
            self.assertEqual(check['qty'] % 2000, 0)
            self.assertEqual(setup.target_known_at_ms, mk.t(601))

    def test_future_high_low_cannot_move_entry_or_target(self):
        mk, setup = market(), pending()
        initial = entry_check(mk, 601, setup, P, CANDIDATE, 100000)
        target = setup.target
        for name in mk.px:
            mk.px[name][602:] *= 3
        repeated = entry_check(mk, 601, setup, P, CANDIDATE, 100000)
        self.assertEqual(initial, repeated)
        self.assertEqual(target, setup.target)

    def test_stop_and_target_same_minute_stop_wins(self):
        mk, setup = market(), pending()
        check = entry_check(mk, 601, setup, P, CANDIDATE, 100000)
        mk.px['bid_low'][601] = setup.stop - 0.0001
        mk.px['bid_high'][601] = setup.target + 0.0001
        path = X.structural_path(mk, 601, 1, setup.stop, setup.target, P)
        self.assertEqual(path['reason'], 'SL')
        self.assertTrue(path['ambiguous_stop_and_target_same_m1'])
        self.assertAlmostEqual(path['net_unit'] * check['qty'] / check['planned_risk_eur'], -1)

    def test_target_fills_executable_side_and_fees(self):
        for d, side in [(1, 'bid_high'), (-1, 'ask_low')]:
            mk, setup = market(), pending(d)
            check = entry_check(mk, 601, setup, P, CANDIDATE, 100000)
            mk.px[side][601] = setup.target + d * 0.00002
            path = X.structural_path(mk, 601, d, setup.stop, setup.target, P)
            self.assertEqual(path['reason'], 'TP')
            self.assertAlmostEqual(path['net_unit'] / check['risk_unit_eur'], 2)
            self.assertGreater(path['flow_summary_per_unit']['commission_eur'], 0)

    def test_missing_exposure_is_unknown_keeps_entry_commission(self):
        mk, setup = market(), pending()
        entry_check(mk, 601, setup, P, CANDIDATE, 100000)
        mk.present[602] = False
        with self.assertRaises(ExecutionPathUnknown) as caught:
            X.structural_path(mk, 601, 1, setup.stop, setup.target, P)
        event = caught.exception.event
        self.assertIsNone(event['total_net_pnl'])
        self.assertEqual(event['remaining_fraction'], 1)
        self.assertLess(event['known_realized_per_unit'], 0)

    def test_impulse_cannot_reuse_stale_h4(self):
        mk = market()
        mk.px['mid_close'][239] += 0.001
        mk.px['mid_high'][:240] += 0.001
        mk.present[240] = False
        records = impulse_records(D.make_bars(mk, 240, 'H4'), 0.25)
        self.assertEqual(records[0].state, B.BULL)
        self.assertEqual(records[1].state, B.SUSPENDED)

    def test_context_without_shared_cache_honours_candidate_bias(self):
        mk = market()
        ctx = build_context(mk, P, C, CANDIDATE)
        self.assertEqual(ctx.bias.state_at(ORIGIN + 240 * D.MIN_MS), B.NEUTRAL)

    def test_future_suffix_cannot_change_past_h4_bias(self):
        mk = market(2)
        first = impulse_records(D.make_bars(mk, 240, 'H4'), 0.25)
        for values in mk.px.values():
            values[1440:] *= 2
        after = impulse_records(D.make_bars(mk, 240, 'H4'), 0.25)
        self.assertEqual([r.state for r in first[:6]], [r.state for r in after[:6]])

    def test_future_prices_cannot_rewrite_past_breakouts_or_pivots(self):
        from dataclasses import asdict
        mk = market(8)
        minute = np.arange(mk.n)
        center = 1.2 + minute * 0.0000004 + 0.001 * np.sin(minute / 100) + 0.0002 * np.sin(minute / 10)
        for side, offset in [('mid', 0), ('bid', -0.00005), ('ask', 0.00005)]:
            for field, delta in [('open', 0), ('close', 0), ('high', 0.0001), ('low', -0.0001)]:
                mk.px[f'{side}_{field}'] = center + offset + delta
        cutoff = ORIGIN + 5 * D.DAY_MS

        def past_context():
            ctx = build_context(mk, P, C, CANDIDATE, shared_structures(mk, P))
            events = [asdict(e) for e in ctx.bos if e.close_ms <= cutoff]
            pivots = [asdict(p) for p in ctx.m30_pivots if p.known_at_ms <= cutoff]
            self.assertTrue(events)
            self.assertTrue(pivots)
            return json.dumps([events, pivots], sort_keys=True)

        before = past_context()
        for values in mk.px.values():
            values[5 * 1440:] *= 4
        self.assertEqual(before, past_context())

    def test_known_target_excludes_broken_visited_and_unknown_pivots(self):
        mk = market()
        pv = SimpleNamespace(kind='HIGH', known_at_ms=mk.t(500), pivot_time_ms=mk.t(440),
                             pid='old', price=1.205, bid_high=1.20495)
        event = SimpleNamespace(direction=1, close_ms=mk.t(600), level_pid='broken', zone_hi=1.2002)
        ctx = SimpleNamespace(market=mk, m30_pivots=[pv])
        self.assertEqual(preknown_target(ctx, event, 0.00001)[0], pv.bid_high)
        event.level_pid = 'old'
        self.assertEqual(preknown_target(ctx, event, 0.00001), (None, None))
        event.level_pid = 'broken'
        mk.px['bid_high'][550] = 1.206
        self.assertEqual(preknown_target(ctx, event, 0.00001), (None, None))
        mk.px['bid_high'][550] = 1.20005
        mk.present[550] = False
        self.assertEqual(preknown_target(ctx, event, 0.00001), (None, None))

    def test_single_entry_per_day_and_pause_after_two_losses(self):
        mk = market(4)
        report, trades, decisions = run_period(context(mk), P, CANDIDATE, C, ORIGIN, mk.end_ms)
        self.assertEqual(report['closed_trades'], 4)
        self.assertEqual(report['counts']['PAUSE_AFTER_TWO_LOSSES'], 2)
        dates = [t['entry_utc'][:10] for t in trades]
        self.assertEqual(len(dates), len(set(dates)))
        # The morning setup is blocked; a genuinely new afternoon setup is allowed
        # after exactly 24 h from the second loss's close.
        self.assertEqual(trades[2]['entry_utc'], '2021-01-06T13:01:00Z')
        self.assertGreaterEqual(pd.Timestamp(trades[2]['entry_utc']) - pd.Timestamp(trades[1]['exit_utc']),
                                pd.Timedelta(hours=24))
        self.assertTrue(all(t['planned_risk_eur'] <= 250 for t in trades))

    def test_feed_gap_does_not_disappear_from_portfolio(self):
        mk = market(4)
        mk.present[602] = False
        report, trades, decisions = run_period(context(mk), P, CANDIDATE, C, ORIGIN, mk.end_ms)
        self.assertEqual(report['halt']['reason'], 'UNRESOLVED_EXECUTION')
        self.assertIsNone(report['net_eur'])
        self.assertEqual(trades, [])
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]['outcome'], 'ENTERED')

    def test_diagnostics_cannot_be_reported_as_portfolio(self):
        mk = market(4)
        mk.present[602] = False
        report, trades, _ = run_period(context(mk), P, CANDIDATE, C, ORIGIN, mk.end_ms, independent_days=True)
        self.assertEqual(report['unknown_days'], 1)
        self.assertEqual(report['closed_trades'], 3)
        self.assertIsNone(report['portfolio_net_eur'])

    def test_missing_first_return_halts_instead_of_selecting_next_touch(self):
        mk = market(2)
        for side in ('mid', 'bid', 'ask'):
            for name in ('open', 'high', 'low', 'close'):
                mk.px[f'{side}_{name}'][600] += 0.001
        mk.present[601] = False
        report, trades, _ = run_period(context(mk), P, CANDIDATE, C, ORIGIN, mk.end_ms)
        self.assertEqual(report['halt']['reason'], 'MISSING_M1_MAY_HIDE_ENTRY')
        self.assertEqual(trades, [])

    def test_time_exit_does_not_read_deadline_high_low(self):
        mk, setup = market(), pending()
        entry_check(mk, 601, setup, P, CANDIDATE, 100000)
        before = X.structural_path(mk, 601, 1, setup.stop, setup.target, P)
        for side in ('bid', 'ask', 'mid'):
            mk.px[side + '_high'][721] = 99
            mk.px[side + '_low'][721] = 0.01
        after = X.structural_path(mk, 601, 1, setup.stop, setup.target, P)
        self.assertEqual(before['reason'], 'TIME')
        self.assertEqual(before['net_unit'], after['net_unit'])

    def test_paris_daylight_saving_is_not_fixed_utc_offset(self):
        winter = int(pd.Timestamp('2021-01-04T14:45:00Z').value // 1_000_000)
        summer = int(pd.Timestamp('2021-07-05T13:45:00Z').value // 1_000_000)
        self.assertFalse(allowed_time(winter, C))
        self.assertFalse(allowed_time(summer, C))
        self.assertTrue(allowed_time(winter - 60 * D.MIN_MS, C))


class SelectionTests(unittest.TestCase):
    def sample(self):
        return {'development': {'profit_factor': 1.5, 'gross_profit_eur': 1500,
                'gross_loss_eur': 1000, 'halt': None, 'closed_trades': 30,
                'net_eur': 500, 'closed_drawdown_eur': 500},
                'final_2021_check': {'net_eur': 100000}}

    def test_future_check_returns_cannot_choose_candidate(self):
        rows = {'A': self.sample(), 'B': self.sample()}
        self.assertEqual(select_development(rows, SPEC['selection']), 'A')
        rows['B']['final_2021_check']['net_eur'] = 999999999
        rows['A']['final_2021_check']['net_eur'] = -999999999
        self.assertEqual(select_development(rows, SPEC['selection']), 'A')

    def test_no_fallback_to_profitable_known_subset_after_halt(self):
        row = self.sample()
        row['development']['halt'] = {'reason': 'UNRESOLVED_EXECUTION'}
        self.assertIsNone(select_development({'A': row}, SPEC['selection']))
        row['development']['halt'] = None
        row['development']['closed_trades'] = 2
        self.assertIsNone(select_development({'A': row}, SPEC['selection']))

    def test_pickle_cannot_import_arbitrary_functions(self):
        import io
        # Loading a function reference is enough to test the whitelist, without executing it.
        with self.assertRaises(pickle.UnpicklingError):
            CacheReader(io.BytesIO(pickle.dumps(eval))).load()


if __name__ == '__main__':
    unittest.main()
