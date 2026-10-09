import copy
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from run_round import TIMEZONE, aggregate, run_round, run_once, top_combinations


class RoundTests(unittest.TestCase):
    def test_top_five_matches_exhaustive_scores_and_ties(self):
        from collections import Counter
        from itertools import combinations
        ranked=list(range(1,9));counts=Counter(dict(zip(ranked,[9,7,7,6,6,5,3,0])))
        expected=sorted(combinations(range(8),3),key=lambda indices:(-sum(counts[ranked[i]] for i in indices),indices))[:5]
        self.assertEqual(top_combinations(ranked,counts,3,5),[[ranked[i] for i in row] for row in expected])
        self.assertEqual(len({tuple(r) for r in top_combinations(ranked,counts,3,5)}),5)
        with self.assertRaises(ValueError): top_combinations([1,2],counts,2,2)

    def test_five_main_combinations_keep_bonus_separate(self):
        rows=self.fixture()
        for row in rows:
            row['product']='655';row['round_id']='655_1425_091026'
            row['suggestion']['numbers']=[1,2,3,4,5,6,15]
        result=aggregate(rows,'655_1425_091026',datetime(2026,10,9,14,25,tzinfo=TIMEZONE),recommendation_count=5)
        self.assertEqual(len(result['recommendations']),5)
        self.assertEqual(len({tuple(r['numbers'][:6]) for r in result['recommendations']}),5)
        self.assertTrue(all(r['numbers'][-1]==15 for r in result['recommendations']))

    def fixture(self, product='645'):
        numbers=[1,2,3,4,5,6] if product=='645' else [1,2,3,4,5,2]
        return [{'iteration':i,'round_id':f'{product}_1425_091026','product':product,
                 'source_sha256':'same','protocol':{'holdout_codes':[100],'seed_offsets':[i]},
                 'audit':{},'selected':{'strategy':'predict','window':30},
                 'suggestion':{'numbers':numbers,'latest_history_date':'2026-10-08'},
                 'holdout':{'summary':{'mean_main_hits':i/10,'mean_baseline_hits':0.8}}}
                for i in range(1,11)]

    def test_exactly_ten_and_no_duplicate_iterations(self):
        rows=self.fixture();stamp=datetime(2026,10,9,14,25,tzinfo=TIMEZONE)
        for invalid in [rows[:9],rows+[rows[0]],rows[:9]+[rows[0]]]:
            with self.assertRaises(ValueError): aggregate(invalid,'645_1425_091026',stamp)

    def test_consensus_is_independent_of_holdout_scores(self):
        rows=self.fixture();stamp=datetime(2026,10,9,14,25,tzinfo=TIMEZONE)
        a=aggregate(rows,'645_1425_091026',stamp)
        for row in rows: row['holdout']['summary']['mean_main_hits']=1000
        b=aggregate(rows,'645_1425_091026',stamp)
        self.assertEqual(a['recommendations'],b['recommendations'])
        self.assertEqual(a['recommendations'][0]['numbers'],[1,2,3,4,5,6])
        self.assertEqual(a['recommendations'][1]['numbers'],[1,2,3,4,5,7])

    def test_bonus_separate_and_mixed_sources_rejected(self):
        rows=self.fixture('535');stamp=datetime(2026,10,9,14,25,tzinfo=TIMEZONE)
        result=aggregate(rows,'535_1425_091026',stamp)
        self.assertEqual(result['recommendations'][0]['numbers'],[1,2,3,4,5,2])
        self.assertEqual(result['main_ranking'][1]['round_count'],10)
        rows[0]['source_sha256']='different'
        with self.assertRaises(ValueError): aggregate(rows,'535_1425_091026',stamp)

    def test_same_minute_does_not_overwrite_existing_round(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d);path=output/'645_1425_091026_1.json'
            path.write_text('keep')
            with self.assertRaises(FileExistsError):
                run_round(output_dir=output,started_at=datetime(2026,10,9,14,25,tzinfo=TIMEZONE))
            self.assertEqual(path.read_text(),'keep')

    def test_latest_recommendation_uses_selected_window_and_audit(self):
        import hashlib
        import json
        from main import Draw
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);source=directory/'645.csv';source.write_text('source')
            data={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                  'audit':{'excluded_codes':[1]},'selected':{'strategy':'predict','window':1}}
            draws=[Draw(3,(1,2,3,4,5,6),date='2026-10-09'),Draw(2,(1,2,3,4,5,6),date='2026-10-07')]
            task=('645',directory,directory,'645_1425_091026',1,42,10,2,2)
            with patch('run_round.evaluate_product',return_value=copy.deepcopy(data)),patch('run_round.load',return_value=draws),patch('run_round.predict',return_value=[{'numbers':[1,2,3,4,5,6]}]) as predict:
                run_once(task)
            self.assertEqual([d.code for d in predict.call_args.args[0]],[3])
            saved=json.loads((directory/'645_1425_091026_1.json').read_text())
            self.assertEqual(saved['iteration'],1)
            self.assertEqual(saved['suggestion']['history_draws'],1)
