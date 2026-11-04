"""One research filter; the original range crossing/rearming stays price-driven."""
from simple_forex.strategy_rearmed import signals as range_signals
from features import finite


def filtered_signals(features):
    def signals(market, day, tick=0.00001):
        events, session = range_signals(market, day, tick)
        for event in events:
            if event['reason'] != 'BREAKOUT':
                continue
            k = features.m5.slot_of_close(event['decision_ms'])
            fast, slow = features.values['ema20'][k], features.values['ema50'][k]
            event.update(unfiltered_reason='BREAKOUT', ema20=finite(fast), ema50=finite(slow))
            if fast != fast or slow != slow:
                event['reason'] = 'FILTER_UNKNOWN_EMA_WARMUP'
            elif event['direction'] * (fast - slow) <= 0:
                event['reason'] = 'FILTER_REFUSED_EMA_DIRECTION'
            if event['reason'] != 'BREAKOUT':
                event['account_checks_status'] = 'NOT_EVALUATED_AFTER_FILTER_REJECTION'
        return events, session
    return signals
