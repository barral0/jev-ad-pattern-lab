"""Whole UI must be Brazilian Portuguese: visible text, aria-labels, titles, placeholders, alt, status codes,
dates and numbers. SYNTHETIC fixtures; the ad copy itself (user data) is excluded. Needs the app at 127.0.0.1:5194."""
import json, re, unittest, urllib.request
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5194'
ENGLISH = ('the and with for not only never proof ad ads creative creatives thumbnail thumbnails search captured collected needs review load more '
           'evidence days unknown close refresh analysis cost reservations median active unique analyzed landscape patterns wall inspector '
           'probability distribution confidence native audience start grouped callout page copy still loading matching worth investigating '
           'shares rates comparator eligible relative run collection replay choice judgments generated examples workspace receipts '
           'longevity proxy continue failed request check server speed timeline').split()
ENGLISH_RE = re.compile(r'\b(' + '|'.join(ENGLISH) + r')\b', re.I)
SNAKE_RE = re.compile(r'\b[a-z]{2,}_[a-z_]{2,}\b')

LABELS = {'model': 'jev-1.14.0', 'rubric_version': 'r2', 'needs_review': True, 'called_audience': 'designers', 'visual_evidence': 'still_only',
          'visual_callout': {'status': 'available', 'text': 'TEXTO NA IMAGEM'},
          'answers': {'format': {'type': 'choice', 'choice': 'graphic', 'confidence': .456, 'probabilities': {'graphic': .9, 'mixed': .1}},
                      'hook': {'type': 'choice', 'choice': 'direct', 'confidence': .8, 'probabilities': {'direct': 1.0}}}}
AD = {'ad_id': 'SYN1', 'page_id': '9', 'page_name': 'SINTÉTICO', 'copy': 'Texto sintético de teste.', 'group_ad_ids': ['SYN1', 'SYN2'], 'fingerprint': 'fp1',
      'days_active': 80, 'winner_proxy': True, 'start_date': '2026-08-01', 'end_date': None, 'thumbnail_src': None, 'media_ids': [], 'active': True,
      'labels': LABELS, 'dimension_titles': {'format': 'Formato', 'hook': 'Gancho'}, 'label_names': {'format': 'Gráfico ou texto', 'hook': 'Direto'},
      'copy_breakdown': {'source': 'Texto salvo do anúncio', 'text': 'x', 'sections': [{'role': 'Abertura', 'text': 'Texto sintético.'}]}}
CARD = {'category': 'graphic', 'winner_proxy_rate': .456, 'ad_count': 2, 'unique_creatives': 1, 'share': .5, 'median_days': 80, 'eligible_ads': 2,
        'unknown_date_ads': 0, 'comparator': 'mixed', 'lift_pp': 12.5, 'relative_lift': .25, 'evidence_ad_ids': ['SYN1']}
FINDING = {'dimension': 'format', 'category': 'graphic', 'heading': 'Gráfico ou texto lidera', 'observation': 'Observação sintética.', 'share': .456,
           'baseline': .3, 'lift': 1.52, 'minimum_group_size': 5, 'comparison': {'label': 'Direto', 'n': 3, 'share': .2},
           'facets': [{'dimension': 'hook', 'label': 'Direto', 'n': 2, 'total': 3}], 'next_test': 'Teste sintético.', 'example_ids': ['SYN1']}
STATE = {'metrics': {'total_ads': 2, 'unique_creatives': 1, 'analyzed_ads': 2, 'median_days': 80.5, 'winner_proxy_ads': 2, 'unknown_date_ads': 0,
                     'categories': {'format': [CARD]}},
         'findings': [FINDING], 'options': {'format': [{'value': 'graphic', 'label': 'Gráfico ou texto'}, {'value': 'mixed', 'label': 'Formato misto'}], 'hook': [{'value': 'direct', 'label': 'Direto'}]},
         'label_coverage': {'legacy': 1, 'total': 2}, 'taxonomy': {'dimensions': ['format', 'hook'], 'titles': {'format': 'Formato', 'hook': 'Gancho'}},
         'pages': {'9': 'SINTÉTICO'}, 'collection': {'status': 'incomplete_scroll_cap'},
         'analysis': {'status': 'partial', 'charged_or_reserved_usd': '0.0162'}, 'ocr': 'available',
         'landscape': {'method': 'Método sintético', 'points': [{'fingerprint': 'fp1', 'ad_id': 'SYN1', 'x': 0, 'y': 0, 'cluster': 0, 'ad_count': 2}], 'clusters': 1}}
JOB = {'id': 'j1', 'action': 'collect_analyze', 'page_id': '9', 'budget': '0.4999', 'paid_consent': True, 'status': 'running', 'stage': 'collect',
       'warning': None, 'error': None, 'live': {'active_ads': 3, 'analyzed_ads': 1, 'capture_status': 'incomplete_scroll_cap'},
       'results': {'collect': {'status': 'incomplete_scroll_cap', 'ads': 3},
                   'analyze': {'status': 'complete', 'analyzed_ads': 3, 'calls': 2, 'reported_cost_usd': '0.0123', 'reserved_unknown_usd': '0.0005'}}}


class PortugueseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: urllib.request.urlopen(BASE + '/api/state', timeout=1).close()
        except OSError: raise unittest.SkipTest('Run scripts/lab.py serve for the Portuguese UI test')
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def open(self, job=None, state_status=None, ads=True, width=1360, unknown_metrics=False):
        ctx = self.browser.new_context(viewport={'width': width, 'height': 900}, locale='pt-BR', color_scheme='dark')
        self.addCleanup(ctx.close)
        page = ctx.new_page(); page.set_default_timeout(4000)

        def api(route):
            url = route.request.url
            if state_status: return route.fulfill(status=state_status, content_type='application/json', body='{}')
            state = dict(STATE, metrics=dict(STATE['metrics'], median_days=None, unknown_date_ads=None, winner_proxy_ads=None)) if unknown_metrics else STATE
            body = state if '/api/state' in url else {'csrf_token': 'x'} if 'bootstrap' in url else (job or None) if '/api/jobs' in url else \
                {'ads': [AD] if ads else [], 'total': 1 if ads else 0, 'offset': 0, 'limit': 500, 'has_more': False} if '/api/ads?' in url else AD
            route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
        page.route('**/api/**', api); page.goto(BASE); page.wait_for_selector('header')
        page.wait_for_timeout(300)
        return page

    def texts(self, page):
        return page.evaluate("""()=>{
          const skip='script,style,code,pre,.full-copy,.copy-preview,.copy-section p';
          const out=[];const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
          while(w.nextNode()){const n=w.currentNode;if(n.parentElement.closest(skip))continue;const t=n.textContent.trim();if(t)out.push(t)}
          document.querySelectorAll('[aria-label],[title],[placeholder],[alt]').forEach(e=>['aria-label','title','placeholder','alt'].forEach(a=>{const v=e.getAttribute(a);if(v)out.push(v)}));
          document.querySelectorAll('option').forEach(o=>out.push(o.textContent));
          return out}""")

    def assert_portuguese(self, page, where):
        bad = []
        for t in self.texts(page):
            m = ENGLISH_RE.search(t) or SNAKE_RE.search(t)
            if m: bad.append(f'{m.group(0)!r} em {t[:90]!r}')
        self.assertEqual(bad, [], f'inglês restante em {where}')

    # ---- document -----------------------------------------------------------------
    def test_document_language_and_title(self):
        page = self.open()
        self.assertEqual(page.evaluate('document.documentElement.lang'), 'pt-BR')
        self.assertNotRegex(page.title().lower(), r'\b(pattern|lab|ad)\b')

    # ---- every view ---------------------------------------------------------------
    def test_main_screen_is_portuguese(self): self.assert_portuguese(self.open(job=JOB), 'tela principal com execução ativa')

    def test_all_tabs_exist_with_portuguese_names(self):
        page = self.open()
        for name in ('Parede de miniaturas', 'Mapa', 'Padrões', 'Reprodução'):
            self.assertEqual(page.get_by_role('button', name=name, exact=True).count(), 1, name)

    def test_each_view_is_portuguese(self):
        page = self.open()
        for name in ('Parede de miniaturas', 'Mapa', 'Padrões', 'Reprodução'):
            page.get_by_role('button', name=name, exact=True).click(); page.wait_for_timeout(500)
            self.assert_portuguese(page, 'aba ' + name)

    def test_inspector_is_portuguese(self):
        page = self.open(); page.locator('.ad-card').click(); page.wait_for_selector('dialog[open]')
        self.assert_portuguese(page, 'inspetor')
        self.assertIn('Fechar', page.locator('dialog button').first.inner_text())

    def test_empty_state_is_portuguese(self):
        page = self.open(ads=False); self.assert_portuguese(page, 'estado vazio')

    def test_network_error_is_portuguese(self):
        page = self.open(state_status=500); page.wait_for_timeout(300)
        self.assertRegex(page.locator('.error[role=alert]').first.inner_text(), r'Falha')
        self.assert_portuguese(page, 'erro de rede')

    # ---- codes, dates, numbers -----------------------------------------------------------
    def test_status_codes_are_translated(self):
        page = self.open(job=JOB)
        pill = page.locator('.status').inner_text().lower()
        self.assertIn('incompleta', pill); self.assertNotIn('_', pill)
        job = page.locator('#job-status').inner_text().lower()
        for needle in ('em execução', 'captura', 'classificados', 'chamadas'): self.assertIn(needle, job)
        self.assertIn('disponível', page.locator('.meta-line').inner_text().lower())

    def test_labels_are_not_title_cased(self):
        page = self.open()
        self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('.filters label')).textTransform"), 'none')
        self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('.pattern-grid h3, h3')).textTransform"), 'none')

    def test_comparator_code_is_shown_with_its_portuguese_label(self):
        page = self.open(); page.get_by_role('button', name='Padrões', exact=True).click(); page.wait_for_timeout(300)
        body = page.locator('.patterns').inner_text()
        self.assertIn('Contra Formato misto', body); self.assertNotIn('Contra mixed', body)

    def test_failed_job_status_translated(self):
        page = self.open(job=dict(JOB, status='failed', stage='analyze', error='Falha de teste'))
        self.assertIn('falhou', page.locator('#job-status').inner_text().lower())

    def test_numbers_and_dates_use_brazilian_format(self):
        page = self.open(); page.get_by_role('button', name='Padrões', exact=True).click(); page.wait_for_timeout(300)
        body = page.locator('.patterns').inner_text()
        self.assertIn('45,6%', body); self.assertIn('12,5', body); self.assertNotRegex(body, r'\d\.\d+%')
        page.get_by_role('button', name='Parede de miniaturas', exact=True).click()
        page.locator('.ad-card').click(); page.wait_for_selector('dialog[open]')
        dialog = page.locator('dialog').inner_text()
        self.assertIn('01/08/2026', dialog); self.assertIn('45,6%', dialog)
        self.assertIn('US$ 0,0162', page.locator('.meta-line').inner_text())

    def test_long_portuguese_values_do_not_overflow_on_mobile(self):
        for width in (390, 360):
            page = self.open(unknown_metrics=True, width=width, job=JOB)
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'), f'estouro horizontal a {width}px')

    # ---- server side strings -----------------------------------------------------------------
    def test_server_strings_are_portuguese(self):
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        for name, needle in (('analytics.py', 'Copy TF-IDF'), ('webapp.py', 'Thumbnail unavailable'), ('webjobs.py', 'Invalid stage result'), ('webjobs.py', 'CLI stage failed')):
            self.assertNotIn(needle, (root / name).read_text(encoding='utf-8'), f'{name}: {needle}')

    def test_live_landscape_method_is_portuguese(self):
        state = json.load(urllib.request.urlopen(BASE + '/api/state'))
        method = (state.get('landscape') or {}).get('method')
        if not method: self.skipTest('sem mapa salvo')
        self.assertNotIn('Copy TF-IDF', method)


if __name__ == '__main__':
    unittest.main()
