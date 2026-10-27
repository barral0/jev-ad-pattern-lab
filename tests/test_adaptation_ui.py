"""Interface adaptada (achados, 7 dimensões, quebra de copy). Respostas da API são SINTÉTICAS.
Requer o aplicativo servido em 127.0.0.1:5194 (scripts/lab.py serve); ignorado caso contrário."""
import json, unittest, urllib.request
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5194'
DIMS = ['format', 'hook', 'angle', 'offer', 'proof', 'objection', 'cta']
TITLES = {'format': 'Formato', 'hook': 'Gancho', 'angle': 'Ângulo', 'offer': 'Oferta', 'proof': 'Prova',
          'objection': 'Objeção', 'cta': 'Chamada para ação'}
CARD = {'category': 'talking_head', 'winner_proxy_rate': .83, 'ad_count': 6, 'unique_creatives': 6, 'share': 1,
        'median_days': 148, 'eligible_ads': 6, 'unknown_date_ads': 0, 'comparator': None, 'lift_pp': None,
        'relative_lift': None, 'evidence_ad_ids': ['SYNTHETIC1']}
FINDING = {'dimension': 'format', 'category': 'talking_head', 'label': 'Pessoa falando à câmera', 'n': 6, 'creatives': 6,
           'dated': 6, 'old': 5, 'share': 5 / 6, 'median_days': 148, 'baseline': 7 / 13, 'minimum_group_size': 5,
           'lift': 1.43, 'facets': [{'dimension': 'hook', 'category': 'curiosity', 'label': 'Curiosidade', 'n': 5, 'total': 5}],
           'comparison': {'category': 'graphic', 'label': 'Gráfico ou texto', 'n': 6, 'share': 1 / 6},
           'example_ids': ['SYNTHETIC1'], 'heading': 'Pessoa falando à câmera tem a maior fatia de anúncios com 60+ dias',
           'observation': '5 de 6 anúncios ativos com data neste grupo começaram há pelo menos 60 dias. Mediana de idade: 148 dias.',
           'next_test': 'Abra com um problema específico do negócio, ensine um passo aplicável.'}
OPTIONS = {d: [{'value': 'v_' + d, 'label': 'Rótulo ' + TITLES[d]}] for d in DIMS}
OPTIONS['format'] = [{'value': 'talking_head', 'label': 'Pessoa falando à câmera'}]
AD = {'ad_id': 'SYNTHETIC1', 'page_id': '9', 'page_name': 'SYNTHETIC', 'copy': 'Cansado? Organize tudo. Baixe o guia.',
      'group_ad_ids': ['SYNTHETIC1'], 'fingerprint': 'synthetic', 'days_active': 148, 'start_date': '2026-06-01',
      'end_date': None, 'thumbnail_src': None,
      'labels': {'needs_review': False, 'legacy': True, 'answers': {
          'hook': {'type': 'choice', 'choice': 'curiosity', 'confidence': .9, 'probabilities': {'curiosity': 1.0}},
          'cta': {'type': 'choice', 'choice': 'learn', 'confidence': .8, 'probabilities': {'learn': 1.0}}},
          'visual_callout': {'status': 'unavailable', 'text': None}},
      'copy_breakdown': {'source': 'Texto salvo do anúncio', 'text': 'x', 'sections': [
          {'role': 'Abertura', 'text': 'Cansado?'}, {'role': 'Corpo', 'text': 'Organize tudo.'},
          {'role': 'Fechamento / chamada', 'text': 'Baixe o guia.'}]},
      'label_names': {'hook': 'Curiosidade', 'cta': 'Saber mais'}, 'dimension_titles': TITLES}
STATE = {'metrics': {'total_ads': 6, 'unique_creatives': 6, 'analyzed_ads': 6, 'median_days': 148, 'winner_proxy_ads': 5,
                     'unknown_date_ads': 0, 'categories': {'format': [CARD], 'hook': [], 'angle': [], 'offer': [],
                                                          'proof': [], 'objection': [], 'cta': []}},
         'findings': [FINDING], 'options': OPTIONS, 'taxonomy': {'dimensions': DIMS, 'titles': TITLES},
         'label_coverage': {'v2': 0, 'legacy': 6, 'unlabeled': 0, 'total': 6},
         'pages': {'9': 'SYNTHETIC'}, 'collection': {'status': 'SYNTHETIC_UI_TEST_ONLY'},
         'analysis': {'status': 'SYNTHETIC_UI_TEST_ONLY'}, 'ocr': 'available', 'landscape': {'points': []}}


class AdaptationUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: urllib.request.urlopen(BASE + '/api/state', timeout=1).close()
        except OSError: raise unittest.SkipTest('Run scripts/lab.py serve for the adaptation UI test')
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def open(self, width=1360, scheme='dark'):
        ctx = self.browser.new_context(color_scheme=scheme, viewport={'width': width, 'height': 900})
        self.addCleanup(ctx.close)
        page = ctx.new_page(); self.errors = []; self.ad_queries = []
        page.on('pageerror', lambda e: self.errors.append(str(e)))

        def api(route):
            url = route.request.url
            if '/api/ads?' in url or url.endswith('/api/ads'): self.ad_queries.append(url); data = {'ads': [AD], 'total': 1, 'has_more': False}
            elif '/api/ads/SYNTHETIC1' in url: data = AD
            elif '/api/state' in url: data = STATE
            elif '/api/bootstrap' in url: data = {'csrf_token': 'synthetic'}
            else: data = None
            route.fulfill(status=200, content_type='application/json', body=json.dumps(data))
        page.route('**/api/**', api); page.goto(BASE); page.wait_for_selector('.ad-card')
        return page

    def test_filters_cover_the_seven_dimensions_with_portuguese_titles(self):
        page = self.open()
        selects = page.locator('section.filters select')
        self.assertEqual(selects.count(), 1 + len(DIMS))   # anunciante + 7 dimensões
        text = page.locator('section.filters').inner_text()
        for title in TITLES.values(): self.assertIn(title, text)
        self.assertIn('Rótulo Ângulo', page.locator('section.filters').inner_html())

    def test_findings_render_with_evidence_and_a_test_hypothesis_not_a_prediction(self):
        page = self.open()
        page.get_by_role('button', name='Padrões', exact=True).click()
        section = page.locator('#findings')
        self.assertIn('Achados', section.inner_text())
        body = section.inner_text()
        for fragment in ('Pessoa falando à câmera tem a maior fatia', '5 de 6', 'Curiosidade', 'Gráfico ou texto', 'Abra com um problema'):
            self.assertIn(fragment, body)
        self.assertIn('não é previsão', body.lower())
        self.assertIn('indicador de longevidade', body.lower())

    def test_see_examples_applies_filter_and_older_only_then_returns_to_the_wall(self):
        page = self.open()
        page.get_by_role('button', name='Padrões', exact=True).click()
        page.get_by_role('button', name='Ver exemplos', exact=True).click()
        page.wait_for_selector('.ad-card')
        self.assertEqual(page.locator('section.filters select').nth(1).input_value(), 'talking_head')
        self.assertTrue(page.locator('section.filters input[type=checkbox]').nth(1).is_checked())
        last = self.ad_queries[-1]
        self.assertIn('format=talking_head', last); self.assertIn('winner=true', last)
        self.assertTrue(page.get_by_role('button', name='Parede de miniaturas', exact=True).get_attribute('aria-pressed') == 'true')

    def test_legacy_notice_explains_partial_labels_without_charging(self):
        page = self.open()
        notice = page.locator('#label-coverage')
        self.assertIn('6', notice.inner_text())
        self.assertIn('rubrica anterior', notice.inner_text())
        self.assertIn('autoriza', notice.inner_text().lower())

    def test_inspector_shows_titles_labels_copy_sections_and_legacy_flag(self):
        page = self.open()
        page.locator('.ad-card').click(); page.wait_for_selector('dialog[open]')
        text = page.locator('dialog').inner_text()
        for fragment in ('Gancho', 'Curiosidade', 'Chamada para ação', 'Saber mais', 'Abertura', 'Cansado?', 'Fechamento / chamada', 'Baixe o guia.', 'rubrica anterior'):
            self.assertIn(fragment, text)

    def test_no_horizontal_scroll_and_no_page_errors_on_mobile_in_both_themes(self):
        for scheme in ('dark', 'light'):
            page = self.open(390, scheme)
            page.get_by_role('button', name='Padrões', exact=True).click(); page.wait_for_timeout(100)
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>window.innerWidth'), scheme)
            self.assertEqual(self.errors, [])

    def test_findings_hidden_when_none_and_old_state_shape_still_works(self):
        ctx = self.browser.new_context(); self.addCleanup(ctx.close)
        page = ctx.new_page(); errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
        old = {k: v for k, v in STATE.items() if k not in ('findings', 'options', 'taxonomy', 'label_coverage')}
        def api(route):
            url = route.request.url
            data = old if '/api/state' in url else {'csrf_token': 's'} if 'bootstrap' in url else None if '/api/jobs' in url else {'ads': [AD], 'total': 1, 'has_more': False}
            route.fulfill(status=200, content_type='application/json', body=json.dumps(data))
        page.route('**/api/**', api); page.goto(BASE); page.wait_for_selector('.ad-card')
        page.get_by_role('button', name='Padrões', exact=True).click()
        self.assertEqual(page.locator('#findings .finding').count(), 0)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
