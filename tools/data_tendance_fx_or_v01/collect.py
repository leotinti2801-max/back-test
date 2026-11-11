"""Acquire and prepare XAUUSD price data only; no strategy imports or results.

All network calls use inherited proxy/TLS settings. At most two HistData months
are fetched concurrently; each month uses its own sequential GET/POST session.
The user-requested clock correction is applied by the C++ aggregator using UTC
intervals generated with the standard Europe/Berlin timezone database.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import calendar
import csv
import hashlib
import http.cookiejar
import json
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

UTC = timezone.utc
START = datetime(2020, 1, 1, tzinfo=UTC)
END = datetime(2026, 10, 17, tzinfo=UTC)
HEADER = ['utc_minute', 'bid_open', 'bid_high', 'bid_low', 'bid_close',
          'ask_open', 'ask_high', 'ask_low', 'ask_close', 'n_ticks']
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'datasets/tendance_fx_or_v01'

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''): h.update(b)
    return h.hexdigest()

def months():
    y, m = 2019, 12
    while (y, m) <= (2026, 10):
        yield y, m
        y, m = (y+1, 1) if m == 12 else (y, m+1)

def dst_intervals():
    """Find transitions using zoneinfo, rather than a US/EST DST calendar."""
    tz = ZoneInfo('Europe/Berlin')
    intervals = []
    for y in range(2019, 2027):
        t = datetime(y, 1, 1, tzinfo=UTC)
        finish = datetime(y+1, 1, 1, tzinfo=UTC)
        start = None
        while t < finish:
            active = bool(t.astimezone(tz).dst())
            if active and start is None: start = t
            elif not active and start is not None:
                intervals.append((int(start.timestamp()*1000), int(t.timestamp()*1000)))
                start = None
            t += timedelta(hours=1)
    return intervals

def corrected_utc(label):
    u0 = label.replace(tzinfo=UTC) + timedelta(hours=5)
    return u0 - timedelta(hours=1 if u0.astimezone(ZoneInfo('Europe/Berlin')).dst() else 0)

class DownloadForm(HTMLParser):
    def __init__(self):
        super().__init__(); self.active = False; self.fields = {}
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'form': self.active = a.get('id') == 'file_down'
        if self.active and tag == 'input' and 'name' in a:
            self.fields[a['name']] = a.get('value', '')
    def handle_endtag(self, tag):
        if tag == 'form': self.active = False

def download(y, m, cache):
    p = cache / f'DAT_ASCII_XAUUSD_T_{y}{m:02}.zip'
    url = f'https://www.histdata.com/download-free-forex-historical-data/?/ascii/tick-data-quotes/xauusd/{y}/{m}'
    if p.exists() and zipfile.is_zipfile(p): return p, url, 'cached'
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    with op.open(url, timeout=40) as r: html = r.read().decode('utf-8')
    form = DownloadForm(); form.feed(html)
    expected = {'date': str(y), 'datemonth': f'{y}{m:02}', 'fxpair': 'XAUUSD', 'timeframe': 'T', 'platform': 'ASCII'}
    if not form.fields.get('tk') or any(form.fields.get(k) != v for k, v in expected.items()):
        raise ValueError(f'No matching official download form: {y}-{m:02}')
    time.sleep(1)
    req = urllib.request.Request('https://www.histdata.com/get.php',
        data=urllib.parse.urlencode(form.fields).encode(), headers={'Referer': url})
    tmp = p.with_suffix('.download')
    with op.open(req, timeout=180) as r, tmp.open('wb') as f:
        shutil.copyfileobj(r, f, 1024*1024)
    if not zipfile.is_zipfile(tmp):
        raise ValueError(f'Non-ZIP download: {tmp.read_bytes()[:100]!r}')
    tmp.replace(p)
    return p, url, datetime.now(UTC).isoformat()

def prepare_one(y, m, cache, exe, dst_file):
    key = f'{y}-{m:02}'
    part = cache / f'{key}.parts.csv'
    meta = cache / f'{key}.json'
    if part.exists() and meta.exists(): return json.loads(meta.read_text())
    archive, url, fetched = download(y, m, cache)
    stats = cache / f'{key}.stats.json'
    tmp = part.with_suffix('.tmp')
    with zipfile.ZipFile(archive) as z:
        name = f'DAT_ASCII_XAUUSD_T_{y}{m:02}.csv'
        if name not in z.namelist(): raise ValueError(f'Missing expected source CSV: {name}')
        info = z.getinfo(name)
        h = hashlib.sha256()
        with z.open(name) as raw, tmp.open('wb') as out:
            proc = subprocess.Popen([str(exe), 'ticks', str(int(START.timestamp()*1000)),
                str(int(END.timestamp()*1000)), str(dst_file), str(stats)], stdin=subprocess.PIPE, stdout=out)
            try:
                while True:
                    b = raw.read(4*1024*1024)
                    if not b: break
                    h.update(b); proc.stdin.write(b)
                proc.stdin.close()
            except BaseException:
                proc.kill(); proc.wait(); raise
            if proc.wait(): raise ValueError(f'Aggregation failed: {key}')
        record = dict(source_month=key, source_page=url,
            download_url='https://www.histdata.com/get.php', fetched_at_utc=fetched,
            source_archive=archive.name, zip_bytes=archive.stat().st_size,
            zip_sha256=sha(archive), source_csv=name, source_csv_bytes=info.file_size,
            source_csv_sha256=h.hexdigest(), source_csv_crc32=f'{info.CRC:08x}',
            parts_sha256=sha(tmp), **json.loads(stats.read_text()))
    tmp.replace(part); dump(meta, record)
    return record

def finalize(cache, exe, ledger):
    p = OUTPUT / 'provenance'; p.mkdir(parents=True, exist_ok=True)
    dump(p / 'monthly_source_ledger.json', ledger)
    merged = cache / 'merged.csv'
    with merged.open('wb') as out:
        proc = subprocess.Popen([str(exe), 'merge'], stdin=subprocess.PIPE, stdout=out)
        try:
            for y,m in months():
                with (cache / f'{y}-{m:02}.parts.csv').open('rb') as f:
                    shutil.copyfileobj(f, proc.stdin, 1024*1024)
            proc.stdin.close()
        except BaseException:
            proc.kill(); proc.wait(); raise
        if proc.wait(): raise ValueError('Merge failed')
    prices = OUTPUT / 'xauusd_m1'; prices.mkdir(exist_ok=True)
    gaps = OUTPUT / 'minutes_manquantes'; gaps.mkdir(exist_ok=True)
    coverage = []
    start_min = int(START.timestamp()/60); end_min = int(END.timestamp()/60)
    with merged.open(newline='') as f:
        reader = csv.reader(f); row = next(reader, None)
        yy,mm = 2020,1
        total_ticks = total_rows = 0
        while (yy,mm) <= (2026,10):
            begin = datetime(yy,mm,1,tzinfo=UTC)
            next_month = datetime(yy+1,1,1,tzinfo=UTC) if mm==12 else datetime(yy,mm+1,1,tzinfo=UTC)
            finish = min(next_month,END)
            key=f'{yy}-{mm:02}'
            n=ticks=missing=0
            with (prices/f'XAUUSD_M1_BID_ASK_{key}.csv').open('w',newline='') as pf, (gaps/f'MINUTES_MANQUANTES_{key}.csv').open('w',newline='') as gf:
                pw=csv.writer(pf);gw=csv.writer(gf);pw.writerow(HEADER);gw.writerow(['utc_minute'])
                for minute in range(int(begin.timestamp()/60),int(finish.timestamp()/60)):
                    label=datetime.fromtimestamp(minute*60,UTC).strftime('%Y-%m-%dT%H:%M:00Z')
                    if row and int(row[0])==minute:
                        pw.writerow([label]+row[1:]);n+=1;ticks+=int(row[-1]);row=next(reader,None)
                    elif row and int(row[0])<minute: raise ValueError('Merged timestamps out of order')
                    else:gw.writerow([label]);missing+=1
            coverage.append(dict(month=key,expected_utc_minutes=int((finish-begin).total_seconds()/60),observed_minutes=n,missing_minutes=missing,n_ticks=ticks))
            total_ticks+=ticks;total_rows+=n
            yy,mm=(yy+1,1) if mm==12 else (yy,mm+1)
        if row:raise ValueError('Merged data outside requested period')
    if total_ticks!=sum(x['included_ticks'] for x in ledger):raise ValueError('Tick reconciliation failed')
    with (p/'monthly_coverage.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(coverage[0]));w.writeheader();w.writerows(coverage)
    dump(p/'DATA_VALIDATION.json',dict(
        start_inclusive=START.isoformat(),end_exclusive=END.isoformat(),
        source_archives=len(ledger),monthly_price_files=82,monthly_gap_files=82,
        observed_utc_minutes=total_rows,included_source_ticks=total_ticks,
        expected_grid_minutes=end_min-start_min,
        missing_utc_minutes=sum(x['missing_minutes'] for x in coverage),
        missing_grid_includes_weekends_holidays_and_unknown_absences=True,
        ticks_reconcile=True,invalid_source_rows=0,
        crossed_source_quotes=sum(x['source_crossed_quotes'] for x in ledger),
        backward_timestamp_transitions=sum(x['source_backward_timestamp_transitions'] for x in ledger),
        interpolation=False,synthetic_ask=False,data_only=True))

def main():
    a=argparse.ArgumentParser();a.add_argument('--cache',type=Path,required=True)
    a.add_argument('--limit',type=int);a.add_argument('--finalize-only',action='store_true')
    args=a.parse_args();cache=args.cache.resolve();cache.mkdir(parents=True,exist_ok=True)
    exe=cache/'aggregate';source=Path(__file__).with_name('aggregate.cpp')
    subprocess.run(['g++','-O3','-std=c++17',str(source),'-o',str(exe)],check=True)
    dst_file=cache/'dst_intervals.txt'
    dst_file.write_text(''.join(f'{s} {e}\n' for s,e in dst_intervals()))
    items=list(months())[:args.limit or 83]
    def worker(item):
        y,m=item
        if args.finalize_only:return json.loads((cache/f'{y}-{m:02}.json').read_text())
        errors=[]
        for attempt in range(3):
            try:
                record=prepare_one(y,m,cache,exe,dst_file)
                time.sleep(2)
                return record
            except urllib.error.HTTPError as e:
                errors.append(dict(at_utc=datetime.now(UTC).isoformat(),http_status=e.code,
                    url=e.url,response_body=e.read(1000).decode(errors='replace')))
                dump(cache/f'{y}-{m:02}.errors.json',errors)
                if e.code not in (500,502,503,504) or attempt==2:raise
                time.sleep(10*(attempt+1))
        raise RuntimeError('unreachable')
    ledger=[]
    pool=concurrent.futures.ThreadPoolExecutor(max_workers=2)
    try:
        for record in pool.map(worker,items):
            ledger.append(record)
            dump(OUTPUT/'provenance/ACQUISITION_STATE.json',dict(status='IN_PROGRESS',completed=len(ledger),last_month=record['source_month'],at_utc=datetime.now(UTC).isoformat()))
            print(f'{len(ledger)}/83 {record["source_month"]}: {record["source_rows"]} source ticks, {record["zip_bytes"]} ZIP bytes',flush=True)
    except Exception as e:
        pool.shutdown(wait=True,cancel_futures=True)
        dump(OUTPUT/'provenance/ACQUISITION_STATE.json',dict(status='INCOMPLETE',completed=len(ledger),error=str(e),at_utc=datetime.now(UTC).isoformat()))
        raise
    else:pool.shutdown(wait=True)
    if len(ledger)==83:
        finalize(cache,exe,ledger)
        dump(OUTPUT/'provenance/ACQUISITION_STATE.json',dict(status='ACQUISITION_COMPLETE',completed=83,at_utc=datetime.now(UTC).isoformat(),dukascopy_validation='SEE_SEPARATE_CONTROL_STATUS'))
        print('ACQUISITION_COMPLETE; independent Dukascopy validation is separate.',flush=True)

if __name__=='__main__':main()
