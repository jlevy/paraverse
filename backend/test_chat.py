import unittest
from chat_service import explicit_action
class ChatIntentTests(unittest.TestCase):
 def test_questions_never_take_fast_planning_path(self):
  for text in ['Who should I meet?','Who else is going?','What events are around automating workflows?','Why did you pick these for me?','What is on my calendar?','Hello']:
   self.assertIsNone(explicit_action(text))
 def test_explicit_plan_requests(self):
  self.assertEqual(explicit_action('Plan my sessions'),'plan_sessions')
  self.assertEqual(explicit_action('I can only arrive after 3 PM.'),'plan_sessions')

class RecommendationCardTests(unittest.TestCase):
 def test_only_known_people_and_authoritative_identity(self):
  from chat_service import hydrate_recommendations
  records=[{'id':'a','name':'Actual name','role':'Engineer','profile_url':'https://x.com/a','source_url':'https://x.com/a/status/1','avatar_asset':'attendee-a','linkedin_url':'https://www.linkedin.com/in/a','github_url':'https://github.com/a'}]
  result=hydrate_recommendations([{'personID':'unknown','reason':'Invented'},{'personID':'a','reason':'Shared interests','name':'Fake'},{'personID':'a','reason':'Duplicate'}],records)
  self.assertEqual(len(result),1)
  self.assertEqual(result[0]['name'],'Actual name')
  self.assertEqual(result[0]['avatarAsset'],'attendee-a')

  self.assertEqual(result[0]['linkedinURL'],'https://www.linkedin.com/in/a')
  self.assertEqual(result[0]['xURL'],'https://x.com/a')
  self.assertEqual(result[0]['githubURL'],'https://github.com/a')

class MixedPeopleTests(unittest.TestCase):
 def test_pool_includes_speakers_and_deduplicates_names(self):
  from chat_service import recommendation_people
  rows=recommendation_people()
  self.assertTrue(any(p['kind']=='speaker' for p in rows))
  self.assertTrue(any(p['kind']=='attendee' for p in rows))
  self.assertEqual(len(rows),len({p['name'].strip().casefold() for p in rows}))
 def test_ten_people_are_not_truncated_to_three(self):
  from chat_service import hydrate_recommendations
  rows=[dict(id=str(i),name=str(i),profile_url='https://example.com/profile',source_url='https://example.com/source') for i in range(12)]
  result=hydrate_recommendations([dict(personID=str(i),reason='Specific shared interest') for i in range(12)],rows)
  self.assertEqual(len(result),12)
  self.assertIsNone(result[0]['xURL'])

class BundledProfileTests(unittest.TestCase):
 def test_missing_local_enrichment_preserves_bundled_fields(self):
  import json,tempfile
  from pathlib import Path
  from unittest.mock import patch
  import attendee_graph
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory); assets=root/'native/Assets';assets.mkdir(parents=True)
   bundled=dict(username='example',name='Example',about='Public professional biography',interests=[{'label':'Developer tools'}],linkedin_url='https://www.linkedin.com/in/example')
   (assets/'universe-attendees.json').write_text(json.dumps([bundled]))
   with patch.object(attendee_graph,'ROOT',root): rows=attendee_graph.people()
  self.assertEqual(rows[0]['about'],bundled['about'])
  self.assertEqual(rows[0]['interests'],bundled['interests'])
  self.assertEqual(rows[0]['linkedin_url'],bundled['linkedin_url'])

class ChatCacheTests(unittest.TestCase):
 def test_interrupted_cache_is_regenerated(self):
  import json, tempfile
  from pathlib import Path
  from unittest.mock import patch
  import chat_service
  result=dict(action='answer', message='A bounded answer', personIDs=[], sessionIDs=[], recommendations=[])
  response=dict(status='completed', output=[dict(content=[dict(type='output_text', text=json.dumps(result))])])
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory); (root/'work').mkdir()
   with patch.object(chat_service,'ROOT',root), patch.object(chat_service,'recommendation_people',return_value=[]), patch.object(chat_service,'lookup',return_value=[]), patch.object(chat_service,'catalog',return_value=[]), patch.object(chat_service,'api',return_value=response) as api, patch.dict('os.environ',{'OPENAI_API_KEY':'synthetic-test-key'}):
    self.assertEqual(chat_service.answer(dict(prompt='Which sessions?',profile={})),result)
    file=next((root/'work/chat-answers').glob('*.json'));file.write_text('{"action":')
    self.assertEqual(chat_service.answer(dict(prompt='Which sessions?',profile={})),result)
    file.write_text('[]')
    self.assertEqual(chat_service.answer(dict(prompt='Which sessions?',profile={})),result)
    file.write_text(json.dumps(dict(result,recommendations=[dict(personID='known',reason='Missing authoritative identity fields')])))
    self.assertEqual(chat_service.answer(dict(prompt='Which sessions?',profile={})),result)
    for action in ([], {}):
     with self.subTest(action=type(action).__name__):
      file.write_text(json.dumps(dict(result,action=action)))
      self.assertEqual(chat_service.answer(dict(prompt='Which sessions?',profile={})),result)
    recommendation=dict(personID='known',reason='Shared interest',name='Example',role='Engineer',profileURL='https://example.com/profile',sourceURL='https://example.com/source')
    for key in ('avatarAsset','linkedinURL','xURL','githubURL'):
     with self.subTest(optional=key):
      file.write_text(json.dumps(dict(result,recommendations=[dict(recommendation,**{key:42})])))
      self.assertEqual(chat_service.answer(dict(prompt='Which sessions?',profile={})),result)
    self.assertEqual(api.call_count,10)
    for optional in ({},{'avatarAsset':None,'linkedinURL':None,'xURL':None,'githubURL':None},{'avatarAsset':'example','linkedinURL':'https://example.com/in/example','xURL':'https://example.com/example','githubURL':'https://example.com/example'}):
     cached=dict(result,recommendations=[dict(recommendation,**optional)])
     file.write_text(json.dumps(cached))
     self.assertEqual(chat_service.answer(dict(prompt='Which sessions?',profile={})),cached)
    self.assertEqual(api.call_count,10)

 def test_concurrent_publications_never_expose_partial_json(self):
  import tempfile, threading
  from pathlib import Path
  import chat_service
  with tempfile.TemporaryDirectory() as directory:
   file=Path(directory)/'answer.json'
   results=[dict(action='answer',message=str(i)*10000,personIDs=[],sessionIDs=[],recommendations=[]) for i in range(2)]
   chat_service.publish_cache(file,results[0])
   failures=[]
   def write(result):
    for _ in range(30):chat_service.publish_cache(file,result)
   threads=[threading.Thread(target=write,args=(r,)) for r in results]
   for thread in threads:thread.start()
   while any(thread.is_alive() for thread in threads):
    value=chat_service.read_cache(file)
    if value not in results:failures.append(value)
   for thread in threads:thread.join()
   self.assertEqual(failures,[])
   self.assertEqual(list(Path(directory).iterdir()),[file])

class ConferenceScopeTests(unittest.TestCase):
 def test_universe_recommendations_exclude_other_event_participants(self):
  import json,tempfile
  from pathlib import Path
  from unittest.mock import patch
  import chat_service
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);assets=root/'native/Assets';assets.mkdir(parents=True)
   common=dict(name='Example',role='Engineer',company='',biography='',sourceURL='https://example.com/source',sessions=[],participationRoles=['speaker'])
   universe=dict(common,id='universe',eventID='event:github-universe-2026')
   other=dict(common,id='ptc',eventID='event:patch-the-conference-2026',participationRoles=['judge'])
   (assets/'kb-native-manifest.json').write_text('{}')
   (assets/'world-speakers.json').write_text(json.dumps([universe,other]))
   (assets/'ptc-judges.json').write_text(json.dumps([other]))
   with patch.object(chat_service,'ROOT',root):records=chat_service.recommendation_people()
  self.assertEqual([p['id'] for p in records],['universe'])
  self.assertEqual(chat_service.hydrate_recommendations([dict(personID='ptc',reason='Invented attendance')],records),[])


class AttendanceEvidenceTests(unittest.TestCase):
 def test_native_attendee_evidence_joins_by_kb_id_and_stays_separate_from_biography(self):
  import json,tempfile
  from pathlib import Path
  from unittest.mock import patch
  import chat_service
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);assets=root/'native/Assets';assets.mkdir(parents=True)
   person=dict(id='legacy-person',kbID='person:example',name='Example',eventID='event:github-universe-2026',role='Attendee',company='',biography='',biographyProvenance={'source':'https://example.org/bio'},sourceURL='https://example.org/profile',sessions=[],participationRoles=['attendee'],attendee=True)
   proof=dict(id='person:example',kbID='person:example',evidence='I am attending the conference.',source_url='https://example.org/attendance-post',evidence_sources=[dict(url='https://example.org/attendance-post',quote='I am attending the conference.')])
   (assets/'kb-native-manifest.json').write_text('{}')
   (assets/'world-speakers.json').write_text(json.dumps([person]))
   (assets/'kb-attendees.json').write_text(json.dumps([proof]))
   with patch.object(chat_service,'ROOT',root): rows=chat_service.recommendation_people()
  self.assertEqual(rows[0]['evidence'],proof['evidence'])
  self.assertEqual(rows[0]['source_url'],proof['source_url'])
  self.assertEqual(rows[0]['biography_provenance'],person['biographyProvenance'])
  self.assertEqual(rows[0]['evidence_sources'],proof['evidence_sources'])
  self.assertEqual(rows[0]['about'],'')

 def test_mixed_speaker_and_attendee_keeps_self_report_proof(self):
  import json,tempfile
  from pathlib import Path
  from unittest.mock import patch
  import chat_service
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);assets=root/'native/Assets';assets.mkdir(parents=True)
   person=dict(id='legacy-person',kbID='person:example',name='Example',eventID='event:github-universe-2026',role='Attendee',company='',biography='',biographyProvenance={'source':'https://example.org/bio'},sourceURL='https://example.org/profile',sessions=[],participationRoles=['attendee','speaker'],attendee=False)
   proof=dict(id='person:example',kbID='person:example',evidence='I am attending the conference.',source_url='https://example.org/attendance-post',evidence_sources=[dict(url='https://example.org/attendance-post',quote='I am attending the conference.')])
   (assets/'kb-native-manifest.json').write_text('{}')
   (assets/'world-speakers.json').write_text(json.dumps([person]))
   (assets/'kb-attendees.json').write_text(json.dumps([proof]))
   with patch.object(chat_service,'ROOT',root): rows=chat_service.recommendation_people()
  self.assertEqual(rows[0]['evidence'],proof['evidence'])
  self.assertEqual(rows[0]['source_url'],proof['source_url'])
  self.assertEqual(rows[0]['biography_provenance'],person['biographyProvenance'])
  self.assertEqual(rows[0]['evidence_sources'],proof['evidence_sources'])
  self.assertEqual(rows[0]['about'],'')
  self.assertIn('Public self-report',rows[0]['attendance_status'])
  self.assertIn('speaker',rows[0]['attendance_status'])
