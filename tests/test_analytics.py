import unittest
from datetime import date
class AnalyticsTests(unittest.TestCase):
    def test_individual_dates_unknowns_and_second_most_used_comparator(self):
        from analytics import statistics, landscape
        rows=[{'ad_id':'1','fingerprint':'same','start_date':'2026-01-01','active':True,'copy':'SYNTHETIC alpha','labels':{'answers':{'hook':{'choice':'Direct'}}}},
              {'ad_id':'2','fingerprint':'same','start_date':'2026-10-01','active':True,'copy':'SYNTHETIC alpha','labels':{'answers':{'hook':{'choice':'Direct'}}}},
              {'ad_id':'3','fingerprint':'other','start_date':None,'active':True,'copy':'SYNTHETIC beta','labels':{'answers':{'hook':{'choice':'Curiosity'}}}},
              {'ad_id':'4','fingerprint':'third','start_date':'2026-01-01','active':True,'copy':'SYNTHETIC beta','labels':{'answers':{'hook':{'choice':'Curiosity'}}}},
              {'ad_id':'5','fingerprint':'fourth','start_date':'2026-01-01','active':True,'copy':'SYNTHETIC gamma','labels':{'answers':{'hook':{'choice':'Frustration'}}}}]
        result=statistics(rows,today=date(2026,10,27))
        self.assertEqual(result['eligible_ads'],4); self.assertEqual(result['unknown_date_ads'],1)
        self.assertEqual(result['unique_creatives'],4); self.assertEqual(result['winner_proxy_ads'],3)
        cards=result['categories']['hook']; direct=next(x for x in cards if x['category']=='Direct')
        self.assertEqual(direct['comparator'],'Direct') # count tie sorted Curiosity then Direct
        self.assertEqual(direct['eligible_ads'],2); self.assertEqual(direct['winner_proxy_rate'],.5)
        curiosity=next(x for x in cards if x['category']=='Curiosity')
        self.assertEqual(curiosity['lift_pp'],50); self.assertEqual(curiosity['relative_lift'],1)
        points=landscape(rows)
        self.assertIn('TF-IDF',points['method']); self.assertEqual(len(points['points']),4)
        self.assertEqual(points,landscape(rows))
    def test_zero_denominator_is_unknown_not_winner(self):
        from analytics import statistics, days_active
        self.assertIsNone(days_active({'start_date':None}))
        self.assertIsNone(days_active({'start_date':'bad'}))
        result=statistics([{'ad_id':'x','fingerprint':'x','copy':'','active':True,'labels':{'answers':{'hook':{'choice':'Direct'}}}}])
        self.assertIsNone(result['categories']['hook'][0]['winner_proxy_rate'])
        self.assertIsNone(result['categories']['hook'][0]['relative_lift'])
