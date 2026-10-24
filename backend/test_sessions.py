import unittest
from session_service import schedule,catalog
class SessionTests(unittest.TestCase):
 def setUp(self):
  self.rows=[dict(id='a',start='2026-10-28T10:00:00-07:00',end='2026-10-28T11:00:00-07:00'),dict(id='b',start='2026-10-28T10:30:00-07:00',end='2026-10-28T11:30:00-07:00'),dict(id='c',start='2026-10-29T15:00:00-07:00',end='2026-10-29T16:00:00-07:00')]
  self.rank=[dict(id=x,reason='Relevant') for x in ['bogus','a','a','b','c']]
 def test_unknown_duplicate_and_overlap_rejected(self):self.assertEqual([r['id'] for r in schedule(self.rank,self.rows)],['a','c'])
 def test_calendar_utc_conflict(self):self.assertEqual([r['id'] for r in schedule(self.rank,self.rows,[dict(start='2026-10-28T17:00:00Z',end='2026-10-28T19:00:00Z')])],['c'])
 def test_late_start(self):self.assertEqual([r['id'] for r in schedule(self.rank,self.rows,late=True)],['c'])
 def test_external_catalog_is_separate(self):
  external=catalog(True)
  self.assertTrue(external)
  self.assertTrue(all(r.get('sourceURL','').startswith('https://') for r in external))
  self.assertTrue(all(r['sourceURL'].startswith('https://luma.com/') for r in external if r['id'].startswith('luma:')))
  self.assertTrue(all('registrationStatus' in r for r in external))
 def test_real_catalog_has_both_days(self):self.assertEqual({r['start'][:10] for r in catalog()},{'2026-10-28','2026-10-29'})
if __name__=='__main__':unittest.main()

class RankingCacheTests(unittest.TestCase):
 def test_cache_reuse_and_live_calendar_filters(self):
  import tempfile,json
  from pathlib import Path
  from unittest.mock import patch
  import session_service as service
  rows=[dict(id='a',title='A',start='2026-10-28T10:00:00-07:00',end='2026-10-28T11:00:00-07:00'),dict(id='b',title='B',start='2026-10-28T16:00:00-07:00',end='2026-10-28T17:00:00-07:00')]
  ranked=[dict(id=x,reason='Fits the profile') for x in ['a','b']]
  response={'output':[{'content':[{'type':'output_text','text':json.dumps({'ranked':ranked})}]}]}
  with tempfile.TemporaryDirectory() as temp,patch.object(service,'ROOT',Path(temp)),patch.object(service,'catalog',return_value=rows),patch('profile_service.api',return_value=response) as api,patch.dict('os.environ',{'OPENAI_API_KEY':'test'}):
   (Path(temp)/'work').mkdir()
   body={'profile':{'title':'Engineer','interests':['AI'],'avatarURL':'first'},'prompt':'Recommend speaker sessions for both days'}
   first=service.recommend(body);self.assertFalse(first['rankingCacheHit'])
   body['profile']['avatarURL']='second';body['profile']['conferenceStates']={'universe-2026':'going'};body['prompt']='Recommend sessions'
   self.assertTrue(service.recommend(body)['rankingCacheHit']);self.assertEqual(api.call_count,1)
   body['prompt']='I can only arrive after 3 PM.'
   self.assertEqual([x['id'] for x in service.recommend(body)['sessions']],['b']);self.assertEqual(api.call_count,1)
   body['busy']=[dict(start='2026-10-28T16:00:00-07:00',end='2026-10-28T17:00:00-07:00')]
   self.assertEqual(service.recommend(body)['sessions'],[]);self.assertEqual(api.call_count,1)
   body['prompt']='Recommend database sessions'
   service.recommend(body);self.assertEqual(api.call_count,2)
   body['profile']['interests']=['Design'];service.recommend(body);self.assertEqual(api.call_count,3)
   rows[0]['title']='Updated agenda';service.recommend(body);self.assertEqual(api.call_count,4)


class ExternalSelectionTests(unittest.TestCase):
 def test_ten_options_spread_across_days_and_avoid_schedule(self):
  from session_service import select_external
  rows=[dict(id=f'{day}-{i}',start=f'2026-10-{day}T{10+i:02}:00:00-07:00',end=f'2026-10-{day}T{11+i:02}:00:00-07:00') for day in range(26,30) for i in range(4)]
  ranks=[dict(id=r['id'],reason='Specific fit') for r in rows]
  selected=select_external(ranks,rows,[dict(start='2026-10-26T10:00:00-07:00',end='2026-10-26T11:00:00-07:00')])
  self.assertEqual(len(selected),10)
  self.assertEqual(len({r['start'][:10] for r in selected}),4)
  self.assertNotIn('26-0',[r['id'] for r in selected])
  self.assertEqual(len({r['id'] for r in selected}),10)
