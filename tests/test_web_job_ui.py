"""Real Chromium clicks; all APIs intercepted with SYNTHETIC responses."""
import json, unittest, urllib.request
from playwright.sync_api import sync_playwright, expect

class JobBrowserTests(unittest.TestCase):
    def test_capture_poll_refresh_paid_consent_and_errors(self):
        try: urllib.request.urlopen('http://127.0.0.1:5194/api/state',timeout=1).close()
        except OSError: self.skipTest('Requires existing local server on 5194')
        state={'metrics':{},'pages':{'9':'SYNTHETIC'},'collection':{},'analysis':{},'landscape':{'points':[]}}
        calls=[]; polls=[]; refreshes=[]
        job={'id':'synthetic-job','page_id':'9','action':'collect','status':'queued','stage':'queued','results':{},'error':None}
        with sync_playwright() as p:
            browser=p.chromium.launch(); page=browser.new_page(viewport={'width':1360,'height':1000}); errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            def route(r):
                url=r.request.url
                status=200
                if '/api/bootstrap' in url: data={'csrf_token':'SYNTHETIC_CSRF'}
                elif '/api/jobs' in url:
                    if r.request.method=='POST':
                        calls.append(r.request.post_data_json)
                        self.assertEqual(r.request.headers['x-csrf-token'],'SYNTHETIC_CSRF')
                        if len(calls)>1: data={'detail':'SYNTHETIC erro visível'};status=422
                        else: data=job;status=202
                    elif not calls: data=None
                    else:
                        polls.append(url)
                        data={**job,'status':'running' if len(polls)==1 else 'complete','stage':'collect','results':{'collect':{'ads':2,'status':'complete'}}}
                elif '/api/state' in url: refreshes.append(url);data=state
                else: data={'ads':[],'total':0,'has_more':False}
                r.fulfill(status=status,content_type='application/json',body=json.dumps(data))
            page.route('**/api/**',route);page.goto('http://127.0.0.1:5194')
            page.get_by_label('ID da página',exact=True).fill('9')
            page.get_by_role('button',name='Capturar',exact=True).click()
            expect(page.get_by_role('button',name='Capturar',exact=True)).to_be_disabled()
            expect(page.locator('#job-status')).to_contain_text('concluída',timeout=10000)
            self.assertEqual(calls[0]['action'],'collect');self.assertEqual(calls[0]['page_id'],'9')
            for _ in range(100):
                if any('page_id=9' in url for url in refreshes): break
                page.wait_for_timeout(20)
            self.assertTrue(any('page_id=9' in url for url in refreshes))
            expect(page.get_by_role('button',name='Classificar com Jev',exact=True)).to_be_disabled()
            page.get_by_label('Autorizo chamadas cobradas').check()
            page.get_by_role('button',name='Classificar com Jev',exact=True).click()
            expect(page.locator('#job-error')).to_contain_text('SYNTHETIC erro visível')
            self.assertTrue(calls[1]['paid_consent']);self.assertEqual(calls[1]['action'],'analyze')
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(100)
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            self.assertEqual(errors,[]);browser.close()
