import unittest
from datetime import date
from unittest.mock import patch
from conference_catalog import recommend, supported

class CatalogTests(unittest.TestCase):
    def record(self, id, topic, start='2026-12-01'):
        return ({'id':id,'name':id,'start_date':start,'end_date':start,'city':'San Francisco','topics':[topic],'source_url':'https://example.com'}, {})
    def test_profiles_change_ranking(self):
        entries=[self.record('design','design'),self.record('data','data')]
        p={'city':'San Francisco','travel':'Nearby','interests':['Databases']}
        with patch('conference_catalog.records',return_value=entries),patch('conference_catalog.version',return_value='test'):
            self.assertEqual(recommend(p,date(2026,10,23))['matches'][0]['conference']['id'],'data')
            p['interests']=['Typography']
            self.assertEqual(recommend(p,date(2026,10,23))['matches'][0]['conference']['id'],'design')
            p['interests']=['Gardening']
            self.assertEqual(recommend(p,date(2026,10,23))['matches'],[])
    def test_geography_is_not_assumed(self):
        self.assertFalse(supported({'city':'New York','travel':'Nearby'}))
        self.assertFalse(supported({'city':'San Francisco','travel':'Online'}))
        self.assertTrue(supported({'city':'San Francisco, CA','travel':'Nearby'}))

    def test_six_matches_without_padding_unmatched_events(self):
        entries = [self.record(str(i), 'software') for i in range(8)]
        profile = {'city': 'San Francisco', 'travel': 'Nearby', 'interests': ['Software']}
        with patch('conference_catalog.records', return_value=entries), patch('conference_catalog.version', return_value='test'):
            matches = recommend(profile, date(2026, 10, 24))['matches']
            self.assertEqual(len(matches), 6)
            self.assertEqual([m['conference']['id'] for m in matches], list('012345'))
        with patch('conference_catalog.records', return_value=entries[:2]), patch('conference_catalog.version', return_value='test'):
            self.assertEqual(len(recommend(profile, date(2026, 10, 24))['matches']), 2)
