"""Opt-in observation of the byte-identified V02 simulator, without changing rules.

Integration::

    from focused_diagnostics import run_diagnosed
    (summary, trades, decisions), audit = run_diagnosed(
        ctx, params, candidate, controls, start_ms, end_ms, scenario="base")
    audit.write_outputs(output_directory)

Only the exact source versions below are supported. Tracing observes actual
branches and setup changes; it never executes refused trades. M1 liquidation
envelopes are model outputs, not tick equity or a claim of FTMO compliance.
"""
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

from backtest_bot import simulation as S
from backtest_bot.reference import D, ROOT, X


EXPECTED = {
    'src/backtest_bot/simulation.py': 'e9bf7151d9cd7876af0c450126e1643b1488c49bc3ba2843bd94f704d59b9111',
    'src/backtest_bot/strategy.py': '3a1eea23ff1a8f67d0e4205320a06065ca9d1f64b1383ea899d26044982ef0ed',
    'vendor/h4m30_v01/h4m30_execution.py': '2f6e58e74f23af55616cbdbe1b0b1c3d70768742795aeae67fd95797aa3edb8e',
}


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, 'item'):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def json_file(path, value):
    path.write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csv_file(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row)) or ['no_rows']
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(clean(v), ensure_ascii=False) if isinstance(v, (dict, list, tuple))
                             else clean(v) for k, v in row.items()})


class FocusedAudit:
    def __init__(self, ctx, controls, start_ms, end_ms, scenario='base'):
        for name, expected in EXPECTED.items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
                raise RuntimeError(f'Diagnostic source mapping is unsupported: {name}')
        self.ctx, self.controls = ctx, controls
        self.start, self.end, self.scenario = int(start_ms), int(end_ms), scenario
        self.frames, self.lifecycle, self.events, self.envelopes, self.errors = {}, {}, [], [], []
        self.opportunities, self.bos_objects = {}, {}
        self.last_ledger = None
        self._finished = False
        for event in ctx.bos:
            if self.start <= event.close_ms < self.end:
                key = id(event)
                self.bos_objects[key] = event
                self.opportunities[key] = {
                    'bos_id': f'BOS_{event.seq}', 't_utc': D.iso(event.close_ms),
                    'direction': event.direction, 'level_pid': event.level_pid,
                    'level_known_at_utc': D.iso(event.level_known_at_ms),
                    'level_price': event.level_price, 'body': event.body,
                    'atr_reference': event.atr_ref, 'bias_state': event.bias_state,
                    'zone_lo': event.zone_lo, 'zone_hi': event.zone_hi,
                    'static_failures': list(event.static_reasons),
                    'caveats': list(event.caveats), 'dynamic_failures': [],
                    'engine_reached_bos_logic': False, 'engine_evaluated_static_checks': False,
                    'outcome': 'NOT_OBSERVED_YET', 'setup_id': None,
                }
        self.by_time = {}
        for key, event in self.bos_objects.items():
            self.by_time.setdefault(int(event.close_ms), []).append(key)

    def __enter__(self):
        if sys.gettrace() is not None:
            raise RuntimeError('A debugger/tracer is already installed; diagnostics will not replace it')
        sys.settrace(self._global_trace)
        return self

    def __exit__(self, exc_type, exc, tb):
        sys.settrace(None)
        self._finished = exc_type is None
        return False

    def _global_trace(self, frame, event, arg):
        if event != 'call':
            return None
        if frame.f_code is S.session.__code__:
            ledger = frame.f_locals['ledger']
            self.frames[id(frame)] = {
                'last_line': None, 'setup': None, 'created': [],
                'decisions': len(ledger.decisions), 'trades': len(ledger.trades),
            }
            return self._session_trace
        if frame.f_code is X.structural_path.__code__ and frame.f_back.f_code is S.session.__code__:
            return self._path_trace
        return None

    def _event(self, t, event, sid=None, **detail):
        self.events.append({'sequence': len(self.events), 't_utc': D.iso(t),
                            'event': event, 'setup_id': sid, **detail})

    def _finish_setup(self, sid, t, status, reasons=(), known=True):
        record = self.lifecycle[sid]
        if record['terminal_status'] is not None:
            self.errors.append(f'Duplicate terminal status for {sid}: {status}')
            return
        record.update(terminal_status=status, terminal_utc=D.iso(t),
                      terminal_reasons=list(reasons), market_state_known=known)
        self._event(t, 'SETUP_END', sid, status=status, reasons=list(reasons), market_state_known=known)

    def _setup_change(self, frame, state):
        local = frame.f_locals
        previous, current = state['setup'], local.get('setup')
        if previous is current:
            return
        t = int(local.get('t', local['day']))
        line = state['last_line']
        if previous is not None:
            sid = previous.setup_id
            if current is not None:
                self._finish_setup(sid, t, 'REPLACED_BY_NEW_BREAKOUT', [current.setup_id])
            elif line == 86:
                mk, i = local['mk'], local['i']
                self._event(t, 'FIRST_RETURN_CONSUMED', sid,
                            return_open_utc=D.iso(t - D.MIN_MS),
                            mid_low=float(mk.px['mid_low'][i]), mid_high=float(mk.px['mid_high'][i]),
                            mid_close=float(mk.px['mid_close'][i]),
                            zone_lo=previous.zone_lo, zone_hi=previous.zone_hi)
            elif line == 66:
                reasons = []
                if t >= previous.expiry_ms:
                    reasons.append('TTL_EXPIRED')
                if local['state'] != ('BULL' if previous.direction == 1 else 'BEAR'):
                    reasons.append('H4_STATE_' + local['state'])
                self._finish_setup(sid, t, 'EXPIRED_OR_BIAS_CHANGED', reasons)
            elif line == 77:
                self._finish_setup(sid, t, 'CANCELLED_MISSING_M1_OUTSIDE_ENTRY_WINDOW',
                                   ['FIRST_RETURN_NOT_OBSERVABLE'], known=False)
            elif line == 84:
                self._finish_setup(sid, t, 'TARGET_REVISITED_BEFORE_ENTRY')
            elif line == 139:
                self._finish_setup(sid, t, 'ZONE_INVALIDATED')
            elif line == 52:
                self._finish_setup(sid, t, 'CANCELLED_PAUSE_STARTED')
            else:
                self.errors.append(f'Unclassified setup removal line {line}: {sid}')
                self._finish_setup(sid, t, 'UNCLASSIFIED_REMOVAL', [str(line)], known=False)
        if current is not None:
            sid = current.setup_id
            if sid in self.lifecycle:
                self.errors.append(f'Duplicate setup creation: {sid}')
            else:
                event = local.get('event')
                self.lifecycle[sid] = {
                    'setup_id': sid, 'created_utc': D.iso(current.created_ms),
                    'direction': current.direction, 'zone_lo': current.zone_lo, 'zone_hi': current.zone_hi,
                    'stop': current.stop, 'atr': current.atr, 'expiry_utc': D.iso(current.expiry_ms),
                    'bos_id': f'BOS_{event.seq}' if event is not None else None,
                    'terminal_status': None, 'terminal_utc': None,
                    'terminal_reasons': [], 'market_state_known': True,
                }
                state['created'].append(sid)
                self._event(t, 'SETUP_CREATED', sid)
        state['setup'] = current

    @staticmethod
    def _gate_reasons(local):
        reasons = []
        if local.get('position') is not None:
            reasons.append('POSITION_OPEN')
        if local.get('entered', False):
            reasons.append('DAILY_ENTRY_LIMIT_REACHED')
        if local['t'] == local.get('end'):
            reasons.append('SESSION_HARD_CLOSE')
        if local['t'] < local['ledger'].pause_end_ms:
            reasons.append('PAUSE_AFTER_TWO_LOSSES')
        return reasons

    def _session_trace(self, frame, event, arg):
        try:
            state = self.frames[id(frame)]
            local = frame.f_locals
            ledger = local['ledger']
            self.last_ledger = ledger
            if event in ('line', 'return'):
                self._setup_change(frame, state)
                t = int(local.get('t', local['day']))
                while state['decisions'] < len(ledger.decisions):
                    decision = ledger.decisions[state['decisions']]
                    state['decisions'] += 1
                    sid = decision['setup_id']
                    detail = dict(decision)
                    detail['entry_execution_checks_status'] = (
                        'EVALUATED_AT_OPEN' if 'entry_row_ms' in decision
                        else 'NOT_EVALUATED_AFTER_RETURN_OR_TIME_REFUSAL')
                    if 'OUTSIDE_ENTRY_WINDOW' in decision['reasons']:
                        minute = t % D.DAY_MS // D.MIN_MS
                        if not self.controls['entry_start_utc_minute'] <= minute < self.controls['entry_end_utc_minute']:
                            detail['specific_time_failures'] = ['OUTSIDE_UTC_ENTRY_WINDOW']
                        else:
                            detail['specific_time_failures'] = ['PARIS_EXCLUSION_WINDOW']
                    self.lifecycle[sid]['decision'] = detail
                    self._finish_setup(sid, t, 'ENTERED' if decision['outcome'] == 'ENTERED' else 'FIRST_RETURN_REFUSED',
                                       decision['reasons'])
                    self._event(t, 'ENTRY_DECISION', sid, decision=detail)
                while state['trades'] < len(ledger.trades):
                    trade = ledger.trades[state['trades']]
                    state['trades'] += 1
                    self._event(t, 'TRADE_CLOSED', trade['setup_id'], exit_reason=trade['exit_reason'],
                                net_eur=trade['net_eur'], balance_eur=trade['balance_after_eur'])
            if event == 'line':
                line = frame.f_lineno
                if line in (61, 132) and 't' in local:
                    reasons = self._gate_reasons(local)
                    for key in self.by_time.get(int(local['t']), ()):
                        row = self.opportunities[key]
                        row['dynamic_failures'] = reasons
                        row['outcome'] = 'IGNORED_DYNAMIC_GATE' if reasons else 'AWAITING_BOS_EVALUATION'
                if line in (143, 147, 150):
                    key = id(local.get('event'))
                    if key in self.opportunities:
                        row = self.opportunities[key]
                        row['engine_reached_bos_logic'] = True
                        row['engine_evaluated_static_checks'] = True
                        if line == 143:
                            row['outcome'] = 'REFUSED_STATIC_CONDITIONS'
                        elif line == 147:
                            row['outcome'] = 'NO_ADMISSIBLE_PREKNOWN_TARGET'
                        else:
                            row['outcome'] = 'SETUP_CREATED'
                            row['setup_id'] = local['setup'].setup_id
                state['last_line'] = line
            elif event == 'return':
                t = int(local.get('t', local['day']))
                for sid in state['created']:
                    if self.lifecycle[sid]['terminal_status'] is None:
                        if ledger.halt:
                            self._finish_setup(sid, t, 'HALTED_' + ledger.halt['reason'],
                                               [ledger.halt['reason']], known=not ledger.halt.get('uncertain', False))
                        else:
                            self._finish_setup(sid, int(local['end']), 'SESSION_CLOSE_NO_ENTRY')
                del self.frames[id(frame)]
        except Exception as exc:
            # An observation failure must not interrupt or alter financial replay.
            self.errors.append(f'Tracer error: {type(exc).__name__}: {exc}')
        return self._session_trace

    def _path_trace(self, frame, event, arg):
        if event == 'return' and isinstance(arg, dict) and 'net_unit' in arg:
            try:
                parent = frame.f_back.f_locals
                setup, qty = parent['current'], float(parent['qty'])
                balance = float(parent['ledger'].balance)
                for t, low, high, mark in zip(arg['t'], arg['worst'], arg['best'], arg['mark'], strict=True):
                    self.envelopes.append({
                        'setup_id': setup.setup_id, 't_utc': D.iso(t),
                        'equity_low_model_eur': balance + qty * low,
                        'equity_high_model_eur': balance + qty * high,
                        'equity_mark_model_eur': balance + qty * mark,
                        'balance_before_entry_eur': balance,
                    })
            except Exception as exc:
                self.errors.append(f'Path observation error: {type(exc).__name__}: {exc}')
        return self._path_trace

    def finalize(self, summary, trades, decisions):
        halt = summary.get('halt')
        for key, row in self.opportunities.items():
            if row['outcome'] not in ('NOT_OBSERVED_YET', 'AWAITING_BOS_EVALUATION'):
                continue
            t = int(self.bos_objects[key].close_ms)
            minute = t % D.DAY_MS // D.MIN_MS
            if halt and row['t_utc'] >= halt['at_utc']:
                row['outcome'] = 'NOT_EVALUATED_AFTER_BRANCH_HALT'
                row['dynamic_failures'] = [halt['reason']]
            elif not self.controls['entry_start_utc_minute'] <= minute <= self.controls['hard_exit_utc_minute']:
                row['outcome'] = 'NOT_EVALUATED_OUTSIDE_UTC_SESSION'
                row['dynamic_failures'] = ['OUTSIDE_UTC_SESSION']
            else:
                row['outcome'] = 'UNCLASSIFIED_NOT_EVALUATED'
                self.errors.append(f'Unclassified BOS: {row["bos_id"]}')
        terminal = Counter(row['terminal_status'] for row in self.lifecycle.values())
        if terminal.get(None):
            self.errors.append('Some created setups lack a terminal observation')
        if len(self.lifecycle) != summary['counts'].get('SETUP_CREATED', 0):
            self.errors.append('Setup creation count differs from simulator')
        entered = terminal.get('ENTERED', 0)
        if entered != len(trades) + int(bool(halt and halt['reason'] == 'UNRESOLVED_EXECUTION')):
            self.errors.append('Entered setup reconciliation differs from closed/unresolved positions')
        self.reconciliation = {
            'scenario': self.scenario, 'completed': self._finished,
            'audit_status': 'PASS' if self._finished and not self.errors else 'INCOMPLETE',
            'errors': self.errors, 'source_mapping_sha256': EXPECTED,
            'bos_rows': len(self.opportunities),
            'bos_outcomes': dict(Counter(row['outcome'] for row in self.opportunities.values())),
            'setups_created': len(self.lifecycle), 'setup_terminal_states': dict(terminal),
            'closed_trades': len(trades), 'entry_decisions': len(decisions),
            'minute_envelope_rows': len(self.envelopes),
            'no_counterfactual_refused_trade_execution': True,
            'known_scope_limit': 'BOS list includes only crossings certified by the existing context; incomplete bars may hide other opportunities.',
            'equity_warning': 'M1 liquidation model envelopes include prospective exit fees/slippage; not tick equity or a declaration of FTMO compliance.',
            'financial_summary_unchanged_by_observer': summary,
        }
        return self.reconciliation

    def write_outputs(self, directory):
        if not hasattr(self, 'reconciliation'):
            raise RuntimeError('Call finalize after replay')
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        prefix = self.scenario.upper()
        paths = {name: directory / f'{prefix}_{name}' for name in (
            'OPPORTUNITIES.csv', 'SETUPS.csv', 'SETUP_EVENTS.csv', 'EQUITY_ENVELOPES.csv',
            'BAR_COVERAGE.csv', 'DIAGNOSTIC_RECONCILIATION.json')}
        if any(path.exists() for path in paths.values()):
            raise ValueError('Diagnostic output already exists')
        csv_file(paths['OPPORTUNITIES.csv'], list(self.opportunities.values()))
        csv_file(paths['SETUPS.csv'], list(self.lifecycle.values()))
        csv_file(paths['SETUP_EVENTS.csv'], self.events)
        csv_file(paths['EQUITY_ENVELOPES.csv'], self.envelopes)
        bars = self.ctx.m30
        coverage = []
        for i in range(bars.n):
            close = bars.close_ms(i)
            if self.start <= bars.open_ms(i) and close <= self.end:
                complete = bool(bars.complete[i])
                coverage.append({'m30_open_utc': D.iso(bars.open_ms(i)),
                                 'm30_close_utc': D.iso(close), 'complete': complete,
                                 'm1_count': int(bars.m1_count[i]),
                                 'certified_bos_events': len(self.by_time.get(close, ())),
                                 'status': 'COMPLETE_BAR' if complete else 'INCOMPLETE_BAR_BOS_NOT_CERTIFIABLE'})
        csv_file(paths['BAR_COVERAGE.csv'], coverage)
        json_file(paths['DIAGNOSTIC_RECONCILIATION.json'], self.reconciliation)
        return list(paths.values())


def run_diagnosed(ctx, params, candidate, controls, start_ms, end_ms, scenario='base'):
    """Return the unchanged run_period tuple and a separate observer."""
    audit = FocusedAudit(ctx, controls, start_ms, end_ms, scenario)
    with audit:
        result = S.run_period(ctx, params, candidate, controls, start_ms, end_ms)
    audit.finalize(*result)
    return result, audit
