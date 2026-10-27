import unittest, json
class CaptureTests(unittest.TestCase):
    def test_graphql_collation_scopes_active_page_and_pagination(self):
        from collector import parse_capture
        payload={'data':{'ad_library_main':{'edges':[{'node':{'collated_results':[
          {'ad_archive_id':'11','page_id':'9','is_active':True,'start_date':1700000000,'snapshot':{'body':{'text':'SYNTHETIC copy'},'videos':[{'video_preview_image_url':'https://scontent.xx.fbcdn.net/a.jpg','video_hd_url':'DO-NOT-SAVE','video_id':'v1'}]}},
          {'ad_archive_id':'12','page_id':'8','is_active':True}, {'ad_archive_id':'13','page_id':'9','is_active':False} ]}}], 'page_info':{'has_next_page':False,'end_cursor':None}}}}
        result=parse_capture('for (;;);'+json.dumps(payload)+'\n'+json.dumps({'extensions':{}}),'9')
        self.assertEqual([a.ad_id for a in result['ads']],['11'])
        self.assertEqual(result['pagination'],[{'has_next_page':False,'end_cursor':None}])
        self.assertNotIn('DO-NOT-SAVE',result['ads'][0].model_dump_json())
        self.assertEqual(result['ads'][0].media_ids,['v1'])
    def test_empty_is_not_trusted_termination(self):
        from collector import parse_capture, collection_status
        self.assertEqual(collection_status(parse_capture('{}','9'),False),'incomplete_stalled')
        self.assertEqual(collection_status({'ads':[],'pagination':[{'has_next_page':False}]},False),'complete_zero_ads')
        self.assertEqual(collection_status({'ads':[],'pagination':[{'has_next_page':False}]},True),'incomplete_challenge')
