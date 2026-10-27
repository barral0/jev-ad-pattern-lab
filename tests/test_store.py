"""All records here are SYNTHETIC, never live capture."""
import unittest, tempfile
from pathlib import Path

class StoreTests(unittest.TestCase):
    def test_import_persists_ads_and_groups_without_conflating_media(self):
        from labcore import Store, Ad
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d))
            s.put_ads([Ad(ad_id='1',page_id='9',copy=' Same  copy ',media_ids=['x']), Ad(ad_id='2',page_id='9',copy='same copy',media_ids=['x']), Ad(ad_id='3',page_id='9',copy='same copy',media_ids=['y'])])
            rows=s.ads()
            self.assertEqual(len(rows),3)
            self.assertEqual(rows[0]['group_ad_ids'],['1','2'])
            self.assertNotEqual(rows[0]['fingerprint'],rows[2]['fingerprint'])
            self.assertEqual(len(Store(Path(d)).ads()),3)

if __name__=='__main__': unittest.main()
