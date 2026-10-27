"""Taxonomia de sete dimensões e pedido nativo ao Jev (sem chamadas pagas)."""
import hashlib, json, unittest
from taxonomy import (DIMENSIONS, CATEGORIES, LABELS_PT, NEXT_TESTS, DIMENSION_TITLES, label_pt)


class TaxonomyTests(unittest.TestCase):
    def test_seven_dimensions_in_reference_order(self):
        self.assertEqual(DIMENSIONS, ('format', 'hook', 'angle', 'offer', 'proof', 'objection', 'cta'))
        self.assertEqual(set(CATEGORIES), set(DIMENSIONS))
        self.assertEqual(set(DIMENSION_TITLES), set(DIMENSIONS))

    def test_every_dimension_has_an_unknown_or_none_escape(self):
        for dim, options in CATEGORIES.items():
            self.assertIn('unknown', options, dim)

    def test_values_are_snake_case_and_have_portuguese_labels(self):
        for dim, options in CATEGORIES.items():
            for value, description in options.items():
                self.assertRegex(value, r'^[a-z]+(_[a-z]+)*$')
                self.assertTrue(description.strip())
                self.assertIn(value, LABELS_PT[dim], f'{dim}.{value} sem rótulo em português')
                self.assertTrue(LABELS_PT[dim][value].strip())

    def test_labels_have_no_extra_values(self):
        for dim in DIMENSIONS:
            self.assertEqual(set(LABELS_PT[dim]), set(CATEGORIES[dim]))

    def test_next_tests_cover_offer_hook_and_format_values(self):
        for dim in ('format', 'hook', 'offer'):
            for value in CATEGORIES[dim]:
                if value in ('unknown', 'mixed'):
                    continue
                self.assertIn(value, NEXT_TESTS, f'{dim}.{value} sem hipótese de teste')

    def test_label_pt_falls_back_for_legacy_values(self):
        self.assertEqual(label_pt('hook', 'curiosity'), 'Curiosidade')
        self.assertEqual(label_pt('hook', 'Proof / numbers'), 'Proof / numbers')
        self.assertEqual(label_pt('hook', None), 'Indefinido')


class RubricRequestTests(unittest.TestCase):
    def test_inference_uses_the_shared_taxonomy_and_new_rubric(self):
        import inference
        self.assertEqual(inference.RUBRIC_VERSION, '2.0.0')
        self.assertEqual(inference.CATEGORIES, CATEGORIES)

    def test_request_has_eight_choice_questions_per_ad_and_exact_criteria(self):
        from inference import build_request
        rows = [{'ad_id': 'a', 'copy': 'Chame designers. Checklist gratuito!'}, {'ad_id': 'b', 'copy': 'Outro texto.'}]
        body = build_request(rows, {}, 'jev-1.14.0')
        self.assertEqual(len(body['questions']), 2 * (len(DIMENSIONS) + 1))
        for i in range(2):
            for dim in DIMENSIONS:
                q = body['questions'][f'a{i}_{dim}']
                self.assertEqual(q['type'], 'choice')
                self.assertEqual(q['criteria'], CATEGORIES[dim])
            self.assertIn('None', body['questions'][f'a{i}_audience']['criteria'])

    def test_instructions_forbid_inferring_performance_and_unseen_content(self):
        from inference import build_request
        body = build_request([{'ad_id': 'a', 'copy': 'x'}], {}, 'jev-1.14.0')
        text = json.dumps(body['questions']['a0_hook']).lower()
        self.assertIn('untrusted', text)
        self.assertIn('performance', text)
        self.assertIn('unknown', text)
        self.assertIn('opening', text)

    def test_cache_key_isolated_by_rubric_and_legacy_key_is_reproducible(self):
        from inference import cache_key
        row = {'fingerprint': 'fp123'}
        legacy = hashlib.sha256(json.dumps(['fp123', 'jev-1.14.0', '1.0.0', True]).encode()).hexdigest()
        self.assertEqual(cache_key(row, 'jev-1.14.0', True, rubric='1.0.0'), legacy)
        self.assertNotEqual(cache_key(row, 'jev-1.14.0', True), legacy)
        new = hashlib.sha256(json.dumps(['fp123', 'jev-1.14.0', '2.0.0', True]).encode()).hexdigest()
        self.assertEqual(cache_key(row, 'jev-1.14.0', True), new)

    def test_validate_response_accepts_all_seven_dimensions(self):
        from inference import build_request, validate_response
        body = build_request([{'ad_id': 'a', 'copy': 'x'}], {}, 'jev-1.14.0')
        answers = {}
        for key, q in body['questions'].items():
            first = next(iter(q['criteria']))
            answers[key] = {'type': 'choice', 'choice': first, 'confidence': .9,
                            'probabilities': {label: float(label == first) for label in q['criteria']}}
        validate_response({'model': 'jev-1.14.0', 'answers': answers, 'usage': {'input_tokens': 10, 'output_tokens': 5}}, body)


if __name__ == '__main__':
    unittest.main()
