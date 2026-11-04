from pathlib import Path
from dataclasses import replace
import hashlib
import json
import subprocess
from backtest_bot.reference import ROOT

HERE = Path(__file__).resolve().parent
START = '2021-01-04T00:00:00Z'
CONTROL_END = '2021-04-01T00:00:00Z'
END = '2022-01-01T00:00:00Z'
SCENARIOS = ('S_CONT', 'S_PESS', 'S_OPT')


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def assert_scope():
    base = json.loads((HERE / 'PROVENANCE.json').read_text())['base_HEAD']
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    if branch != 'research/missing-minute-v01':
        raise RuntimeError('Required dedicated research branch')
    differences = subprocess.check_output(['git', 'diff', '--name-only', base, '--', '.',
        ':!research/missing_minute_20261104'], cwd=ROOT, text=True)
    if differences.strip():
        raise RuntimeError('Protected files changed outside allowed directory')


def configs():
    return {name: json.loads((ROOT / f'simple_forex/protocol_{version}.json').read_text())
            for name, version in [('V03', 'v03'), ('V04', 'v04')]}


def control_market(market, end_ms):
    n = market.idx(end_ms)
    return replace(market, end_ms=end_ms, n=n, present=market.present[:n].copy(),
        px={k: v[:n].copy() for k,v in market.px.items()}, first_ts=market.first_ts[:n].copy(),
        quality_minutes=market.quality_minutes[:n].copy(), closure_minutes=market.closure_minutes[:n].copy())
