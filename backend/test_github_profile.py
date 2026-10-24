import unittest
from github_profile import canonical_url, normalize
from profile_service import cache_path

class GitHubProfileTests(unittest.TestCase):
    def test_links_and_cache_identity(self):
        self.assertEqual(canonical_url('github.com/JLevy'), 'https://github.com/jlevy')
        for url in ('https://github.com/a/repo','https://github.com/login','https://evil.com/a','https://github.com/a?x=1'):
            with self.assertRaises(ValueError): canonical_url(url)
        self.assertNotEqual(cache_path('li','x'),cache_path('li','x','https://github.com/a'))
        self.assertNotEqual(cache_path('li','x','https://github.com/a'),cache_path('li','x','https://github.com/b'))

    def test_attribution_and_forks(self):
        repo=dict(name='project',html_url='https://github.com/alex/project',owner={'login':'alex'},description='A tool')
        data={'profile':{'login':'alex','bio':'I build tools'},'repos':[repo,dict(repo,fork=True),dict(repo,private=True),dict(repo,owner={'login':'other'})],
              'events':[{'actor':{'login':'alex'},'type':'PullRequestEvent','payload':{'pull_request':{'user':{'login':'other'},'html_url':'https://github.com/test/pull/1'}}}]}
        evidence=normalize(data)
        self.assertEqual(len(evidence),2)
        self.assertIn('does not establish sole authorship',evidence[1]['text'])
