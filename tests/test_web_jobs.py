"""SYNTHETIC isolated stores/transports; no Meta or billed API calls."""
import asyncio, tempfile, unittest
from pathlib import Path
from labcore import Store, Ad

class PageScopeTests(unittest.TestCase):
    def test_selected_page_only_can_reserve_or_send(self):
        from inference import analyze, cache_key, MODEL
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)); store.put_ads([Ad(ad_id='s1',page_id='9'),Ad(ad_id='s2',page_id='8')])
            selected=store.ads()[0]; store.cache_put(cache_key(selected,MODEL,False),{'synthetic':True})
            async def forbidden(body): self.fail('Cross-page paid request')
            report=asyncio.run(analyze(store,api_key='SYNTHETIC',transport=forbidden,images=False,page_id='9',run_id='scoped'))
            self.assertEqual(report['total_ads'],1); self.assertEqual(report['calls'],0)
            self.assertEqual(report['page_id'],'9'); self.assertEqual(len(store.ads()),2)
            self.assertEqual(store.meta('analysis:9')['run_id'],'scoped')

class JobTests(unittest.TestCase):
    def test_cli_runner_fixed_argv_and_cancel_stops_child(self):
        from webjobs import Jobs
        from unittest.mock import patch, MagicMock
        import threading
        async def scenario(s):
            done=threading.Event();started=threading.Event()
            process=MagicMock();process.returncode=0
            def communicate(**kwargs):
                started.set();done.wait(2)
                return '{"status":"complete","calls":0}', ''
            process.communicate.side_effect=communicate
            process.kill.side_effect=done.set
            with patch('webjobs.subprocess.Popen',return_value=process) as popen:
                task=asyncio.create_task(Jobs(s).run_cli('analyze',{'id':'synthetic','page_id':'9','budget':'.1'}))
                await asyncio.to_thread(started.wait,1)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError): await task
                process.kill.assert_called_once()
                argv=popen.call_args.args[0]
                self.assertEqual(argv[-6:],['--page-id','9','--budget','.1','--run-id','web-synthetic'])
                self.assertFalse(popen.call_args.kwargs['shell'])
        with tempfile.TemporaryDirectory() as d: asyncio.run(scenario(Store(Path(d))))

    def test_page_metadata_and_job_live_counts_never_mix_pages(self):
        from fastapi.testclient import TestClient
        from webapp import create_app
        async def runner(stage,job): return {'status':'complete','calls':0}
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d));s.put_ads([Ad(ad_id='s1',page_id='9'),Ad(ad_id='s2',page_id='8')])
            s.set_meta('collection',{'status':'complete','page_id':'8','ads':99})
            s.set_meta('analysis',{'status':'complete','page_id':'8','total_ads':99})
            with TestClient(create_app(s,job_runner=runner),base_url='http://localhost:5194') as c:
                state=c.get('/api/state?page_id=9').json()
                self.assertEqual(state['collection']['status'],'not_collected')
                self.assertEqual(state['analysis']['status'],'not_analyzed')
                headers={'X-CSRF-Token':c.get('/api/bootstrap').json()['csrf_token']}
                job=c.post('/api/jobs',json={'action':'analyze','page_id':'9','paid_consent':True},headers=headers).json()
                live=c.get('/api/jobs/'+job['id']).json()['live']
                self.assertEqual(live['active_ads'],1);self.assertEqual(live['analyzed_ads'],0)

    def test_stage_gates_safe_errors_empty_and_restart(self):
        from fastapi.testclient import TestClient
        from webapp import create_app
        import time
        for capture_status,expected_stages,expected_status in [('incomplete_challenge',['collect'],'partial'),('complete_zero_ads',['collect'],'complete'),('complete',['collect','analyze'],'complete'),('throws',['collect'],'failed')]:
            stages=[]
            async def runner(stage,job):
                stages.append(stage)
                if capture_status=='throws': raise RuntimeError('SECRET_SYNTHETIC_NOT_FOR_UI')
                return {'status':capture_status if stage=='collect' else 'complete','ads':0}
            with tempfile.TemporaryDirectory() as d:
                s=Store(Path(d))
                with TestClient(create_app(s,job_runner=runner),base_url='http://localhost:5194') as c:
                    headers={'X-CSRF-Token':c.get('/api/bootstrap').json()['csrf_token']}
                    job=c.post('/api/jobs',json={'action':'collect_analyze','page_id':'9','paid_consent':True},headers=headers).json()
                    for _ in range(100):
                        job=c.get('/api/jobs/'+job['id']).json()
                        if job['status'] not in ('queued','running'): break
                        time.sleep(.01)
                    self.assertEqual(job['status'],expected_status); self.assertEqual(stages,expected_stages)
                    self.assertNotIn('SECRET_SYNTHETIC',str(job))
        with tempfile.TemporaryDirectory() as d:
            from webjobs import Jobs
            s=Store(Path(d)); Jobs(s)
            import json
            with s.connect() as conn: conn.execute('INSERT INTO web_jobs VALUES(?,?,?)',('interrupted','running',json.dumps({'id':'interrupted','status':'running'})))
            with TestClient(create_app(s,job_runner=runner),base_url='http://localhost:5194') as c:
                self.assertEqual(c.get('/api/jobs/current').json()['status'],'failed')

    def test_analyze_warns_about_incomplete_page_inventory(self):
        from fastapi.testclient import TestClient
        from webapp import create_app
        async def runner(stage,job): return {'status':'complete','calls':0}
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.set_meta('collection',{'status':'incomplete_stalled','page_id':'9'})
            with TestClient(create_app(s,job_runner=runner),base_url='http://localhost:5194') as c:
                headers={'X-CSRF-Token':c.get('/api/bootstrap').json()['csrf_token']}
                r=c.post('/api/jobs',json={'action':'analyze','page_id':'9','paid_consent':True},headers=headers)
                self.assertEqual(r.status_code,202); self.assertIn('incompleta',r.json()['warning'])

    def test_rejects_unsafe_requests_before_scheduling(self):
        from fastapi.testclient import TestClient
        from webapp import create_app
        async def forbidden(stage,job): self.fail('Invalid job was scheduled')
        with tempfile.TemporaryDirectory() as d:
            with TestClient(create_app(Store(Path(d)),job_runner=forbidden),base_url='http://localhost:5194') as c:
                valid={'action':'analyze','page_id':'9','budget':'0.4999','paid_consent':True}
                headers={'X-CSRF-Token':c.get('/api/bootstrap').json()['csrf_token']}
                self.assertEqual(c.post('/api/jobs',json=valid).status_code,403)
                self.assertEqual(c.post('/api/jobs',json=valid,headers={**headers,'Origin':'https://evil.invalid'}).status_code,403)
                self.assertEqual(c.post('/api/jobs',json=valid,headers={**headers,'Origin':'http://127.0.0.1:5194'}).status_code,403)
                self.assertEqual(c.post('/api/jobs',content='{}',headers=headers).status_code,415)
                for key,values in {'page_id':['9;ls','９','',9,'1'*31,'9\n'], 'action':['shell','',None], 'budget':['0','-.1','.5','NaN','Infinity',True,{},None], 'paid_consent':[False,'true',1,None]}.items():
                    for value in values:
                        response=c.post('/api/jobs',json={**valid,key:value},headers=headers)
                        self.assertEqual(response.status_code,422,(key,value,response.text))
                self.assertEqual(c.post('/api/jobs',json={**valid,'argv':['danger']},headers=headers).status_code,422)

    def test_async_job_lifecycle_and_persistence(self):
        from fastapi.testclient import TestClient
        from webapp import create_app
        import time, threading
        gate=threading.Event()
        async def runner(stage,job):
            await asyncio.to_thread(gate.wait,2)
            return {'status':'complete','ads':2,'page_id':job['page_id'],'synthetic':True}
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d))
            with TestClient(create_app(store,job_runner=runner),base_url='http://localhost:5194') as client:
                token=client.get('/api/bootstrap').json()['csrf_token']
                headers={'X-CSRF-Token':token}
                response=client.post('/api/jobs',json={'action':'collect','page_id':'9'},headers=headers)
                self.assertEqual(response.status_code,202,response.text)
                job=response.json(); self.assertEqual(job['status'],'queued')
                self.assertEqual(client.post('/api/jobs',json={'action':'collect','page_id':'8'},headers=headers).status_code,409)
                self.assertIn(client.get('/api/jobs/current').json()['status'],['queued','running'])
                gate.set()
                for _ in range(100):
                    job=client.get('/api/jobs/'+job['id']).json()
                    if job['status']=='complete': break
                    time.sleep(.01)
                self.assertEqual(job['status'],'complete'); self.assertTrue(job['finished_at'])
                self.assertEqual(job['results']['collect']['ads'],2)
            with TestClient(create_app(store,job_runner=runner),base_url='http://localhost:5194') as client:
                self.assertEqual(client.get('/api/jobs/'+job['id']).json()['status'],'complete')
