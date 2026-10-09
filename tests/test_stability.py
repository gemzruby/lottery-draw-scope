import copy
import csv
import json
import tempfile
import unittest
from concurrent.futures import Future
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from experiments.stability import compare_checkpoints, organize_legacy, write_stability_report
from main import ChaCha8, _chacha8_block
from run_round import TIMEZONE, aggregate, run_round
from tests import test_round


class ImmediatePool:
    def __init__(self, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def submit(self, function, *args):
        future=Future()
        try: future.set_result(function(*args))
        except Exception as error: future.set_exception(error)
        return future


class StabilityTests(unittest.TestCase):
    def test_custom_655_stages_and_five_reported_combinations(self):
        template=test_round.RoundTests().fixture()
        rows=[]
        for i in range(1,201):
            row=copy.deepcopy(template[(i-1)%10])
            row.update(iteration=i,product='655',round_id='655_1425_091026')
            row['suggestion']['numbers']=[1,2,3,4,5,6,15]
            rows.append(row)
        stamp=datetime(2026,10,9,14,25,tzinfo=TIMEZONE)
        snapshots=[aggregate(rows[:n],'655_1425_091026',stamp,n,recommendation_count=5) for n in [20,50,200]]
        comparison=compare_checkpoints(snapshots)
        self.assertEqual([r['runs'] for r in comparison['checkpoints']],[20,50,200])
        self.assertTrue(all(len(r['recommendations'])==5 for r in comparison['checkpoints']))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'report.md';write_stability_report(comparison,path)
            text=path.read_text()
            self.assertIn('20, 50, 200-run',text)
            self.assertIn('## Final consensus combinations',text)
            self.assertIn('| 5 |',text)
            self.assertIn('| 15 |',text)

    def checkpoints(self):
        rows=test_round.RoundTests().fixture()
        rows=[dict(copy.deepcopy(rows[(i-1)%10]),iteration=i) for i in range(1,101)]
        stamp=datetime(2026,10,9,14,25,tzinfo=TIMEZONE)
        return [aggregate(rows[:n],'645_1425_091026',stamp,n) for n in [10,30,100]]

    def test_nested_counts_and_distribution_metrics(self):
        result=compare_checkpoints(self.checkpoints())
        self.assertEqual([r['runs'] for r in result['checkpoints']],[10,30,100])
        for row in result['checkpoints'][1:]:
            self.assertEqual(row['change_from_previous']['retained_main_numbers'],6)
            self.assertAlmostEqual(row['change_from_previous']['main_distribution_total_variation'],0)
            self.assertAlmostEqual(sum(row['main_number_distribution'].values()),1)

    def test_non_nested_checkpoints_rejected(self):
        snapshots=self.checkpoints();snapshots[1]['runs'][0]['seed_offset']=999
        with self.assertRaises(ValueError): compare_checkpoints(snapshots)

    def test_cache_preserves_counter_key_and_unaliased_blocks(self):
        for seed in [0,42,(1<<64)-1]:
            rng=ChaCha8(seed)
            for _ in range(6):
                expected=list(_chacha8_block.__wrapped__(tuple(rng.key),rng.counter))
                self.assertEqual(rng.block(),expected)
        rng=ChaCha8(42);block=rng.block();block[0]=0
        self.assertNotEqual(ChaCha8(42).block()[0],0)
        self.assertEqual(_chacha8_block.cache_info().maxsize,16384)

    def test_migration_preserves_run_bytes_and_summary_references(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'suggestions').mkdir()
            snapshots=self.checkpoints();summary=snapshots[0]
            original=b'{"run": "preserved"}'
            for row in summary['runs']: (root/row['file']).write_bytes(original)
            path=root/'suggestions/645_1425_091026.json';path.write_text(json.dumps(summary))
            self.assertEqual(organize_legacy(root),10)
            self.assertFalse(list(root.glob('*.json')))
            moved=json.loads(path.read_text())
            for row in moved['runs']:
                self.assertTrue(row['file'].startswith('645/645_1425_091026/runs/'))
                self.assertEqual((root/row['file']).read_bytes(),original)
            self.assertEqual(organize_legacy(root),0)

    def test_round_checkpoint_and_resume_do_not_repeat_completed_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=root/'data';output=root/'backtests';data.mkdir()
            with (data/'645.csv').open('w',newline='') as f:
                writer=csv.writer(f);writer.writerow(['draw_code','draw_date','numbers','bonus'])
                for i in range(130):
                    day=datetime(2025,1,1)+timedelta(days=i)
                    writer.writerow([int(day.strftime('%Y%m%d')),day.date().isoformat(),'1 2 3 4 5 6',''])
            stamp=datetime(2026,10,9,14,25,tzinfo=TIMEZONE)
            with patch('run_round.ProcessPoolExecutor',ImmediatePool):
                summary=run_round('645',data,output,7,1,2,2,1,stamp,runs=3,checkpoints=[1,3])
            round_id=summary['round_id'];directory=output/'645'/round_id
            before={p:p.read_bytes() for p in (directory/'runs').glob('*.json')}
            self.assertEqual(len(before),3)
            self.assertTrue((directory/'checkpoints/1.json').exists())
            with patch('run_round.ProcessPoolExecutor',ImmediatePool),patch('run_round.run_once') as run:
                resumed=run_round('645',data,output,None,1,2,2,1,runs=3,checkpoints=[1,3],resume=round_id)
                run.assert_not_called()
            self.assertEqual(summary['recommendations'],resumed['recommendations'])
            self.assertTrue(all(p.read_bytes()==contents for p,contents in before.items()))
            manifest=json.loads((directory/'manifest.json').read_text())
            self.assertEqual(manifest['status'],'complete')
            self.assertFalse((directory/'.lock').exists())
            with self.assertRaises(ValueError):
                run_round('645',data,output,None,2,2,2,1,runs=3,checkpoints=[1,3],resume=round_id)
