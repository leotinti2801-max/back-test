"""Load the byte-preserved reference modules shipped with the user's evidence."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / 'vendor/h4m30_v01'
for name, expected in json.loads((VENDOR / 'ORIGIN_SHA256.json').read_text()).items():
    if hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() != expected:
        raise RuntimeError(f'Modified reference: {name}')
sys.path.insert(0, str(VENDOR))
import h4m30_data as D
import h4m30_bias as B
import h4m30_engine as E
import h4m30_execution as X
from integrity_guard import ExecutionPathUnknown

