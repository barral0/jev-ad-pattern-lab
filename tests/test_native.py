import unittest, tempfile, asyncio, json
from pathlib import Path
from labcore import Store, Ad
class NativeTests(unittest.TestCase):
    def test_native_batch_validation_and_resume_cache(self):
        from inference import analyze, build_request, validate_response, cache_key
        ad=Ad(ad_id='synthetic1',page_id='9',copy='Calling all designers. Free checklist!',media_ids=['m1'])
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)); s.put_ads([ad]); row=s.ads()[0]
            request=build_request([row],{},'jev-1.14.0')
            self.assertEqual(request['model'],'jev-1.14.0')
            self.assertTrue(all(q['type']=='choice' for q in request['questions'].values()))
            answer={k:{'type':'choice','choice':next(iter(q['criteria'])),'confidence':0.4,'probabilities':{label:float(i==0) for i,label in enumerate(q['criteria'])}} for k,q in request['questions'].items()}
            raw={'model':'jev-1.14.0','answers':answer,'usage':{'input_tokens':400,'output_tokens':60}}
            validate_response(raw,request)
            bad=json.loads(json.dumps(raw)); next(iter(bad['answers'].values()))['confidence']=2
            with self.assertRaises(ValueError): validate_response(bad,request)
            calls=[]
            async def transport(body): calls.append(body); return raw
            report=asyncio.run(analyze(s,api_key='SYNTHETIC-test-not-a-key',transport=transport,images=False))
            self.assertEqual(report['analyzed_ads'],1); self.assertEqual(len(calls),1)
            report=asyncio.run(analyze(s,api_key='SYNTHETIC-test-not-a-key',transport=transport,images=False))
            self.assertEqual(len(calls),1)
            self.assertTrue(s.cache_get(cache_key(row,'jev-1.14.0',False))['needs_review'])
    def test_image_reference_once_and_candidate_coverage(self):
        from inference import build_request
        row={'ad_id':'a','copy':'Hey doctors. Get your free resource.'}
        body=build_request([row],{'a':b'bytes'},'jev-1.14.0')
        self.assertEqual(len(body['assets']),1)
        ref=next(iter(body['assets']))
        self.assertEqual(json.dumps(body['state']).count(ref),1)
        audience=body['questions']['a0_audience']['criteria']
        self.assertIn('None',audience)
        self.assertTrue(all(v in row['copy'] for k,v in audience.items() if k!='None'))
    def test_missing_key_stops_without_reservation(self):
        from inference import analyze
        import os
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d))
            with self.assertRaises(ValueError): asyncio.run(analyze(s,api_key=''))
            with s.connect() as c: self.assertEqual(c.execute('select count(*) from charges').fetchone()[0],0)
