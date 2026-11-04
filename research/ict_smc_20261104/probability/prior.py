"""Past-closed-trade diagnostics only; this module never increases position risk."""
import math
from numbers import Integral, Real


MIN_PRIOR_TRADES_FOR_REVIEW = 100
WILSON_Z_95 = 1.959963984540054


class CalibrationUnavailableError(ValueError):
    """A caller assertion cannot establish an independently calibrated model."""


def _timestamp(value, name):
    if isinstance(value, bool) or not isinstance(value, (Integral, Real, str)):
        raise ValueError(f'{name} must be an integer epoch millisecond')
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'{name} must be an integer epoch millisecond') from exc
    if isinstance(value, Real) and (not math.isfinite(value) or value != number):
        raise ValueError(f'{name} must be an integer epoch millisecond')
    if isinstance(value, str) and value.strip() not in (str(number), '+' + str(number)):
        raise ValueError(f'{name} must be an integer epoch millisecond')
    return number


def wilson_interval(wins, total):
    """Nominal two-sided95% Wilson interval, descriptive under unknown dependence."""
    if (isinstance(wins, bool) or isinstance(total, bool)
            or not isinstance(wins, Integral) or not isinstance(total, Integral)
            or not 0 <= wins <= total):
        raise ValueError('Require integer0 <= wins <= total')
    if total == 0:
        return None, None
    p = wins / total
    z2 = WILSON_Z_95 ** 2
    denominator = 1 + z2 / total
    center = (p + z2 / (2 * total)) / denominator
    half = WILSON_Z_95 * math.sqrt(p * (1 - p) / total + z2 / (4 * total ** 2)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def summarize_prior(trades, entry_ms, independent_calibration_verified=False):
    """Read only outcomes whose model close is known before this entry action.

    ``closed_at_ms <= entry_ms`` follows the runner's close-before-new-entry
    event ordering. None close times represent open/unresolved positions and
    are excluded. Future net results are not even parsed. All supplied trades
    must belong to this one strategy/scenario, not pooled alternatives.
    """
    if independent_calibration_verified is not False:
        raise CalibrationUnavailableError(
            'No independent model/calibration artifact is implemented; a flag cannot authorize larger lots')
    cutoff = _timestamp(entry_ms, 'entry_ms')
    pnl = []
    for trade in trades:
        close = trade.get('closed_at_ms')
        if close in (None, ''):
            continue
        if _timestamp(close, 'closed_at_ms') > cutoff:
            continue
        try:
            net = float(trade['net_eur'])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError('A prior closed trade requires finite net_eur') from exc
        if not math.isfinite(net):
            raise ValueError('A prior closed trade requires finite net_eur')
        pnl.append(net)
    total = len(pnl)
    wins = sum(net > 0 for net in pnl)
    losses = sum(net < 0 for net in pnl)
    breakevens = total - wins - losses
    low, high = wilson_interval(wins, total)
    return {
        'entry_ms': cutoff,
        'cutoff_policy': 'model_closed_at_ms <= entry_ms; close processed before new entry',
        'prior_n': total,
        'prior_wins': wins,
        'prior_losses': losses,
        'prior_breakevens': breakevens,
        'empirical_win_fraction': wins / total if total else None,
        'laplace_win_probability_diagnostic': (wins + 1) / (total + 2),
        'wilson95_lower_descriptive': low,
        'wilson95_upper_descriptive': high,
        'observed_mean_net_eur': math.fsum(pnl) / total if total else None,
        'minimum_prior_trades_for_review': MIN_PRIOR_TRADES_FOR_REVIEW,
        'minimum_prior_trades_met': total >= MIN_PRIOR_TRADES_FOR_REVIEW,
        'independent_calibration_verified': False,
        'probability_tradeable': False,
        'risk_multiplier': 1.0,
        'risk_policy': 'Fixed125EUR budget; caller retains500EUR planned daily cap',
        'adaptive_sizing_reason': 'No independently calibrated probability model supplied',
        'confidence_interval_is_descriptive_only': True,
        'uncertainty_note': 'Serial dependence, selection and already-viewed development data are not covered by nominal binomial Wilson coverage',
    }
