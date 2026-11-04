"""Read-only local source audit; no market simulation, interpolation or cache write.

Run with PYTHONDONTWRITEBYTECODE=1. Pandas/numpy globals are explicitly allowed
only after exact input size/SHA and supplied evidence manifest verification.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import io
import json
import pickle
import pickletools
import platform
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REVIEW = Path('/workspace/backtest_review_20261103')
REFERENCE = REVIEW / 'verified_reference/Trading_bot/reference'
TARGET = pd.Timestamp('2021-04-01T11:40:00Z')
OLD = 'reference_data/EURUSD_M1_RAW_SPREAD.pkl'
ANNUAL = 'raw/EURUSD_M1_2021_WITH_202012_WARMUP.pkl'
EXPECTED = {
    OLD: (18033788, '0cad4b151c47e05376e170d0b78351229769e9e86816f60233080fabdf3251de'),
    ANNUAL: (48121320, '9ea1c28c1fc9145192eb4f1de2c19e5576b397b348d8db671026df4c715943b2'),
}
PROOF_SHA = 'd55dffa970fd82fd197a6b2bed373ea990108bd7ba146fd4325600e73018ff03'
ALLOWED = {
    ('pandas.core.frame', 'DataFrame'),
    ('pandas.core.internals.managers', 'BlockManager'),
    ('pandas._libs.internals', '_unpickle_block'),
    ('numpy._core.numeric', '_frombuffer'), ('numpy', 'dtype'),
    ('builtins', 'slice'), ('numpy', 'ndarray'),
    ('numpy._core.multiarray', '_reconstruct'),
    ('pandas.core.indexes.base', '_new_Index'), ('pandas.core.indexes.base', 'Index'),
    ('pandas.core.indexes.datetimes', '_new_DatetimeIndex'),
    ('pandas.core.indexes.datetimes', 'DatetimeIndex'),
    ('pandas._libs.arrays', '__pyx_unpickle_NDArrayBacked'),
    ('pandas.core.arrays.datetimes', 'DatetimeArray'),
    ('pandas.core.dtypes.dtypes', 'DatetimeTZDtype'),
    ('datetime', 'timezone'), ('datetime', 'timedelta'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(path):
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': sha(path.read_bytes())}


class RestrictedFrameReader(pickle.Unpickler):
    def __init__(self, source):
        super().__init__(source)
        self.observed_globals = set()

    def find_class(self, module, name):
        if (module, name) not in ALLOWED:
            raise pickle.UnpicklingError(f'Unexpected global: {module}.{name}')
        self.observed_globals.add((module, name))
        return getattr(importlib.import_module(module), name)

    def persistent_load(self, pid):
        raise pickle.UnpicklingError('Persistent IDs are prohibited')


def verified_bytes(path, size, digest):
    data = path.read_bytes()
    if len(data) != size or sha(data) != digest:
        raise ValueError(f'Input identity mismatch: {path}')
    return data


def read_frame(path, size, digest):
    data = verified_bytes(path, size, digest)
    counts = Counter(op.name for op, _, _ in pickletools.genops(data))
    prohibited = {'EXT1', 'EXT2', 'EXT4', 'PERSID', 'BINPERSID', 'INST', 'OBJ'}
    if prohibited.intersection(counts):
        raise pickle.UnpicklingError('Unexpected extension/persistent/legacy opcode')
    reader = RestrictedFrameReader(io.BytesIO(data))
    frame = reader.load()
    if type(frame) is not pd.DataFrame:
        raise TypeError('Expected an ordinary pandas DataFrame')
    idx = frame.index
    if (not isinstance(idx, pd.DatetimeIndex) or str(idx.tz) != 'UTC'
            or not idx.is_unique or not idx.is_monotonic_increasing
            or idx.unit != 'ns' or np.any(idx.asi8 % 60_000_000_000)):
        raise ValueError('Unexpected minute index')
    columns = [f'{side}_{field}' for side in ('bid', 'ask', 'mid')
               for field in ('open', 'high', 'low', 'close')]
    if list(frame.columns) != columns + ['first_ts', 'tick_count']:
        raise ValueError('Unexpected quote schema')
    prices = frame[columns].to_numpy(float)
    if not np.isfinite(prices).all() or not (prices > 0).all():
        raise ValueError('Invalid quote values')
    for side in ('bid', 'ask', 'mid'):
        lo, hi = frame[f'{side}_low'], frame[f'{side}_high']
        for field in ('open', 'close'):
            if not ((lo <= frame[f'{side}_{field}']) &
                    (frame[f'{side}_{field}'] <= hi)).all():
                raise ValueError('Inconsistent OHLC')
    for field in ('open', 'close'):
        if not ((frame[f'bid_{field}'] <= frame[f'mid_{field}']) &
                (frame[f'mid_{field}'] <= frame[f'ask_{field}'])).all():
            raise ValueError('Inconsistent bid/mid/ask')
    ms = idx.asi8 // 1_000_000
    first = frame['first_ts'].to_numpy(float)
    if (not np.isfinite(first).all() or not ((ms <= first) & (first < ms + 60000)).all()
            or not (frame['tick_count'] > 0).all()):
        raise ValueError('Invalid first-tick or tick-count field')
    window = frame.loc[TARGET - pd.Timedelta(minutes=2):TARGET + pd.Timedelta(minutes=2)]
    rows = [{'minute_utc': str(at), **{k: float(v) for k, v in row.items()}}
            for at, row in window.iterrows()]
    return frame, {
        **identity(path), 'schema_validated': True, 'rows': len(frame),
        'first_minute_utc': str(idx.min()), 'last_minute_utc': str(idx.max()),
        'columns': list(frame.columns), 'target_minute_present': TARGET in idx,
        'neighbouring_observed_rows': rows,
        'restricted_globals_observed': [list(pair) for pair in sorted(reader.observed_globals)],
        'pickle_opcode_counts': dict(sorted(counts.items())),
    }


def inspect_archives(roots):
    archives, direct_raw, errors = [], [], []
    for root in roots:
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            name = path.name.lower()
            if name in ('eurusd_202104.zip', 'archives_ticks_brutes_202012_2021.zip'):
                direct_raw.append(identity(path))
            if path.suffix.lower() != '.zip':
                continue
            try:
                with zipfile.ZipFile(path) as archive:
                    entries = archive.infolist()
                    raw = [{'path': i.filename, 'bytes': i.file_size}
                           for i in entries if any(s in i.filename.lower()
                           for s in ('eurusd_202104', 'archives_ticks_brutes', '.bi5'))]
                    quote = [{'path': i.filename, 'bytes': i.file_size}
                             for i in entries if i.filename.lower().endswith('.pkl')]
                    archives.append({**identity(path), 'entry_count': len(entries),
                                     'matching_raw_entries': raw, 'pickle_entries': quote})
            except (OSError, zipfile.BadZipFile) as exc:
                errors.append({'path': str(path), 'error': str(exc)})
    return {'roots_inspected': [str(r) for r in roots],
            'method': 'Recursive filenames and ZIP central directories; no extraction; no network',
            'archives': archives, 'direct_april_or_raw_bundle_files': direct_raw,
            'errors': errors,
            'limits': 'No assertion about inaccessible locations, remote Drive or other archive formats.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, default=HERE)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    if not output.is_relative_to(HERE):
        raise ValueError('Outputs must stay in this data_quality subtree')
    json_path, note_path = output / 'LOCAL_SOURCE_AUDIT.json', output / 'NOTE_FR.md'
    if json_path.exists() or note_path.exists():
        raise FileExistsError('Use a fresh output directory; preserve previous audits')

    proof_path = REFERENCE / 'PROOF_ENTRIES_SHA256.json'
    proof_data = verified_bytes(proof_path, 49032, PROOF_SHA)
    proof = {row['path']: row for row in json.loads(proof_data)['files']}
    top_path = REVIEW / 'MANIFEST_RESULTATS_SHA256.json'
    top = {r['path']: r for r in json.loads(top_path.read_text())['files']}
    proof_entry = top['verified_reference/Trading_bot/reference/PROOF_ENTRIES_SHA256.json']
    if proof_entry['sha256'] != PROOF_SHA or proof_entry['bytes'] != len(proof_data):
        raise ValueError('Supplied manifests disagree')
    evidence_paths = [
        'README_PREUVES.md', 'analysis/build_input_v02_quarantine.py',
        'protocol/DATA_AUDIT.json', 'protocol/RAW_ARCHIVE_DELIVERY_MANIFEST.json',
        'protocol/RAW_INPUTS_FROZEN.json', 'protocol/EXISTING_RAW_INPUTS.json',
        'analysis/BUILD_INPUT_V02_LOG.txt',
    ]
    evidence = []
    for name in [OLD, ANNUAL, *evidence_paths]:
        entry = proof[name]
        verified_bytes(REFERENCE / name, entry['bytes'], entry['sha256'])
        evidence.append({**identity(REFERENCE / name), 'supplied_manifest_match': True})
    frames, inputs = {}, {}
    for name, (size, digest) in EXPECTED.items():
        if (proof[name]['bytes'], proof[name]['sha256']) != (size, digest):
            raise ValueError('Manifest and pinned input identities disagree')
        frames[name], inputs[name] = read_frame(REFERENCE / name, size, digest)
    old, annual = frames[OLD], frames[ANNUAL]
    subset = annual.loc[old.index.min():old.index.max()]
    exact = subset.equals(old)
    local = REPO / 'data/EURUSD_M1_2021_WITH_202012_WARMUP.pkl'
    verified_bytes(local, *EXPECTED[ANNUAL])
    data_audit = json.loads((REFERENCE / 'protocol/DATA_AUDIT.json').read_text())
    raw_manifest = json.loads((REFERENCE / 'protocol/RAW_ARCHIVE_DELIVERY_MANIFEST.json').read_text())
    april = next(row for row in raw_manifest['files'] if row['path'] == 'EURUSD_202104.zip')
    april_audit = next(row for row in data_audit['month_audits'] if row['month_file'] == april['path'])
    drive = next(row for row in json.loads((REFERENCE / 'protocol/EXISTING_RAW_INPUTS.json').read_text())
                 if row['name'] == april['path'])
    archive_inspection = inspect_archives([Path('/workspace'), Path('/tmp')])
    result = {
        'audit_version': 'LOCAL_M1_SOURCE_CHECK_20261104_V01',
        'audit_type': 'Read-only data/provenance inspection; not a strategy simulation',
        'target_minute_utc': str(TARGET),
        'target_source_clock_under_recorded_fixed_EST_conversion': '2021-04-01 06:40:00 to 06:41:00 (UTC-05:00)',
        'runtime': {'python': platform.python_version(), 'pandas': pd.__version__, 'numpy': np.__version__},
        'script': identity(Path(__file__)),
        'provenance': {'top_manifest': identity(top_path), 'proof_manifest': identity(proof_path),
                       'evidence': evidence,
                       'limit': 'Hashes prove consistency with supplied local evidence, not provider authenticity or market completeness.'},
        'inputs': inputs, 'active_cache': identity(local),
        'old_cache_comparison': {
            'full_14_column_frame_and_index_exactly_equal_to_annual_subset': exact,
            'annual_subset_rows': len(subset), 'old_rows': len(old),
            'old_minutes_not_in_annual': len(old.index.difference(annual.index)),
            'independent_source': False if exact else None,
        },
        'recorded_raw_april': {'monthly_archive_identity': april,
                              'recorded_aggregation_audit_not_reexecuted': april_audit,
                              'recorded_drive_location_not_fetched': drive,
                              'declared_source_clock': data_audit['source_clock'],
                              'provider_full_tick_certification': data_audit['full_tick_certification']},
        'local_archive_inspection': archive_inspection,
        'conclusions': {
            'missing_m1_in_both_reviewed_caches': TARGET not in old.index and TARGET not in annual.index,
            'local_replacement_quote_found': False,
            'tick_archive_available_for_target_inspection': bool(archive_inspection['direct_april_or_raw_bundle_files'])
                or any(a['matching_raw_entries'] for a in archive_inspection['archives']),
            'absence_of_actual_market_quotes_proven': False,
            'collection_or_export_loss_proven': False,
            'active_path_remains_unresolved': True,
            'next_evidence_needed': 'Obtain exact EURUSD_202104.zip (or documented raw bundle), verify SHA and CSV SHA, inspect source-clock 2021-04-01 06:39-06:42 and provider gap report; independent same-convention data only under a separately declared source protocol.',
        },
        'actions': {'cache_modified': False, 'cache_merged': False, 'prices_interpolated': False,
                    'simulation_run': False, 'external_file_fetched': False},
    }
    note = f'''# Vérification locale de la minute manquante — 4 novembre 2026

La minute du **1er avril 2021 à 11:40 UTC** manque dans les deux caches vérifiés.
Le fichier antérieur contient {len(old):,} lignes du {old.index.min()} au {old.index.max()}.
Ses 14 colonnes et son index sont exactement identiques au sous-ensemble du cache annuel.
Ce contrôle a été reproduit ici : il ne repose pas uniquement sur l'ancien audit.
Il n'apporte donc aucune cotation supplémentaire pour résoudre l'exposition de London Range V01.

SHA256 antérieur : `{EXPECTED[OLD][1]}` ({EXPECTED[OLD][0]} octets).
SHA256 annuel et copie active : `{EXPECTED[ANNUAL][1]}` ({EXPECTED[ANNUAL][0]} octets).
Les identités correspondent au manifeste de preuves fourni. Le manifeste, les audits et
le script historique de préparation sont identifiés dans `LOCAL_SOURCE_AUDIT.json`.
Une concordance de SHA prouve la cohérence des pièces, pas leur authenticité fournisseur.
La lecture a employé une whitelist explicite des globals pandas/numpy/datetime ; aucun
`pickle.load` libre ni ancien script de préparation n'a été exécuté.

Les caches contiennent 11:39 puis 11:41, avec les mêmes valeurs dans les deux fichiers.
La première cotation enregistrée pour 11:41 est à 11:41:05.289 UTC. Le détail des quatre
barres observées de 11:38 à 11:42 est conservé dans le JSON. Une barre M1 n'identifie
pas la dernière cotation réelle de la minute précédente, ni le parcours entre deux barres.

L'inventaire récursif de `/workspace` et `/tmp` et les répertoires centraux de
{len(archive_inspection['archives'])} ZIP locaux n'ont pas fourni d'archive de ticks d'avril.
Le README des preuves annonce les ticks dans un paquet distinct
`ARCHIVES_TICKS_BRUTES_202012_2021.zip`, absent du périmètre local inspecté.
Le CSV de quarantaine d'octobre concerne une heure d'octobre : il ne couvre pas avril.
Les ZIP de livraison contiennent des caches ou résultats, sans ticks supplémentaires identifiés.

L'archive requise est `EURUSD_202104.zip`, {april['bytes']} octets,
SHA256 `{april['sha256']}` ; le CSV interne annoncé a le SHA256
`{april_audit['csv_sha256']}`. L'ancien inventaire indique sa présence sur Drive :
{drive['drive_url']}
Cette localisation est une indication documentaire ; aucun accès Drive n'a été effectué ici.
Le fuseau déclaré par la préparation est EST fixe UTC−5. Il faut donc examiner les
ticks source du 1er avril entre 06:39 et 06:42, notamment `[06:40,06:41)`.

Les audits enregistrent zéro ligne invalide supprimée et aucune interpolation, mais
sans l'archive, ces affirmations ne peuvent pas être revérifiées à cette minute.
**Absence locale du fichier brut** : démontrée dans le périmètre inspecté.
**Absence de cotation dans le fichier source** : non vérifiable sans ce fichier.
**Absence de cotation sur le marché ou perte lors de collecte/export** : non démontrée.
Même un fichier source sans ticks ne suffirait pas à prouver un marché sans cotations.
Il faut le fichier exact, son rapport de gaps et, si nécessaire, une source indépendante
avec conventions de prix et de temps documentées, sans raccord implicite de flux.

Le trou reste non résolu. Aucun prix n'a été rempli, aucune source mélangée,
aucun cache modifié et aucune simulation lancée. Le total annuel inconnu doit le rester.

Reproduction : depuis le dépôt, exécuter
`PYTHONDONTWRITEBYTECODE=1 python research/knowledge_cycle_20261104/data_quality/inspect_local_sources.py --output-directory research/knowledge_cycle_20261104/data_quality/reproduction_02`.
Choisir un répertoire de sortie neuf ; les audits existants ne sont pas écrasés.
L'inventaire reflétera les fichiers présents au moment de chaque reproduction.
'''
    output.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    note_path.write_text(note)
    print(json.dumps({'output': str(json_path), 'note': str(note_path),
                      'conclusions': result['conclusions']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
