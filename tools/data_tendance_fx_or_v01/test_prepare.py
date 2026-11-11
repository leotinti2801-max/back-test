"""Synthetic price-preparation checks only; never imports strategy code."""
import csv
import io
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from collect import corrected_utc, dst_intervals

class PreparationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.exe=cls.root/'aggregate'
        subprocess.run(['g++','-O2','-std=c++17',str(Path(__file__).with_name('aggregate.cpp')),'-o',str(cls.exe)],check=True)
        cls.dst=cls.root/'dst.txt';cls.dst.write_text(''.join(f'{s} {e}\n' for s,e in dst_intervals()))
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def aggregate(self, text):
        stats=self.root/'stats.json'
        p=subprocess.run([str(self.exe),'ticks','1577836800000','1792195200000',str(self.dst),str(stats)],input=text,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return list(csv.reader(io.StringIO(p.stdout))),json.loads(stats.read_text())
    def test_requested_clock_in_winter_summer_and_us_eu_mismatch(self):
        expected={'2020-01-07 12:00':'2020-01-07T17:00:00+00:00',
          '2020-07-14 12:00':'2020-07-14T16:00:00+00:00',
          '2020-03-10 12:00':'2020-03-10T17:00:00+00:00',
          '2020-03-17 12:00':'2020-03-17T17:00:00+00:00',
          '2020-03-24 12:00':'2020-03-24T17:00:00+00:00',
          '2020-10-27 12:00':'2020-10-27T17:00:00+00:00'}
        for label,answer in expected.items():
            value=datetime.strptime(label,'%Y-%m-%d %H:%M')
            self.assertEqual(corrected_utc(value).isoformat(),answer)
            raw=value.strftime('%Y%m%d %H%M')+'00123,1500.000000,1501.000000,0\n'
            rows,_=self.aggregate(raw)
            self.assertEqual(int(rows[0][0])*60,int(datetime.fromisoformat(answer).timestamp()))
    def test_preserves_extremes_event_time_and_equal_tick_order(self):
        raw=('20200714 120030000,1500.100001,1500.200002,0\n'
             '20200714 120010000,1499.000003,1499.100004,0\n'
             '20200714 120030000,1501.000005,1501.100006,0\n')
        rows,stats=self.aggregate(raw)
        merged=subprocess.run([str(self.exe),'merge'],input=','.join(rows[0])+'\n',text=True,capture_output=True,check=True).stdout
        f=next(csv.reader(io.StringIO(merged)))
        self.assertEqual(f[1:5],['1499.000003','1501.000005','1499.000003','1501.000005'])
        self.assertEqual(f[5:9],['1499.100004','1501.100006','1499.100004','1501.100006'])
        self.assertEqual(f[9],'3');self.assertEqual(stats['source_backward_timestamp_transitions'],1)
    def test_left_boundary_uses_previous_source_month(self):
        rows,stats=self.aggregate('20191231 185959999,1500.0,1500.1,0\n20191231 190000000,1500.0,1500.1,0\n')
        self.assertEqual(stats['source_rows'],2);self.assertEqual(stats['included_ticks'],1)
        self.assertEqual(int(rows[0][0])*60,1577836800)
    def test_merge_retains_both_sides_and_counts(self):
        a,_=self.aggregate('20200714 120010000,1500.0,1501.0,0\n')
        b,_=self.aggregate('20200714 120020000,1502.0,1503.0,0\n')
        p=subprocess.run([str(self.exe),'merge'],input=','.join(a[0])+'\n'+','.join(b[0])+'\n',text=True,capture_output=True,check=True)
        f=next(csv.reader(io.StringIO(p.stdout)))
        self.assertEqual(f[1:5],['1500.00000','1502.00000','1500.00000','1502.00000'])
        self.assertEqual(f[5:9],['1501.00000','1503.00000','1501.00000','1503.00000'])
        self.assertEqual(f[9],'2')

if __name__=='__main__':unittest.main()
