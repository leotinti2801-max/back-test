"""Reuse the frozen engine without mutating its module or duplicating its loop."""
from types import FunctionType
from simple_forex import runner as frozen


def parameters(reference, cfg, deadline_ms, stress):
    params = frozen.parameters(reference, cfg, deadline_ms, stress)
    minutes = cfg.get('research_max_holding_minutes', 1440)
    if minutes not in (60, 1440):
        raise ValueError('Unsupported holding limit')
    params['exit']['max_holding_minutes'] = minutes
    return params


# The code object, defaults and all accounting functions are identical. Only this
# clone's private globals replace parameters; frozen.runner remains untouched.
_simulate = FunctionType(frozen.simulate.__code__,
    {**frozen.simulate.__globals__, 'parameters': parameters},
    name='simulate_research', argdefs=frozen.simulate.__defaults__, closure=frozen.simulate.__closure__)
_simulate.__kwdefaults__ = dict(frozen.simulate.__kwdefaults__) if frozen.simulate.__kwdefaults__ else None


def simulate(*args, signal_source, **kwargs):
    if signal_source is None:
        raise ValueError('Explicit research signal required; no legacy V01 fallback')
    return _simulate(*args, signal_source=signal_source, **kwargs)
