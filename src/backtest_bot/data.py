"""Read only the identified cache; whitelist pickle globals and verify schema."""
import hashlib
import importlib
import io
import pickle
from pathlib import Path

from .reference import D

CACHE_SHA256 = '9ea1c28c1fc9145192eb4f1de2c19e5576b397b348d8db671026df4c715943b2'
ALLOWED = {
    ('pandas.core.frame', 'DataFrame'),
    ('pandas.core.internals.managers', 'BlockManager'),
    ('pandas._libs.internals', '_unpickle_block'),
    ('numpy._core.numeric', '_frombuffer'), ('numpy', 'dtype'),
    ('builtins', 'slice'), ('numpy', 'ndarray'),
    ('pandas.core.indexes.base', '_new_Index'), ('pandas.core.indexes.base', 'Index'),
    ('numpy._core.multiarray', '_reconstruct'),
    ('pandas.core.indexes.datetimes', '_new_DatetimeIndex'),
    ('pandas.core.indexes.datetimes', 'DatetimeIndex'),
    ('pandas._libs.arrays', '__pyx_unpickle_NDArrayBacked'),
    ('pandas.core.arrays.datetimes', 'DatetimeArray'),
    ('pandas.core.dtypes.dtypes', 'DatetimeTZDtype'),
    ('datetime', 'timezone'), ('datetime', 'timedelta'),
}


class CacheReader(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) not in ALLOWED:
            raise pickle.UnpicklingError(f'Unexpected cache global: {module}.{name}')
        return getattr(importlib.import_module(module), name)

    def persistent_load(self, pid):
        raise pickle.UnpicklingError('Persistent IDs are not accepted')


def load_cache(path):
    raw = Path(path).read_bytes()
    if len(raw) != 48_121_320 or hashlib.sha256(raw).hexdigest() != CACHE_SHA256:
        raise ValueError('The supplied cache differs from the reviewed 2021 evidence')
    frame = CacheReader(io.BytesIO(raw)).load()
    quality = D.validate_frame(frame)
    return frame, quality


def market_from_cache(path):
    frame, quality = load_cache(path)
    # The existing cache already excludes this repeated source-clock hour.
    import pandas as pd
    ms = lambda s: int(pd.Timestamp(s).value // 1_000_000)
    market = D.build_market(frame, ms('2020-12-01T00:00:00Z'), ms('2022-01-01T00:00:00Z'), quality=[{
        'start_ms': ms('2021-11-01T00:00:00Z'), 'end_ms': ms('2021-11-01T01:00:00Z'),
    }])
    return market, quality

