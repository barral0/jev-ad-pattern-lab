import unittest, tempfile, asyncio
from pathlib import Path
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from labcore import Store, Ad
class HardeningTests(unittest.TestCase):
    def test_audience_candidates_are_whole_literal_clauses(self):
        from inference import audience_candidates
        self.assertIn('Calling all designers',audience_candidates('Calling all designers. Get your free resource!').values())
    def test_budget_multi_process_style_connections_never_overspend(self):
        from inference import Budget, RESERVE
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d))
            def reserve(_): return Budget(s,'shared',Decimal('.01')).reserve()
            with ThreadPoolExecutor(max_workers=8) as pool: ids=list(pool.map(reserve,range(20)))
            self.assertEqual(sum(i is not None for i in ids),3)
            self.assertEqual(Budget(s,'shared',Decimal('.01')).total(),3*RESERVE)
    def test_timeout_keeps_charge_and_caches_nothing(self):
        from inference import analyze, Budget, RESERVE
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d));s.put_ads([Ad(ad_id='s1',page_id='9')])
            async def timeout(body): raise TimeoutError('synthetic transport timeout')
            report=asyncio.run(analyze(s,api_key='SYNTHETIC',transport=timeout,images=False,run_id='test-run'))
            self.assertEqual(report['status'],'partial');self.assertEqual(report['analyzed_ads'],0)
            self.assertEqual(Budget(s,'test-run').total(),RESERVE)
    def test_run_id_cannot_escape_data_root(self):
        from inference import analyze
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): asyncio.run(analyze(Store(Path(d)),api_key='SYNTHETIC',run_id='../escape'))
    def test_invalid_ad_identifier_rejected(self):
        with self.assertRaises(ValueError): Ad(ad_id='../x',page_id='9')
