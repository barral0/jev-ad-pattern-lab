"""Real browser UI tests with SYNTHETIC responses, never default database writes.
Requires the locally served static application at localhost:5194; skipped otherwise.
"""
import unittest, json, urllib.request
from playwright.sync_api import sync_playwright
class BrowserTests(unittest.TestCase):
    def test_wall_inspector_search_patterns_and_mobile(self):
        try: urllib.request.urlopen('http://127.0.0.1:5194/api/state',timeout=1).close()
        except OSError: self.skipTest('Run scripts/lab.py serve for optional browser integration test')
        ad={'ad_id':'SYNTHETIC1','page_id':'9','page_name':'SYNTHETIC test fixture','copy':'<script>window.INJECTED=true</script> Calling designers.','group_ad_ids':['SYNTHETIC1'],'fingerprint':'synthetic','days_active':80,'start_date':'2026-01-01','end_date':None,'thumbnail_src':None,'labels':{'needs_review':True,'answers':{'hook':{'type':'choice','choice':'Direct','confidence':.4,'probabilities':{'Direct':1.0}}},'visual_callout':{'status':'unavailable','text':None}}}
        card={'category':'Direct','winner_proxy_rate':1,'ad_count':1,'unique_creatives':1,'share':1,'median_days':80,'eligible_ads':1,'unknown_date_ads':0,'comparator':None,'lift_pp':None,'relative_lift':None,'evidence_ad_ids':['SYNTHETIC1']}
        state={'metrics':{'total_ads':1,'unique_creatives':1,'analyzed_ads':1,'median_days':80,'winner_proxy_ads':1,'unknown_date_ads':0,'categories':{'hook':[card]}},'pages':{'9':'SYNTHETIC test fixture'},'collection':{'status':'SYNTHETIC_UI_TEST_ONLY'},'analysis':{'status':'SYNTHETIC_UI_TEST_ONLY'},'ocr':'unavailable','landscape':{'points':[]}}
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1360,'height':900});errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            def route(request):
                url=request.request.url
                data=state if '/api/state' in url else ad if '/api/ads/SYNTHETIC1' in url else {'ads':[ad],'total':1,'has_more':False}
                request.fulfill(status=200,content_type='application/json',body=json.dumps(data))
            page.route('**/api/**',route);page.goto('http://127.0.0.1:5194');page.wait_for_selector('.ad-card')
            page.locator('.ad-card').click();page.wait_for_selector('dialog[open]')
            self.assertIn('Calling designers',page.locator('.full-copy').inner_text())
            self.assertIsNone(page.evaluate('window.INJECTED'))
            page.get_by_role('button',name='Fechar',exact=True).click()
            page.get_by_role('button',name='Padrões',exact=True).click();page.get_by_role('button',name='Anúncio SYNTHETIC1',exact=True).click();page.wait_for_selector('dialog[open]')
            page.keyboard.press('Escape');page.set_viewport_size({'width':390,'height':844});page.emulate_media(color_scheme='dark');page.wait_for_timeout(100)
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>window.innerWidth'))
            self.assertEqual(errors,[])
            browser.close()
