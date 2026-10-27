import unittest, tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from labcore import Store, Ad
class ApiTests(unittest.TestCase):
    def test_empty_dashboard_and_security(self):
        from webapp import create_app
        with tempfile.TemporaryDirectory() as d:
            c=TestClient(create_app(Store(Path(d))),base_url='http://localhost:5194')
            state=c.get('/api/state').json()
            self.assertEqual(state['metrics']['total_ads'],0)
            self.assertEqual(c.get('/api/ads').json()['total'],0)
            self.assertIn('Nenhum anúncio coletado',c.get('/').text)
            self.assertNotIn('x-html',c.get('/').text)
            self.assertEqual(c.get('/api/state',headers={'host':'evil.example'}).status_code,400)
            self.assertEqual(c.get('/api/state',headers={'origin':'https://evil.example'}).status_code,403)
            self.assertEqual(c.post('/api/ads').status_code,405)
            self.assertEqual(c.get('/api/thumbnail/nope').status_code,404)
    def test_search_filters_inspector_and_secret_not_exposed(self):
        from webapp import create_app
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.put_ads([Ad(ad_id='1',page_id='9',copy='<script>SYNTHETIC needle</script>'),Ad(ad_id='2',page_id='8',copy='SYNTHETIC other')])
            c=TestClient(create_app(s),base_url='http://127.0.0.1:5194')
            data=c.get('/api/ads?q=needle&page_id=9').json()
            self.assertEqual(data['total'],1); self.assertEqual(data['ads'][0]['ad_id'],'1')
            self.assertEqual(c.get('/api/ads/1').json()['copy'],'<script>SYNTHETIC needle</script>')
            self.assertEqual(c.get('/api/ads/404').status_code,404)
            self.assertNotIn('TYPESAFE_API_KEY',c.get('/api/state').text)
