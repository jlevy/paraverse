import unittest
from profile_roles import current_roles, validate_public_role
from profile_service import normalize

class RoleTests(unittest.TestCase):
    def test_role_punctuation_and_identity(self):
        result={'title':'Co-Founder and CEO','company':'Example','quote':"Example's current Co-Founder/CEO is Alex Lee."}
        page={'text':"Example's current Co-Founder/CEO is Alex Lee .",'resolvedURL':'https://example.com/team','retrievedAt':'2026-10-23'}
        self.assertEqual(validate_public_role(result,page,'Alex Lee','Example')['title'],'Co-Founder and CEO at Example')
        self.assertIsNone(validate_public_role(result,page,'Other Person','Example'))
        self.assertIsNone(validate_public_role({**result,'title':'CTO'},page,'Alex Lee','Example'))
    def test_nested_current_role(self):
        record={'experience':[{'company':'Example','positions':[{'title':'Co-Founder/CEO','duration':'2021 - Present'},{'title':'Engineer','end_date':'2020'}]}]}
        self.assertEqual(current_roles(record)[0]['title'],'Co-Founder/CEO at Example')
        self.assertEqual(len(current_roles(record)),1)
    def test_no_inferred_current_role(self):
        self.assertEqual(current_roles({'experience':[{'title':'CEO','company':'Example'}]}),[])
    def test_company_without_title_does_not_invent_title(self):
        evidence=normalize([{'url':'https://www.linkedin.com/in/test','current_company':{'name':'Example'}}],[], 'https://www.linkedin.com/in/test')
        self.assertEqual(evidence[0]['kind'],'company')
        self.assertNotIn('CEO',evidence[0]['text'])
    def test_wrong_person_excluded(self):
        evidence=normalize([{'url':'https://www.linkedin.com/in/other','experience':[{'title':'CEO','company':'Example','end_date':'Present'}]}],[], 'https://www.linkedin.com/in/test')
        self.assertEqual(evidence,[])

if __name__=='__main__':unittest.main()
