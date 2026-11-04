"""Checks that causal observation preserves replay and reconciles refusals."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from focused_diagnostics import run_diagnosed
from test_research import C, CANDIDATE, ORIGIN, P, context, market
from backtest_bot.simulation import run_period


def audited_context(mk, extra_outside=False):
    ctx = context(mk)
    if extra_outside:
        for minute in (420, 990):
            event = copy.copy(ctx.bos[0])
            event.close_ms = ORIGIN + minute * 60000
            ctx.bos.append(event)
        ctx.bos.sort(key=lambda e: e.close_ms)
    for i, event in enumerate(ctx.bos):
        event.seq = i
        event.level_pid = f'P{i}'
        event.level_known_at_ms = event.close_ms - 240 * 60000
        event.level_price = 1.1997
        event.body = 0.002
        event.bias_state = 'BULL'
        event.caveats = []
    return ctx


class DiagnosticTests(unittest.TestCase):
    def test_observer_preserves_financial_replay_and_classifies_outside_bos(self):
        mk = market(4)
        ctx = audited_context(mk, extra_outside=True)
        expected = run_period(ctx, P, CANDIDATE, C, ORIGIN, mk.end_ms)
        actual, audit = run_diagnosed(ctx, P, CANDIDATE, C, ORIGIN, mk.end_ms)
        self.assertEqual(expected, actual)
        self.assertEqual(audit.reconciliation['audit_status'], 'PASS')
        self.assertEqual(audit.reconciliation['bos_rows'], 10)
        self.assertEqual(audit.reconciliation['bos_outcomes']['NOT_EVALUATED_OUTSIDE_UTC_SESSION'], 2)
        self.assertEqual(audit.reconciliation['setup_terminal_states']['ENTERED'], 4)

    def test_pending_setup_replacement_and_session_close_are_not_lost(self):
        mk = market()
        ctx = audited_context(mk)
        for event in ctx.bos:
            event.zone_lo, event.zone_hi, event.poi_bid_low = 1.18, 1.181, 1.179
        result, audit = run_diagnosed(ctx, P, CANDIDATE, C, ORIGIN, mk.end_ms)
        self.assertEqual(result[0]['closed_trades'], 0)
        self.assertEqual(audit.reconciliation['audit_status'], 'PASS')
        self.assertEqual(audit.reconciliation['setups_created'], 2)
        self.assertEqual(audit.reconciliation['setup_terminal_states'],
                         {'REPLACED_BY_NEW_BREAKOUT': 1, 'SESSION_CLOSE_NO_ENTRY': 1})

    def test_unresolved_execution_stays_unknown_in_diagnostics(self):
        mk = market(2)
        mk.present[602] = False
        result, audit = run_diagnosed(audited_context(mk), P, CANDIDATE, C, ORIGIN, mk.end_ms)
        self.assertIsNone(result[0]['net_eur'])
        self.assertEqual(result[0]['halt']['reason'], 'UNRESOLVED_EXECUTION')
        self.assertEqual(audit.reconciliation['audit_status'], 'PASS')
        self.assertTrue(audit.reconciliation['bos_outcomes']['NOT_EVALUATED_AFTER_BRANCH_HALT'])
        self.assertEqual(result[1], [])


if __name__ == '__main__':
    unittest.main()
