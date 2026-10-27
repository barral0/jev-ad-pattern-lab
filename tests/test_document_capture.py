"""Embedded-document capture. All payloads here are SYNTHETIC fixtures, never live data."""
import json, unittest

from collector import parse_capture, parse_document, collection_status


def ad(ad_id, page_id='999'):
    return {'ad_archive_id': ad_id, 'page_id': page_id, 'page_name': 'Synthetic Page', 'is_active': True,
            'start_date': 1760000000, 'snapshot': {'body': {'text': 'synthetic copy ' + ad_id},
                                                  'images': [{'original_image_url': 'https://scontent.xx.fbcdn.net/a.jpg'}]}}


def script(payload):
    return '<script type="application/json" nonce="x" data-sjs>' + json.dumps(payload) + '</script>'


def listing(ads, has_next):
    return {'require': [['ScheduledServerJS', 'handle', None, [{'__bbox': {'result': {'data': {
        'ad_library_main': {'search_results_connection': {
            'count': len(ads),
            'edges': [{'node': {'collated_results': ads}}],
            'page_info': {'has_next_page': has_next, 'end_cursor': None if not has_next else 'abc'}}}}}}}]]]}


class DocumentCaptureTests(unittest.TestCase):
    def test_ads_embedded_in_html_document_are_captured(self):
        html = '<html><head>' + script({'unrelated': 1}) + script(listing([ad('111'), ad('222')], False)) + '</head></html>'
        parsed = parse_document(html, '999')
        self.assertEqual({a.ad_id for a in parsed['ads']}, {'111', '222'})
        self.assertEqual(collection_status(parsed), 'complete')

    def test_graphql_text_parser_ignores_html_so_documents_need_their_own_path(self):
        html = '<html>' + script(listing([ad('111')], False)) + '</html>'
        self.assertEqual(parse_capture(html, '999')['ads'], [])

    def test_other_pages_in_document_are_not_captured(self):
        html = script(listing([ad('111'), ad('333', page_id='123')], False))
        self.assertEqual([a.ad_id for a in parse_document(html, '999')['ads']], ['111'])

    def test_document_with_next_page_is_not_complete(self):
        parsed = parse_document(script(listing([ad('111')], True)), '999')
        self.assertEqual(collection_status(parsed), 'incomplete_stalled')

    def test_invalid_script_blocks_do_not_break_other_blocks(self):
        html = '<script type="application/json" data-sjs>{broken</script>' + script(listing([ad('111')], False))
        self.assertEqual([a.ad_id for a in parse_document(html, '999')['ads']], ['111'])

    def test_non_json_scripts_are_ignored(self):
        html = '<script>var x = "ad_archive_id";</script>' + script(listing([ad('111')], False))
        self.assertEqual([a.ad_id for a in parse_document(html, '999')['ads']], ['111'])


if __name__ == '__main__':
    unittest.main()
