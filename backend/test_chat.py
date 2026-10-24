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
