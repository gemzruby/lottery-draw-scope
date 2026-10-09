import runpy
import unittest
from pathlib import Path

CRAWLER = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'crawl.py'))


class CrawlerTests(unittest.TestCase):
    def test_api_html_fields(self):
        row = CRAWLER['parse_row']('14/08<br>(Thứ sáu)<br>26',
                                   '07,&nbsp;09,&nbsp;13,&nbsp;31,&nbsp;35,&nbsp;44')
        self.assertEqual(row, {'draw_code': 20260814, 'draw_date': '2026-08-14',
                               'numbers': '7 9 13 31 35 44', 'bonus': ''})

    def test_overlap_and_conflict(self):
        row = CRAWLER['parse_row']('14/08<br>26', '7,9,13,31,35,44')
        accumulated = {}
        CRAWLER['append_rows'](accumulated, [row, row.copy()])
        self.assertEqual(len(accumulated), 1)
        with self.assertRaises(ValueError):
            CRAWLER['append_rows'](accumulated, [dict(row, numbers='1 2 3 4 5 6')])

    def test_invalid_numbers(self):
        for numbers in ['1,1,2,3,4,5', '1,2,3,4,5,46', '1,2,3']:
            with self.assertRaises(ValueError):
                CRAWLER['parse_row']('14/08<br>26', numbers)


class IncrementalTests(unittest.TestCase):
    @staticmethod
    def payload(*records):
        import json
        return json.dumps({'lotto': [dict(date=date+'<br>26', dex=str(index),
                                        num='1,2,3,4,5,6', sp=bonus)
                                   for date, index, bonus in records]})

    def test_655_bonus(self):
        row = CRAWLER['parse_row']('15/08<br>26', '16,20,25,27,30,50', '655', '02')
        self.assertEqual(row['bonus'], '2')

    def test_discovery_append_and_noop(self):
        import tempfile
        from unittest.mock import patch
        import crawl
        discovery = self.payload(('09/10', 31, ''), ('07/10', 30, ''))
        batch = self.payload(('07/10', 30, ''))
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            path = directory / '645.csv'
            original = b'draw_code,draw_date,numbers,bonus\n20261007,2026-10-07,1 2 3 4 5 6,\n'
            path.write_bytes(original)
            with patch('crawl.fetch', side_effect=[discovery, batch]) as fetch:
                self.assertEqual(crawl.update_product('645', directory, delay=0), 1)
                self.assertIn('Lindex=100000', fetch.call_args_list[0].args[0])
                self.assertIn('Lindex=31&', fetch.call_args_list[1].args[0])
            updated = path.read_bytes()
            self.assertTrue(updated.startswith(original))
            self.assertIn(b'20261009', updated)  # Latest excluded by cursor query is retained.
            with patch('crawl.fetch', side_effect=[discovery, batch]):
                self.assertEqual(crawl.update_product('645', directory, delay=0), 0)
            self.assertEqual(path.read_bytes(), updated)

    def test_bootstrap_stop_and_conflict_preserves_csv(self):
        import tempfile
        from unittest.mock import patch
        import crawl
        discovery = self.payload(('09/10', 10, ''), ('07/10', 9, ''))
        batch = self.payload(('07/10', 9, ''), ('04/10', 8, ''))
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            with patch('crawl.fetch', side_effect=[discovery, batch]):
                self.assertEqual(crawl.update_product('645', directory, delay=0), 2)
            path = directory / '645.csv'
            original = path.read_bytes()
            self.assertNotIn(b'20261004', original)
            with patch('crawl.fetch', return_value=discovery.replace('1,2,3,4,5,6','2,3,4,5,6,7')):
                with self.assertRaises(ValueError):
                    crawl.update_product('645', directory, delay=0)
            self.assertEqual(path.read_bytes(), original)

    def test_long_gap(self):
        import tempfile
        from unittest.mock import patch
        import crawl
        responses = [self.payload(('09/10',31,'')),
                     self.payload(('07/10',30,''),('04/10',29,'')),
                     self.payload(('02/10',28,''))]
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            path = directory / '645.csv'
            original = b'draw_code,draw_date,numbers,bonus\n20261002,2026-10-02,1 2 3 4 5 6,\n'
            path.write_bytes(original)
            with patch('crawl.fetch', side_effect=responses) as fetch:
                self.assertEqual(crawl.update_product('645', directory, delay=0), 3)
                self.assertEqual(fetch.call_count, 3)
                self.assertIn('Lindex=29&',fetch.call_args.args[0])
            self.assertTrue(path.read_bytes().startswith(original))

    def test_invalid_cursor(self):
        from unittest.mock import patch
        import crawl
        for payload in [self.payload(), self.payload(('09/10',100000,'')),
                        self.payload(('09/10',20,''),('07/10',21,''))]:
            with patch('crawl.fetch', return_value=payload):
                with self.assertRaises(ValueError):
                    crawl.fetch_records('645',100000)

    def test_535_two_draws_same_day_incremental(self):
        import tempfile
        import json
        from unittest.mock import patch
        import crawl
        from main import load, predict
        def record(code):
            return dict(date=f'{code:05d}<br>08/10<br>(Thứ năm)<br>26',
                        dex=str(code), num='1,6,20,22,25', sp='04')
        def payload(*codes):
            return json.dumps({'lotto': [record(code) for code in codes]})
        first = crawl.parse_row(record(933)['date'], record(933)['num'], '535', '04')
        second = crawl.parse_row(record(934)['date'], record(934)['num'], '535', '04')
        self.assertEqual(first['draw_date'], second['draw_date'])
        self.assertEqual(second['draw_code'], 934)
        accumulated = {}
        crawl.append_rows(accumulated, [first, second])
        self.assertEqual(len(accumulated), 2)
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            path = directory / '535.csv'
            original = b'draw_code,draw_date,numbers,bonus\n932,2026-10-08,1 6 20 22 25,4\n933,2026-10-08,1 6 20 22 25,4\n'
            path.write_bytes(original)
            with patch('crawl.fetch', side_effect=[payload(934,933), payload(933,932)]):
                self.assertEqual(crawl.update_product('535', directory, delay=0), 1)
            updated = path.read_bytes()
            self.assertTrue(updated.startswith(original))
            draws = load(str(path), '535')
            self.assertEqual([draw.code for draw in draws], [934,933,932])
            self.assertEqual(len(predict(draws,'535',42)[0]['numbers']), 6)
            with patch('crawl.fetch', side_effect=[payload(934,933), payload(933,932)]):
                self.assertEqual(crawl.update_product('535', directory, delay=0), 0)
            self.assertEqual(updated, path.read_bytes())

    def test_535_invalid_main_and_bonus(self):
        import crawl
        for numbers, bonus in [('1,2,3,4,36','4'), ('1,2,3,4,5,6','4'),
                               ('1,2,3,4,5','13'), ('1,2,3,4,5','')]:
            with self.assertRaises(ValueError):
                crawl.parse_row('00934<br>08/10<br>26', numbers, '535', bonus)
