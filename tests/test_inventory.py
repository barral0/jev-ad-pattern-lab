import unittest,tempfile
from pathlib import Path
from labcore import Store,Ad
class InventoryTests(unittest.TestCase):
    def test_complete_page_inventory_excludes_stale_ads_without_cross_page_loss(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d));s.put_ads([Ad(ad_id='1',page_id='9'),Ad(ad_id='2',page_id='9'),Ad(ad_id='3',page_id='8')])
            s.reconcile_inventory('9',['2'],complete=False)
            self.assertEqual(sum(r['active'] for r in s.ads()),3)
            s.reconcile_inventory('9',['2'],complete=True)
            self.assertEqual([r['ad_id'] for r in s.ads() if r['active']],['2','3'])
            s.reconcile_inventory('9',[],complete=True)
            self.assertEqual([r['ad_id'] for r in s.ads() if r['active']],['3'])
            from webapp import create_app
            from fastapi.testclient import TestClient
            state=TestClient(create_app(s),base_url='http://localhost:5194').get('/api/state').json()
            self.assertEqual([p['ad_id'] for p in state['landscape']['points']],['3'])
