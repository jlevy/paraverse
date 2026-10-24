import unittest
from profile_service import normalize, validate, profile_url, PROMPT
class ProfileTests(unittest.TestCase):
    def test_arbitrary_account_and_attribution(self):
        posts=[dict(user_posted='anotherperson',description='I love hiking',url='https://x.com/anotherperson/status/1'),dict(user_posted='someoneelse',description='I love jazz',url='https://x.com/someoneelse/status/2')]
        evidence=normalize([],posts,x_url='https://x.com/anotherperson')
        self.assertEqual(len(evidence),1)
        self.assertEqual(evidence[0]['text'],'I love hiking')
    def test_no_likes_or_reposts(self):
        li=[dict(url='https://linkedin.com/in/test',activity=[dict(interaction='Test liked this',title='My favorite band',link='https://linkedin.com/posts/1')])]
        self.assertEqual(normalize(li,[dict(user_posted='test',is_repost=True,description='My hobby',url='https://x.com/test/status/1')]),[])
    def test_evidence_rejects_invented_quotes_and_sources(self):
        evidence=[dict(id='e1',text='I love hiking',url='https://x.com/person/status/1')]
        item=dict(label='Hiking',category='personal',confidence='high',reason='Explicit preference',evidence=[dict(id='e1',quote='I love hiking')])
        result=dict(title=None,background='',interests=[item])
        self.assertEqual(len(validate(result,evidence)['interests']),1)
        item['evidence'][0]['quote']='I love swimming'
        self.assertEqual(validate(result,evidence)['interests'],[])
        item['evidence'][0]=dict(id='invented',quote='I love hiking')
        self.assertEqual(validate(result,evidence)['interests'],[])
    def test_medium_requires_multiple_sources(self):
        result=dict(title=None,background='',interests=[dict(label='Hiking',category='personal',confidence='medium',reason='Mentioned',evidence=[dict(id='e1',quote='hiking')])])
        self.assertEqual(validate(result,[dict(id='e1',text='hiking',url='https://x.com/p/status/1')])['interests'],[])
    def test_prompt_has_no_test_person_or_suggested_hobbies(self):
        for word in ['sam','radiohead','basketball','planetscale']:self.assertNotIn(word,PROMPT.lower())
    def test_unsupported_title_is_rejected(self):
        with self.assertRaises(ValueError):
            validate(dict(title='Invented title',titleEvidence=[],background='',interests=[]),[])
    def test_raw_sam_sample_normalizes_without_invented_hobbies(self):
        import json
        from pathlib import Path
        source=Path(__file__).resolve().parents[1]/'work/data/profiles/sam-lambert/x-brightdata-100.json'
        records=json.loads(source.read_text())
        evidence=normalize([],records,x_url='https://x.com/samlambert')
        self.assertGreater(len(evidence),50)
        self.assertTrue(all(e['url'].startswith('https://x.com/samlambert') for e in evidence))
        self.assertTrue(any('CEO @PlanetScale' in e['text'] for e in evidence))
    def test_url_validation(self):
        self.assertEqual(profile_url('https://x.com/someone/','x'),'https://x.com/someone')
        for url in ['http://x.com/a','https://evil.com/a','https://x.com/a/status/1','https://x.com/a?q=x','https://x.com:443/a']:
            with self.assertRaises(ValueError):profile_url(url,'x')
if __name__=='__main__':unittest.main()
