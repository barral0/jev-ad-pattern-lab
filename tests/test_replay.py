"""Replay (shared-clock animation) of the saved archive. SYNTHETIC API fixtures only; no paid calls.
Inspired by the public ad-pattern-lab demo: wall, map and counters advance on ONE clock.
Requires the app served at 127.0.0.1:5194 (scripts/lab.py serve); skipped otherwise."""
import json, unittest, urllib.request
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5194'
N = 10


def make_ads():
    ads = []
    # ids deliberately NOT in date order, one unknown date, one two-ad group
    dates = ['2026-08-01', '2026-03-01', None, '2026-09-20', '2026-01-15', '2026-10-01', '2026-06-10', '2026-02-02', '2026-10-20', '2026-05-05']
    days = [87, 240, None, 37, 285, 26, 139, 267, 7, 175]
    for i in range(N):
        ads.append({'ad_id': f'SYN{i}', 'page_id': '9', 'page_name': 'SYNTHETIC', 'copy': f'Synthetic copy {i}', 'group_ad_ids': [f'SYN{i}'],
                    'fingerprint': f'fp{i}', 'days_active': days[i], 'winner_proxy': None if days[i] is None else days[i] >= 60,
                    'start_date': dates[i], 'end_date': None, 'thumbnail_src': None, 'labels': None, 'media_ids': [], 'active': True})
    return ads


ADS = make_ads()
POINTS = [{'fingerprint': f'fp{i}', 'ad_id': f'SYN{i}', 'x': (i % 5) * .5 - 1, 'y': (i // 5) * .6 - .3, 'cluster': i % 3, 'ad_count': 1} for i in range(N)]
STATE = {'metrics': {'total_ads': N, 'unique_creatives': N, 'analyzed_ads': 0, 'median_days': 100, 'winner_proxy_ads': 6, 'unknown_date_ads': 1, 'categories': {}},
         'findings': [], 'options': {}, 'label_coverage': {}, 'taxonomy': {}, 'pages': {'9': 'SYNTHETIC'},
         'collection': {'status': 'SYNTHETIC_UI_TEST_ONLY'}, 'analysis': {'status': 'SYNTHETIC_UI_TEST_ONLY'}, 'ocr': 'available',
         'landscape': {'method': 'synthetic', 'points': POINTS, 'clusters': []}}


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: urllib.request.urlopen(BASE + '/api/state', timeout=1).close()
        except OSError: raise unittest.SkipTest('Run scripts/lab.py serve for the replay integration test')
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def open(self, ads=None, reduced='no-preference', width=1360, tab=True, stack=False):
        data = ADS if ads is None else ads
        ctx = self.browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion=reduced, color_scheme='dark')
        self.addCleanup(ctx.close)
        page = ctx.new_page(); page.set_default_timeout(4000); self.errors = []; self.calls = []
        page.on('pageerror', lambda e: self.errors.append(str(e)))
        page.on('request', lambda r: self.calls.append((r.method, r.url)))
        state = json.loads(json.dumps(STATE)); state['landscape']['points'] = [dict(p, x=0, y=0) if stack else p for p in POINTS if any(a['fingerprint'] == p['fingerprint'] for a in data)]

        def api(route):
            url = route.request.url
            body = state if '/api/state' in url else {'csrf_token': 'x'} if 'bootstrap' in url else None if '/api/jobs' in url else \
                {'ads': data, 'total': len(data), 'offset': 0, 'limit': 500, 'has_more': False} if '/api/ads?' in url else data[0] if data else {}
            route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
        page.route('**/api/**', api); page.goto(BASE); page.wait_for_selector('.tab')
        if tab: page.get_by_role('button', name='Reprodução', exact=True).click(); page.wait_for_selector('.rp-stage')
        return page

    def seek(self, page, fraction):
        page.evaluate("f=>{const r=document.querySelector('#rp-scrub');r.value=Math.round(f*r.max);r.dispatchEvent(new Event('input',{bubbles:true}))}", fraction)
        page.wait_for_timeout(60)

    def counts(self, page):
        return {'tiles': page.locator('.rp-tile.revealed').count(), 'points': page.locator('.rp-point.revealed').count(),
                'counter': int(page.locator('#rp-count-revealed').inner_text())}

    # --- pure clock ---------------------------------------------------------------
    def test_clock_functions(self):
        page = self.open(tab=False)
        r = page.evaluate("""()=>{const R=window.BarralReplay;return {
          z:R.frame(0,3,20), s:R.frame(10,0,20), m:R.frame(10,10,20), e:R.frame(10,25,20), neg:R.frame(10,-5,20),
          adv1:R.advance(0,1000,1), adv3:R.advance(0,1000,3), cap:R.advance(19.9,5000,1,20),
          order:R.order([{id:'b',start:'2026-02-01'},{id:'a',start:'2026-02-01'},{id:'u',start:null},{id:'o',start:'2026-01-01'}]).map(x=>x.id)}}""")
        self.assertEqual(r['z']['completed'], 0); self.assertEqual(r['s']['completed'], 0)
        self.assertEqual(r['m']['completed'], 5); self.assertEqual(r['e']['completed'], 10); self.assertEqual(r['neg']['completed'], 0)
        self.assertEqual(r['adv1'], 1.0); self.assertEqual(r['adv3'], 3.0); self.assertEqual(r['cap'], 20)
        self.assertEqual(r['order'], ['o', 'a', 'b', 'u'], 'oldest first, tie by id, unknown dates last')

    # --- structure and one shared clock ---------------------------------------------
    def test_replay_tab_has_wall_map_and_counters(self):
        page = self.open()
        self.assertEqual(page.locator('.rp-tile').count(), N)
        self.assertEqual(page.locator('.rp-point').count(), N)
        for sel in ('#rp-play', '#rp-restart', '#rp-scrub', '#rp-speed'): self.assertEqual(page.locator(sel).count(), 1, sel)

    def test_wall_map_and_counter_share_one_clock(self):
        page = self.open(); page.locator('#rp-play').click() if page.locator('#rp-play').get_attribute('aria-pressed') == 'true' else None
        for f in (0, .3, .5, 1):
            self.seek(page, f); c = self.counts(page)
            self.assertEqual(c['tiles'], c['points'], f'wall and map diverged at {f}: {c}')
            self.assertEqual(c['tiles'], c['counter'], f'counter diverged at {f}: {c}')
        self.assertEqual(self.counts(page)['tiles'], N)
        self.seek(page, 0); self.assertEqual(self.counts(page)['tiles'], 0)

    def test_oldest_creative_appears_first(self):
        page = self.open(); self.seek(page, .1)
        self.assertEqual(page.locator('.rp-tile.revealed').first.get_attribute('data-ad'), 'SYN4', 'oldest start date (2026-01-15) first')

    def test_pause_freezes_and_play_resumes(self):
        page = self.open()
        self.seek(page, .2)
        if page.locator('#rp-play').get_attribute('aria-pressed') == 'true': page.locator('#rp-play').click()
        self.assertEqual(page.locator('#rp-play').get_attribute('aria-pressed'), 'false')
        before = page.locator('#rp-scrub').input_value(); page.wait_for_timeout(500)
        self.assertEqual(page.locator('#rp-scrub').input_value(), before, 'paused clock must not advance')
        page.locator('#rp-play').click(); page.wait_for_timeout(600)
        self.assertGreater(int(page.locator('#rp-scrub').input_value()), int(before))

    def test_restart_returns_to_zero_and_plays(self):
        page = self.open(); self.seek(page, 1)
        page.locator('#rp-restart').click(); page.wait_for_timeout(80)
        self.assertLess(int(page.locator('#rp-scrub').input_value()), int(page.locator('#rp-scrub').get_attribute('max')) * .2)
        self.assertEqual(page.locator('#rp-play').get_attribute('aria-pressed'), 'true')

    def test_keyboard_space_and_r(self):
        page = self.open(); page.locator('body').click(position={'x': 5, 'y': 400})
        was = page.locator('#rp-play').get_attribute('aria-pressed'); page.keyboard.press('Space')
        self.assertNotEqual(page.locator('#rp-play').get_attribute('aria-pressed'), was)
        self.seek(page, .9); page.keyboard.press('r'); page.wait_for_timeout(80)
        self.assertLess(int(page.locator('#rp-scrub').input_value()), int(page.locator('#rp-scrub').get_attribute('max')) * .5)

    def test_speed_selector_offers_1_2_3(self):
        page = self.open()
        self.assertEqual(page.locator('#rp-speed option').all_inner_texts(), ['1×', '2×', '3×'])

    # --- honesty, safety, interaction -------------------------------------------------
    def test_discloses_it_is_a_replay_of_saved_data(self):
        text = self.open().locator('.rp-note').inner_text().lower()
        for needle in ('reprodução', 'dados salvos', 'data de início', 'não', 'jev'): self.assertIn(needle, text)

    def test_replay_makes_no_writes_and_no_paid_calls(self):
        page = self.open(); self.seek(page, 1); page.wait_for_timeout(200)
        bad = [c for c in self.calls if c[0] != 'GET' and 'bootstrap' not in c[1]]
        self.assertEqual(bad, [], 'replay must be read-only')
        self.assertEqual(self.errors, [])

    def test_clicking_a_revealed_tile_opens_inspector(self):
        page = self.open(); self.seek(page, 1)
        page.locator('.rp-tile.revealed').first.click(); page.wait_for_selector('dialog[open]')

    def test_unrevealed_tiles_are_not_focusable(self):
        page = self.open(); self.seek(page, 0)
        self.assertTrue(page.evaluate("[...document.querySelectorAll('.rp-tile:not(.revealed)')].every(t=>t.disabled||t.tabIndex===-1||t.hasAttribute('inert')||t.closest('[inert]'))"))

    def test_empty_archive_shows_message_and_no_division_by_zero(self):
        page = self.open(ads=[])
        self.assertIn('nada para reproduzir', page.locator('.rp-empty').inner_text().lower())
        self.assertEqual(self.errors, [])

    # --- motion preferences, responsive, theme -------------------------------------------
    def test_reduced_motion_starts_finished_and_paused(self):
        page = self.open(reduced='reduce')
        self.assertEqual(page.locator('#rp-play').get_attribute('aria-pressed'), 'false')
        self.assertEqual(self.counts(page)['tiles'], N)
        self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('.rp-tile')).transitionDuration"), '0s')

    def test_uses_official_easing_and_neutral_tokens(self):
        page = self.open()
        self.assertIn('cubic-bezier(0.16, 1, 0.3, 1)', page.evaluate("getComputedStyle(document.querySelector('.rp-tile')).transitionTimingFunction"))
        self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('.rp-stage')).backgroundColor"), 'rgb(21, 21, 21)')

    def test_no_horizontal_overflow_at_360(self):
        page = self.open(width=360)
        self.assertFalse(page.evaluate('document.documentElement.scrollWidth>window.innerWidth'))
        self.assertEqual(self.counts(page)['tiles'] >= 0, True)

    def test_points_sharing_a_position_are_spread_deterministically(self):
        page = self.open(tab=False)
        r = page.evaluate("""()=>{const R=window.BarralReplay;
          const items=[...Array(30).keys()].map(i=>({id:'s'+i,px:40,py:50})).concat([{id:'alone',px:80,py:20}]);
          const a=R.spread(items),b=R.spread(items);
          const keys=new Set(a.map(i=>i.sx.toFixed(2)+','+i.sy.toFixed(2)));
          const alone=a.find(i=>i.id==='alone');
          const grp=a.filter(i=>i.id!=='alone');
          const cx=grp.reduce((s,i)=>s+i.sx,0)/grp.length, cy=grp.reduce((s,i)=>s+i.sy,0)/grp.length;
          return {distinct:keys.size,total:a.length,same:JSON.stringify(a)===JSON.stringify(b),aloneKept:alone.sx===80&&alone.sy===20,
                  inside:a.every(i=>i.sx>=2&&i.sx<=98&&i.sy>=2&&i.sy<=98),cx,cy,
                  minGap:Math.min(...grp.flatMap((i,k)=>grp.slice(k+1).map(j=>Math.hypot(i.sx-j.sx,i.sy-j.sy)))),
                  firstAtCenter:grp[0].sx===40&&grp[0].sy===50,inputUntouched:items[0].sx===undefined}}""")
        self.assertEqual(r['distinct'], r['total'], 'every point must be individually visible')
        self.assertTrue(r['same'], 'spread must be deterministic'); self.assertTrue(r['aloneKept']); self.assertTrue(r['inside'])
        self.assertTrue(r['firstAtCenter'] and r['inputUntouched'])
        self.assertAlmostEqual(r['cx'], 40, delta=3); self.assertAlmostEqual(r['cy'], 50, delta=3)
        self.assertGreater(r['minGap'], 1.5, 'dots must not overlap')

    def test_map_explains_the_spread(self):
        self.assertIn('espiral', self.open().locator('.rp-note').inner_text().lower())

    def test_stacked_creatives_render_at_distinct_screen_positions(self):
        page = self.open(stack=True)
        self.seek(page, 1)
        pos = page.evaluate("[...document.querySelectorAll('.rp-point.revealed')].map(e=>e.style.left+','+e.style.top)")
        self.assertEqual(len(set(pos)), len(pos))

    def test_loop_stops_when_leaving_replay(self):
        page = self.open(); page.get_by_role('button', name='Parede de miniaturas', exact=True).click(); page.wait_for_timeout(100)
        self.assertEqual(page.locator('.rp-stage').count(), 0)
        self.assertFalse(page.evaluate('window.BarralReplay.running()'), 'rAF loop must stop when the tab is closed')


if __name__ == '__main__':
    unittest.main()
