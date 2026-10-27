"""barral.pro design standard, checked in a real browser. API responses are SYNTHETIC fixtures.
Requires the application served at 127.0.0.1:5194 (scripts/lab.py serve); skipped otherwise.
Source of truth: site DESIGN.md + Wiki 'Padrão de Design do Ecossistema barral.pro'."""
import json, unittest, urllib.request
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5194'
CARD = {'category': 'Direct', 'winner_proxy_rate': .5, 'ad_count': 2, 'unique_creatives': 1, 'share': 1, 'median_days': 80,
        'eligible_ads': 2, 'unknown_date_ads': 0, 'comparator': None, 'lift_pp': None, 'relative_lift': None,
        'evidence_ad_ids': ['SYNTHETIC1']}
AD = {'ad_id': 'SYNTHETIC1', 'page_id': '9', 'page_name': 'SYNTHETIC', 'copy': 'Synthetic copy for design test.',
      'group_ad_ids': ['SYNTHETIC1'], 'fingerprint': 'synthetic', 'days_active': 80, 'start_date': '2026-01-01',
      'end_date': None, 'thumbnail_src': None,
      'labels': {'needs_review': True, 'answers': {'hook': {'type': 'choice', 'choice': 'Direct', 'confidence': .4,
                 'probabilities': {'Direct': 1.0}}}, 'visual_callout': {'status': 'unavailable', 'text': None}}}
STATE = {'metrics': {'total_ads': 2, 'unique_creatives': 1, 'analyzed_ads': 2, 'median_days': 80, 'winner_proxy_ads': 2,
                     'unknown_date_ads': 0, 'categories': {'hook': [CARD]}},
         'pages': {'9': 'SYNTHETIC'}, 'collection': {'status': 'SYNTHETIC_UI_TEST_ONLY'},
         'analysis': {'status': 'SYNTHETIC_UI_TEST_ONLY'}, 'ocr': 'available', 'landscape': {'points': []}}


def api(route):
    url = route.request.url
    if '/api/state' in url: data = STATE
    elif '/api/bootstrap' in url: data = {'csrf_token': 'synthetic'}
    elif '/api/jobs' in url: data = None
    elif '/api/ads/SYNTHETIC1' in url: data = AD
    else: data = {'ads': [AD], 'total': 1, 'has_more': False}
    route.fulfill(status=200, content_type='application/json', body=json.dumps(data))


class DesignStandardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: urllib.request.urlopen(BASE + '/api/state', timeout=1).close()
        except OSError: raise unittest.SkipTest('Run scripts/lab.py serve for the design integration test')
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def open(self, scheme='dark', width=1360, reduced='no-preference', storage=None):
        context = self.browser.new_context(color_scheme=scheme, reduced_motion=reduced, viewport={'width': width, 'height': 900})
        self.addCleanup(context.close)
        page = context.new_page()
        self.requests = []
        page.on('request', lambda r: self.requests.append(r.url))
        page.route('**/api/**', api)
        if storage: page.add_init_script(f"localStorage.setItem('barral-theme','{storage}')")
        page.goto(BASE); page.wait_for_selector('.ad-card')
        return page

    def css(self, page, selector, prop):
        return page.evaluate("([s,p])=>getComputedStyle(document.querySelector(s))[p]", [selector, prop])

    # --- colors -----------------------------------------------------------------
    def test_dark_theme_uses_official_neutral_tokens(self):
        page = self.open('dark')
        self.assertEqual(self.css(page, 'html', 'color-scheme').split()[0], 'dark')
        self.assertEqual(self.css(page, 'body', 'backgroundColor'), 'rgb(10, 10, 10)')
        self.assertEqual(self.css(page, 'body', 'color'), 'rgb(237, 237, 237)')
        self.assertEqual(self.css(page, '.panel', 'backgroundColor'), 'rgb(21, 21, 21)')
        self.assertEqual(self.css(page, '.panel', 'borderTopColor'), 'rgb(38, 38, 38)')

    def test_light_theme_uses_official_neutral_tokens(self):
        page = self.open('light')
        self.assertEqual(self.css(page, 'body', 'backgroundColor'), 'rgb(250, 250, 250)')
        self.assertEqual(self.css(page, 'body', 'color'), 'rgb(23, 23, 23)')
        self.assertEqual(self.css(page, '.panel', 'backgroundColor'), 'rgb(255, 255, 255)')
        self.assertEqual(self.css(page, '.panel', 'borderTopColor'), 'rgb(229, 229, 229)')

    def test_no_bluish_dark_backgrounds(self):
        page = self.open('dark')
        for selector in ('body', '.panel', 'header', '.ad-card', '.stat'):
            r, g, b = [int(x) for x in self.css(page, selector, 'backgroundColor').replace('rgba', '').strip('rgb()').split(',')[:3]]
            self.assertLessEqual(max(r, g, b) - min(r, g, b), 2, selector + ' must be neutral, not tinted')

    # --- theme system -----------------------------------------------------------
    def test_theme_script_is_blocking_and_precedes_styles(self):
        page = self.open('dark')
        head = page.evaluate("[...document.head.children].map(e=>[e.tagName,e.getAttribute('src')||e.getAttribute('href')||'',e.hasAttribute('defer'),e.hasAttribute('async')])")
        names = [h[1] for h in head]
        theme = next(i for i, h in enumerate(head) if h[0] == 'SCRIPT' and h[1].endswith('theme.js'))
        self.assertFalse(head[theme][2] or head[theme][3], 'theme.js must block rendering')
        self.assertLess(theme, next(i for i, n in enumerate(names) if n.endswith('app.css')))

    def test_toggle_persists_choice_under_shared_storage_key(self):
        page = self.open('dark')
        self.assertTrue(page.evaluate("document.documentElement.classList.contains('dark')"))
        page.locator('#theme-toggle').click()
        self.assertEqual(page.evaluate("localStorage.getItem('barral-theme')"), 'light')
        self.assertTrue(page.evaluate("document.documentElement.classList.contains('light')"))
        self.assertEqual(self.css(page, 'body', 'backgroundColor'), 'rgb(250, 250, 250)')
        page.reload(); page.wait_for_selector('.ad-card')
        self.assertTrue(page.evaluate("document.documentElement.classList.contains('light')"))

    def test_saved_choice_beats_system_setting(self):
        page = self.open('dark', storage='light')
        self.assertEqual(self.css(page, 'body', 'backgroundColor'), 'rgb(250, 250, 250)')

    def test_toggle_icons_switch_by_css_only(self):
        page = self.open('dark')
        self.assertEqual(self.css(page, '#icon-sun', 'display'), 'none')
        self.assertNotEqual(self.css(page, '#icon-moon', 'display'), 'none')
        page.locator('#theme-toggle').click()
        self.assertNotEqual(self.css(page, '#icon-sun', 'display'), 'none')
        self.assertEqual(self.css(page, '#icon-moon', 'display'), 'none')

    # --- typography -------------------------------------------------------------
    def test_inter_is_self_hosted_and_headings_use_negative_tracking(self):
        page = self.open('dark')
        self.assertTrue(self.css(page, 'body', 'fontFamily').startswith('Inter'))
        self.assertTrue(page.evaluate("document.fonts.ready.then(()=>[...document.fonts].some(f=>f.family.includes('Inter')&&f.status==='loaded'))"))
        self.assertTrue(float(self.css(page, 'h1', 'letterSpacing').replace('px', '')) < 0)
        self.assertGreaterEqual(int(self.css(page, 'h1', 'fontWeight')), 800)
        remote = {urlsplit(u).netloc for u in self.requests if urlsplit(u).scheme in ('http', 'https')}
        self.assertEqual(remote, {'127.0.0.1:5194'}, 'no remote fonts, scripts or styles')

    # --- shape, components, motion ---------------------------------------------
    def test_radii_follow_scale(self):
        page = self.open('dark')
        self.assertEqual(self.css(page, '.panel', 'borderTopLeftRadius'), '16px')
        self.assertEqual(self.css(page, '.ad-card', 'borderTopLeftRadius'), '16px')
        self.assertEqual(self.css(page, 'input[type=search]', 'borderTopLeftRadius'), '8px')
        self.assertGreaterEqual(float(self.css(page, '.btn', 'borderTopLeftRadius').replace('px', '')), 999)

    def test_primary_cta_is_button_in_button_pill(self):
        page = self.open('dark')
        button = page.get_by_role('button', name='Capturar + classificar', exact=True)
        self.assertEqual(button.locator('.btn-icon-circle svg[aria-hidden=true]').count(), 1)
        self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('.btn-primary')).paddingLeft"), '24px')
        self.assertEqual(self.css(page, '.btn-primary', 'backgroundColor'), 'rgb(237, 237, 237)')

    def test_official_easing_and_reduced_motion(self):
        page = self.open('dark')
        self.assertIn('cubic-bezier(0.16, 1, 0.3, 1)', self.css(page, '.ad-card', 'transitionTimingFunction'))
        page.locator('.ad-card').hover(); page.wait_for_timeout(350)
        self.assertIn('-2', page.evaluate("getComputedStyle(document.querySelector('.ad-card')).transform"))
        calm = self.open('dark', reduced='reduce')
        self.assertEqual(self.css(calm, '.ad-card', 'transitionDuration'), '0s')

    def test_errors_are_not_signalled_by_color_alone(self):
        page = self.open('dark')
        page.evaluate("document.querySelector('#job-error').textContent='Falha de teste'")
        page.evaluate("document.querySelector('#job-error').removeAttribute('hidden');document.querySelector('#job-error').style.display='block'")
        self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('#job-error'),'::before').content"), '"Erro"')

    # --- responsive -------------------------------------------------------------
    def test_no_horizontal_overflow_at_360px_in_both_themes(self):
        for scheme in ('dark', 'light'):
            page = self.open(scheme, width=360)
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>window.innerWidth'), scheme)
            self.assertGreaterEqual(page.locator('#theme-toggle').bounding_box()['width'], 36)


if __name__ == '__main__':
    unittest.main()
