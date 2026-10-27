"""API do painel com a taxonomia de 7 dimensões. Dados sintéticos em diretório temporário; sem rede e sem cobrança."""
import json, tempfile, unittest
from pathlib import Path
from fastapi.testclient import TestClient
from labcore import Store, Ad
from inference import cache_key, RUBRIC_VERSION, LEGACY_RUBRIC_VERSION, MODEL


def labels(**choices):
    answers = {k: {'type': 'choice', 'choice': v, 'confidence': .9, 'probabilities': {v: 1.0}} for k, v in choices.items()}
    return {'model': MODEL, 'rubric_version': RUBRIC_VERSION, 'answers': answers, 'called_audience': None,
            'visual_callout': {'status': 'unavailable', 'text': None}, 'visual_evidence': 'still_only', 'needs_review': False}


def make(tmp, count=6):
    store = Store(Path(tmp))
    ads = [Ad(ad_id=f'S{i}', page_id='9', page_name='SYNTHETIC', copy=f'Pergunta {i}? Corpo do anúncio. Baixe o guia.',
              start_date='2026-01-01', media_ids=[f'm{i}']) for i in range(count)]
    store.put_ads(ads)
    store.set_meta('analysis', {'status': 'complete', 'model': MODEL, 'images': True, 'page_id': '9'})
    return store


class WebAdaptationTests(unittest.TestCase):
    def client(self, store):
        from webapp import create_app
        return TestClient(create_app(store), base_url='http://127.0.0.1:5194')

    def test_state_exposes_findings_taxonomy_and_label_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            store = make(d)
            for row in store.ads():
                store.cache_put(cache_key(row, MODEL, True), labels(format='talking_head', hook='curiosity', offer='free_resource',
                                                                    angle='education', proof='none', objection='none', cta='learn'))
            state = self.client(store).get('/api/state').json()
            self.assertEqual(state['taxonomy']['dimensions'], ['format', 'hook', 'angle', 'offer', 'proof', 'objection', 'cta'])
            self.assertEqual(state['taxonomy']['titles']['cta'], 'Chamada para ação')
            self.assertEqual(state['label_coverage'], {'v2': 6, 'legacy': 0, 'unlabeled': 0, 'total': 6})
            self.assertEqual(state['options']['angle'], [{'value': 'education', 'label': 'Aprendizado'}])
            fmt = next(f for f in state['findings'] if f['dimension'] == 'format')
            self.assertEqual(fmt['category'], 'talking_head')
            self.assertEqual(fmt['dated'], 6)
            self.assertEqual(len(state['metrics']['categories']), 7)

    def test_legacy_labels_are_shown_and_flagged_not_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            store = make(d, 3)
            for row in store.ads():
                legacy = labels(format='Talking head', hook='Direct', offer='Free resource')
                legacy['rubric_version'] = LEGACY_RUBRIC_VERSION
                store.cache_put(cache_key(row, MODEL, True, rubric=LEGACY_RUBRIC_VERSION), legacy)
            client = self.client(store)
            state = client.get('/api/state').json()
            self.assertEqual(state['label_coverage'], {'v2': 0, 'legacy': 3, 'unlabeled': 0, 'total': 3})
            self.assertEqual(state['metrics']['analyzed_ads'], 3)
            one = client.get('/api/ads/S0').json()
            self.assertTrue(one['labels']['legacy'])
            self.assertEqual(one['labels']['answers']['hook']['choice'], 'Direct')
            self.assertEqual(state['options']['hook'], [{'value': 'Direct', 'label': 'Direct'}])

    def test_v2_labels_win_over_legacy_for_the_same_creative(self):
        with tempfile.TemporaryDirectory() as d:
            store = make(d, 1)
            row = store.ads()[0]
            old = labels(hook='Direct'); old['rubric_version'] = LEGACY_RUBRIC_VERSION
            store.cache_put(cache_key(row, MODEL, True, rubric=LEGACY_RUBRIC_VERSION), old)
            store.cache_put(cache_key(row, MODEL, True), labels(hook='curiosity'))
            one = self.client(store).get('/api/ads/S0').json()
            self.assertFalse(one['labels'].get('legacy', False))
            self.assertEqual(one['labels']['answers']['hook']['choice'], 'curiosity')

    def test_filters_accept_every_dimension_and_combine(self):
        with tempfile.TemporaryDirectory() as d:
            store = make(d, 4)
            combos = [('education', 'learn'), ('education', 'buy'), ('trust', 'learn'), ('trust', 'buy')]
            for row, (angle, cta) in zip(store.ads(), combos):
                store.cache_put(cache_key(row, MODEL, True), labels(angle=angle, cta=cta))
            client = self.client(store)
            for dim in ('format', 'hook', 'angle', 'offer', 'proof', 'objection', 'cta'):
                self.assertEqual(client.get('/api/ads', params={dim: 'nao_existe'}).json()['total'], 0, dim)
            self.assertEqual(client.get('/api/ads', params={'angle': 'education'}).json()['total'], 2)
            self.assertEqual(client.get('/api/ads', params={'angle': 'education', 'cta': 'buy'}).json()['total'], 1)

    def test_ad_detail_includes_copy_breakdown_and_labels_in_portuguese(self):
        with tempfile.TemporaryDirectory() as d:
            store = make(d, 1)
            store.cache_put(cache_key(store.ads()[0], MODEL, True), labels(hook='curiosity', audience='None'))
            one = self.client(store).get('/api/ads/S0').json()
            roles = [s['role'] for s in one['copy_breakdown']['sections']]
            self.assertEqual(roles, ['Abertura', 'Corpo', 'Fechamento / chamada'])
            self.assertEqual(one['label_names']['hook'], 'Curiosidade')
            self.assertEqual(one['dimension_titles']['hook'], 'Gancho')
            self.assertEqual(one['dimension_titles']['audience'], 'Público citado')
            self.assertEqual(one['label_names'].get('audience'), 'nenhum trecho selecionado')

    def test_unlabeled_ads_do_not_break_state_or_findings(self):
        with tempfile.TemporaryDirectory() as d:
            store = make(d, 3)
            state = self.client(store).get('/api/state').json()
            self.assertEqual(state['findings'], [])
            self.assertEqual(state['label_coverage']['unlabeled'], 3)

    def test_state_is_json_serializable_and_has_no_remote_thumbnail_uri(self):
        with tempfile.TemporaryDirectory() as d:
            store = make(d, 1)
            payload = self.client(store).get('/api/ads').json()
            self.assertNotIn('thumbnail_url', json.dumps(payload))

    def test_cache_get_many_returns_only_existing_keys_in_one_pass(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d))
            store.cache_put('a', {'x': 1}); store.cache_put('b', {'x': 2})
            self.assertEqual(store.cache_get_many(['a', 'missing', 'b', 'a']), {'a': {'x': 1}, 'b': {'x': 2}})
            self.assertEqual(store.cache_get_many([]), {})
            many = [f'k{i}' for i in range(1200)]
            store.cache_put('k1199', {'ok': True})
            self.assertEqual(store.cache_get_many(many), {'k1199': {'ok': True}})


if __name__ == '__main__':
    unittest.main()
