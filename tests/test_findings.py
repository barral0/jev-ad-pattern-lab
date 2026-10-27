"""Achados, exemplos e quebra de copy. Dados sintéticos; sem rede e sem chamadas pagas."""
import unittest
from datetime import date

TODAY = date(2026, 10, 27)
OLD, NEW = '2026-06-01', '2026-10-10'   # 148 dias e 17 dias antes de TODAY


def ad(i, fingerprint=None, start=OLD, labels=None, active=True, copy='copy'):
    answers = {k: {'type': 'choice', 'choice': v, 'confidence': .9, 'probabilities': {v: 1.0}}
               for k, v in (labels or {}).items()}
    return {'ad_id': str(i), 'fingerprint': fingerprint or f'fp{i}', 'start_date': start, 'active': active,
            'copy': copy, 'labels': {'answers': answers, 'needs_review': False} if answers else None}


def dataset():
    rows = []
    # talking_head: 6 anúncios, 5 com 60+ dias (83,3%)
    for i in range(5):
        rows.append(ad(i, start=OLD, labels={'format': 'talking_head', 'hook': 'curiosity', 'offer': 'free_resource'}))
    rows.append(ad(5, start=NEW, labels={'format': 'talking_head', 'hook': 'direct', 'offer': 'free_resource'}))
    # graphic: 6 anúncios, 1 com 60+ dias (16,7%)
    rows.append(ad(6, start=OLD, labels={'format': 'graphic', 'hook': 'direct', 'offer': 'discount'}))
    for i in range(7, 12):
        rows.append(ad(i, start=NEW, labels={'format': 'graphic', 'hook': 'direct', 'offer': 'discount'}))
    # grupo pequeno com 100%, abaixo do mínimo
    rows.append(ad(12, start=OLD, labels={'format': 'founder', 'hook': 'mistake', 'offer': 'course'}))
    return rows


class FindingsTests(unittest.TestCase):
    def test_top_group_baseline_lift_and_minimum_group_size(self):
        from analytics import findings
        result = findings(dataset(), today=TODAY)
        fmt = next(f for f in result if f['dimension'] == 'format')
        self.assertEqual(fmt['category'], 'talking_head')       # 'founder' (100%) fica abaixo do mínimo de 5
        self.assertEqual(fmt['minimum_group_size'], 5)
        self.assertEqual((fmt['old'], fmt['dated'], fmt['n']), (5, 6, 6))
        self.assertAlmostEqual(fmt['share'], 5 / 6)
        self.assertAlmostEqual(fmt['baseline'], 7 / 13)           # 6 + 1 + 0 de 13 anúncios datados
        self.assertAlmostEqual(fmt['lift'], (5 / 6) / (7 / 13))
        self.assertEqual(fmt['label'], 'Pessoa falando à câmera')
        self.assertEqual(fmt['comparison']['category'], 'graphic')
        self.assertEqual(len(fmt['example_ids']), 4)

    def test_facets_use_only_older_ads_and_skip_unknown(self):
        from analytics import findings
        fmt = next(f for f in findings(dataset(), today=TODAY) if f['dimension'] == 'format')
        facets = {f['dimension']: f for f in fmt['facets']}
        self.assertEqual(facets['hook']['category'], 'curiosity')
        self.assertEqual((facets['hook']['n'], facets['hook']['total']), (5, 5))
        self.assertEqual(facets['offer']['category'], 'free_resource')

    def test_texts_are_portuguese_and_make_no_performance_claim(self):
        from analytics import findings
        fmt = next(f for f in findings(dataset(), today=TODAY) if f['dimension'] == 'format')
        self.assertIn('60+ dias', fmt['heading'])
        self.assertIn('5 de 6', fmt['observation'])
        self.assertTrue(fmt['next_test'].startswith('Abra com um problema'))
        blob = (fmt['heading'] + fmt['observation'] + fmt['next_test']).lower()
        for banned in ('roas', 'vendas', 'lucro', 'converte'):
            self.assertNotIn(banned, blob)

    def test_unknown_and_unlabeled_ads_are_not_ranked(self):
        from analytics import findings
        rows = [ad(i, labels={'format': 'unknown'}) for i in range(8)] + [ad(20 + i) for i in range(8)]
        self.assertEqual([f for f in findings(rows, today=TODAY) if f['dimension'] == 'format'], [])

    def test_ads_without_dates_do_not_enter_the_denominator(self):
        from analytics import findings
        rows = [ad(i, start=None, labels={'format': 'product'}) for i in range(10)]
        self.assertEqual(findings(rows, today=TODAY), [])

    def test_inactive_ads_are_ignored(self):
        from analytics import findings
        rows = [ad(i, active=False, labels={'format': 'product'}) for i in range(10)]
        self.assertEqual(findings(rows, today=TODAY), [])

    def test_legacy_title_case_labels_still_group_without_a_next_test(self):
        from analytics import findings
        rows = [ad(i, labels={'hook': 'Proof / numbers'}) for i in range(6)]
        hook = next(f for f in findings(rows, today=TODAY) if f['dimension'] == 'hook')
        self.assertEqual(hook['category'], 'Proof / numbers')
        self.assertEqual(hook['label'], 'Proof / numbers')
        self.assertIn('não tem uma hipótese pronta', hook['next_test'])


class ExamplesTests(unittest.TestCase):
    def test_distinct_families_come_first_then_repeats_each_oldest_first(self):
        from analytics import pattern_examples
        rows = [ad('a1', 'famA', OLD, {'format': 'product'}), ad('a2', 'famA', '2026-07-01', {'format': 'product'}),
                ad('b1', 'famB', '2026-09-01', {'format': 'product'}), ad('c1', 'famC', NEW, {'format': 'graphic'})]
        ids = [r['ad_id'] for r in pattern_examples(rows, 'format', 'product', today=TODAY)]
        self.assertEqual(ids, ['a1', 'b1', 'a2'])

    def test_older_only_requires_60_days_and_active(self):
        from analytics import pattern_examples
        rows = [ad('o', start=OLD, labels={'format': 'product'}), ad('n', start=NEW, labels={'format': 'product'})]
        self.assertEqual([r['ad_id'] for r in pattern_examples(rows, 'format', 'product', older_only=True, today=TODAY)], ['o'])


class CopyBreakdownTests(unittest.TestCase):
    def test_sections_preserve_saved_words(self):
        from analytics import copy_breakdown
        text = 'Cansado de planilhas? Organize tudo no Notion em um só lugar.\n\nBaixe o checklist gratuito agora.'
        result = copy_breakdown(text)
        self.assertEqual(result['source'], 'Texto salvo do anúncio')
        self.assertEqual([s['role'] for s in result['sections']], ['Abertura', 'Corpo', 'Fechamento / chamada'])
        self.assertEqual(result['sections'][0]['text'], 'Cansado de planilhas?')
        self.assertTrue(result['sections'][2]['text'].startswith('Baixe'))
        self.assertEqual(' '.join(s['text'] for s in result['sections']).split(), text.split())

    def test_transcript_has_priority_and_is_named(self):
        from analytics import copy_breakdown
        self.assertEqual(copy_breakdown('texto', transcript='fala gravada. Mais.')['source'], 'Transcrição da fala')

    def test_empty_copy_has_no_sections(self):
        from analytics import copy_breakdown
        self.assertEqual(copy_breakdown('  ')['sections'], [])

    def test_copy_without_call_to_action_has_no_closing_section(self):
        from analytics import copy_breakdown
        roles = [s['role'] for s in copy_breakdown('Frase um. Frase dois sem pedido.')['sections']]
        self.assertNotIn('Fechamento / chamada', roles)


class StatisticsDimensionTests(unittest.TestCase):
    def test_statistics_covers_all_seven_dimensions(self):
        from analytics import statistics
        from taxonomy import DIMENSIONS
        result = statistics(dataset(), today=TODAY)
        self.assertEqual(tuple(result['categories']), DIMENSIONS)
        self.assertEqual(result['categories']['angle'], [])
        self.assertEqual(result['categories']['format'][0]['category'], 'graphic')  # 6 = 6; desempate alfabético


if __name__ == '__main__':
    unittest.main()
