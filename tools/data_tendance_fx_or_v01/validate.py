"""Full structural validation of delivered price and missing-minute CSVs only."""
import csv
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from collect import START, END, OUTPUT, HEADER, dump, sha

def check():
    coverage=[]
    begin=START
    while begin<END:
        key=begin.strftime('%Y-%m')
        next_month=datetime(begin.year+1,1,1,tzinfo=timezone.utc) if begin.month==12 else datetime(begin.year,begin.month+1,1,tzinfo=timezone.utc)
        finish=min(next_month,END)
        observed=set();n_ticks=0
        file=OUTPUT/'xauusd_m1'/f'XAUUSD_M1_BID_ASK_{key}.csv'
        with file.open(newline='') as f:
            r=csv.reader(f);assert next(r)==HEADER,(key,'schema')
            previous=None
            for row in r:
                assert len(row)==10,(key,'column count')
                label=row[0];t=datetime.fromisoformat(label.replace('Z','+00:00'))
                assert begin<=t<finish and t.second==0 and t.microsecond==0,(key,'bounds')
                assert previous is None or label>previous,(key,'ordering/duplicate')
                previous=label;observed.add(label)
                x=[Decimal(v) for v in row[1:9]]
                assert all(v.is_finite() and v>0 for v in x),(key,'quote values')
                for side in (x[:4],x[4:]):
                    o,h,l,c=side
                    assert l<=o<=h and l<=c<=h,(key,'OHLC')
                n=int(row[9]);assert n>0 and str(n)==row[9],(key,'tick count')
                n_ticks+=n
        missing=set()
        with (OUTPUT/'minutes_manquantes'/f'MINUTES_MANQUANTES_{key}.csv').open(newline='') as f:
            r=csv.reader(f);assert next(r)==['utc_minute']
            previous=None
            for row in r:
                assert len(row)==1 and row[0] not in observed,(key,'overlap')
                label=row[0]
                assert previous is None or label>previous,(key,'gap ordering')
                previous=label;missing.add(label)
        t=begin;grid=set()
        while t<finish:
            grid.add(t.strftime('%Y-%m-%dT%H:%M:00Z'));t+=timedelta(minutes=1)
        assert observed|missing==grid,(key,'full UTC grid partition')
        coverage.append(dict(month=key,observed=len(observed),missing=len(missing),ticks=n_ticks))
        begin=finish
    assert len(coverage)==82
    ledger=json.loads((OUTPUT/'provenance/monthly_source_ledger.json').read_text())
    assert len(ledger)==83
    assert sum(x['ticks'] for x in coverage)==sum(x['included_ticks'] for x in ledger)
    result=dict(structural_checks='PASS',monthly_price_csvs=82,monthly_missing_csvs=82,
        source_archive_identities=83,monthly_checks=coverage,
        schema_and_utc_bounds=True,ordered_unique_minutes=True,positive_finite_quotes=True,
        ohlc_extremes_consistent=True,positive_tick_counts=True,
        price_plus_missing_exactly_partitions_requested_grid=True,tick_totals_reconcile=True,
        independent_dukascopy_validation='NOT_PERFORMED_SEE_CONTROLE_DUKASCOPY',
        returns_or_strategy_statistics_computed=False)
    dump(OUTPUT/'provenance/OUTPUT_VALIDATION.json',result)
    print('PASS: 82 monthly price CSVs, 82 missing-minute CSVs, schema/bounds/OHLC/tick and full-grid checks. Dukascopy validation remains separate.')

if __name__=='__main__':check()
