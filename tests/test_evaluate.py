import unittest
from unittest.mock import patch

from evaluate import audit, summarize, evaluate_product
from main import Draw, backtest


class EvaluationTests(unittest.TestCase):
    def test_target_filter_keeps_prior_history_and_excludes_future(self):
        draws=[Draw(i,(1,2,3,4,5,6)) for i in range(1,7)]
        with patch('main.simulate',return_value={'suggested_numbers':[1,2,3,4,5,6]}) as run:
            result=backtest(draws,'645',2,1,'simulate',10,42,[4,5])
        self.assertEqual([r['draw_code'] for r in result['rows']],[4,5])
        self.assertEqual([[d.code for d in call.args[0]] for call in run.call_args_list],[[3,2],[4,3]])
        self.assertEqual(result['hit_histogram'],{6:2})

    def test_simulation_backtest_no_future_leakage(self):
        draws=[Draw(i,(1,2,3,4,5),1) for i in range(1,5)]
        a=backtest(draws,'535',2,1,'simulate',10,123)
        b=backtest(draws+[Draw(5,(20,21,22,23,24),12)],'535',2,1,'simulate',10,123)
        self.assertEqual(a['rows'],b['rows'][:len(a['rows'])])

    def test_audit_flags_prelaunch_without_mutating_data(self):
        draws=[Draw(20170102,(1,2,3,4,5,6),7,'2017-01-02'),
               Draw(20170801,(1,2,3,4,5,6),7,'2017-08-01')]
        result=audit(draws,'655')
        self.assertEqual(result['excluded_codes'],[20170102])
        self.assertEqual(len(draws),2)

    def test_seed_summary_and_bonus(self):
        runs=[{'rows':[{'hits':2,'baseline_hits':1,'bonus_hit':1,'baseline_bonus_hit':0}]}]
        result=summarize(runs,'535')
        self.assertEqual(result['mean_difference'],1)
        self.assertEqual(result['bonus_match_rate'],1)
        self.assertAlmostEqual(result['uniform_expected_main_hits'],25/35)

    def test_invalid_backtest_options(self):
        for kwargs in [{'window':-1},{'min_history':0},{'strategy':'other'},{'samples':0}]:
            with self.assertRaises(ValueError):
                backtest([],'645',**kwargs)

    def test_selection_precedes_holdout_and_keeps_same_date_together(self):
        import tempfile
        from pathlib import Path
        draws=[Draw(i,(1,2,3,4,5,6),date=f'2026-01-{(i-1)//2+1:02d}') for i in range(1,15)]
        calls=[]
        def fake_backtest(history,product,window,minimum,strategy,samples,seed,codes):
            calls.append((strategy,window,list(codes)))
            score=window if strategy=='simulate' else 0
            return {'rows':[{'hits':score,'baseline_hits':1,'bonus_hit':None,
                             'baseline_bonus_hit':None} for code in codes]}
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            source=directory/'645.csv'
            source.write_text('unchanged input')
            task=('645',directory,directory,[1,2],[0,42],4,3,5,5)
            with patch('evaluate.load',return_value=draws), patch('evaluate.backtest',side_effect=fake_backtest):
                result=evaluate_product(task)
            self.assertEqual(result['selected'],{'strategy':'simulate','window':2})
            development=result['protocol']['development_codes']
            holdout=result['protocol']['holdout_codes']
            self.assertEqual(holdout,[11,12,13,14])
            self.assertTrue(max(development)<min(holdout))
            self.assertTrue(all(codes==development for _,_,codes in calls[:-2]))
            self.assertTrue(all(codes==holdout for _,_,codes in calls[-2:]))
            self.assertEqual(source.read_text(),'unchanged input')
