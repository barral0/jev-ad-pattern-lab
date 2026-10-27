"""The maps must explain themselves in plain Portuguese: what a dot is, what the number means, what the map is NOT,
and a live summary computed from the data. SYNTHETIC fixtures. Needs the app at 127.0.0.1:5194."""
import json, unittest, urllib.request
from playwright.sync_api import sync_playwright
try:
    import test_portuguese_ui as P          # unittest discover -s tests
except ImportError:
    from tests import test_portuguese_ui as P  # python -m unittest tests.test_map_explainer

BASE = 'http://127.0.0.1:5194'
CLUSTERS = [0, 0, 0, 1, 2]


def fixtures(stacked=False):
    ads, points = [], []
    for i, c in enumerate(CLUSTERS):
        ads.append(dict(P.AD, ad_id=f'M{i}', fingerprint=f'f{i}', start_date=f'2026-0{i + 1}-10', group_ad_ids=[f'M{i}']))
        x, y = (0.0, 0.0) if stacked and i < 3 else (i * .3, (i % 2) * .4)
        points.append({'fingerprint': f'f{i}', 'ad_id': f'M{i}', 'x': x, 'y': y, 'cluster': c, 'ad_count': 1})
    state = json.loads(json.dumps(P.STATE)); state['landscape'] = {'method': 'Método técnico sintético', 'points': points, 'clusters': 3}
    return ads, state


class MapExplainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: urllib.request.urlopen(BASE + '/api/state', timeout=1).close()
        except OSError: raise unittest.SkipTest('Run scripts/lab.py serve')
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def open(self, tab, width=1360, stacked=False):
        ads, state = fixtures(stacked)
        ctx = self.browser.new_context(viewport={'width': width, 'height': 900}, locale='pt-BR'); self.addCleanup(ctx.close)
        page = ctx.new_page(); page.set_default_timeout(4000)
        page.route('**/api/**', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(
            state if '/api/state' in r.request.url else {'csrf_token': 'x'} if 'bootstrap' in r.request.url else None if '/api/jobs' in r.request.url else
            {'ads': ads, 'total': len(ads), 'offset': 0, 'limit': 500, 'has_more': False} if '/api/ads?' in r.request.url else ads[0])))
        page.goto(BASE); page.wait_for_selector('.tab'); page.get_by_role('button', name=tab, exact=True).click(); page.wait_for_timeout(500)
        return page

    # ---- Mapa tab -------------------------------------------------------------------
    def test_map_tab_explains_what_it_is_in_plain_words(self):
        text = self.open('Mapa').locator('#map-help').inner_text().lower()
        for needle in ('o que é', 'bolinha', 'textos parecidos', 'número', 'grupo', 'não mostra', 'como usar'):
            self.assertIn(needle, text)

    def test_map_help_says_what_it_is_not(self):
        text = self.open('Mapa').locator('#map-help').inner_text().lower()
        self.assertIn('não mostra', text); self.assertIn('imagem', text); self.assertIn('desempenho', text)

    def test_map_summary_is_computed_from_the_data(self):
        text = self.open('Mapa').locator('#map-summary').inner_text()
        self.assertIn('3 grupos', text); self.assertIn('maior reúne 3 de 5 criativos', text); self.assertIn('60%', text)

    def test_identical_creatives_share_one_bubble_marked_with_count(self):
        page = self.open('Mapa', stacked=True)
        self.assertEqual(page.locator('.plot .point').count(), 3, '3 stacked creatives -> 1 bubble, plus 2 others')
        big = page.locator('.plot .point', has_text='×3')
        self.assertEqual(big.count(), 1)
        self.assertEqual(page.locator('.plot .point', has_text='×').count(), 1, 'single creatives carry no count')
        self.assertIn('3 criativos', big.get_attribute('title'))
        size = big.evaluate('e=>e.getBoundingClientRect().width'); small = page.locator('.plot .point').last.evaluate('e=>e.getBoundingClientRect().width')
        self.assertGreater(size, small, 'bigger bubble for bigger group')

    def test_summary_still_counts_creatives_not_bubbles(self):
        self.assertIn('maior reúne 3 de 5 criativos', self.open('Mapa', stacked=True).locator('#map-summary').inner_text())

    def test_help_explains_the_times_n_marker(self):
        self.assertIn('×', self.open('Mapa').locator('#map-help').inner_text())

    def test_technical_details_are_tucked_away_not_deleted(self):
        page = self.open('Mapa')
        details = page.locator('#map-tech')
        self.assertEqual(details.count(), 1)
        self.assertFalse(details.evaluate('d=>d.open'), 'technical text starts collapsed')
        self.assertIn('Método técnico sintético', details.text_content())

    def test_map_help_is_short_and_readable(self):
        words = len(self.open('Mapa').locator('#map-help').inner_text().split())
        self.assertLess(words, 120, 'explanation must stay short')

    # ---- Replay map ---------------------------------------------------------------------
    def test_replay_has_a_plain_legend(self):
        text = self.open('Reprodução').locator('.rp-legend').inner_text().lower()
        for needle in ('cada ponto', 'textos parecidos', 'passe o mouse', 'grupo'):
            self.assertIn(needle, text)

    def test_no_overflow_on_mobile(self):
        for tab in ('Mapa', 'Reprodução'):
            page = self.open(tab, width=360)
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'), tab)


if __name__ == '__main__':
    unittest.main()
