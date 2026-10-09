import unittest
from unittest.mock import patch

from main import MASK64, PRODUCTS, simulate


class SimulationTests(unittest.TestCase):
    def test_counts_ties_bonus_and_seed_wrap(self):
        tickets = [[1,2,3,4,5,2], [1,2,3,4,6,1], [1,2,3,4,5,1]]
        with patch('main.predict', side_effect=[[{'numbers': t}] for t in tickets]) as run:
            result = simulate([], '535', MASK64, 3)
        self.assertEqual([call.args[2] for call in run.call_args_list], [MASK64,0,1])
        self.assertEqual(result['suggested_numbers'], [1,2,3,4,5,1])
        self.assertEqual(result['main_ranking'][0], {'number': 1, 'count': 3, 'sample_rate': 1})
        self.assertEqual(result['bonus_ranking'][0]['count'], 2)
        self.assertEqual(sum(r['count'] for r in result['main_ranking']), 15)
        self.assertEqual(sum(r['count'] for r in result['bonus_ranking']), 3)

    def test_duplicate_samples_are_counted(self):
        with patch('main.predict', return_value=[{'numbers': [1,2,3,4,5,6]}]):
            result = simulate([], '645', 42, 1000)
        self.assertEqual(result['samples'], 1000)
        self.assertEqual([r['count'] for r in result['main_ranking'][:6]], [1000]*6)
        self.assertEqual(result['bonus_ranking'], [])

    def test_real_sampler_reproducible_for_all_products(self):
        for product, (maximum, k, bonus_max) in PRODUCTS.items():
            result = simulate([], product, 42, 30)
            self.assertEqual(result, simulate([], product, 42, 30))
            self.assertEqual(len(result['main_ranking']), maximum)
            self.assertEqual(sum(r['count'] for r in result['main_ranking']), 30*k)
            self.assertEqual(sum(r['count'] for r in result['bonus_ranking']), 30 if bonus_max else 0)
            self.assertEqual(result['suggested_numbers'][:k], sorted(set(result['suggested_numbers'][:k])))

    def test_invalid_sample_count(self):
        for count in [0, -1, 1.5, True]:
            with self.assertRaises(ValueError):
                simulate([], '645', 42, count)
