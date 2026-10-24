import copy,unittest
from datetime import date
from unittest.mock import patch
from conference_service import validate_events,clean_profile,cache_key,public_url
class ConferenceTests(unittest.TestCase):
    def setUp(self):
        self.p=clean_profile({'city':'San Francisco','travel':'Nearby','interests':['Databases']})
        self.sources=[{'id':'s1','url':'https://example.com','resolvedURL':'https://example.com','title':'Event','text':'November 1, 2026 in San Francisco. Database reliability. Online. $50.'}]
        self.event={'sourceID':'s1','title':'Conference','start':'2026-11-01','end':'2026-11-01','city':'San Francisco','venue':'SF','price':'$50','online':False,'nearby':True,'program':'Database reliability','matchedInterests':['Databases'],'reason':'Database reliability fits your interests.','proofs':[{'field':'dates','quote':'November 1, 2026'},{'field':'location','quote':'San Francisco'},{'field':'program','quote':'Database reliability.'}]}
    def check(self,event=None,p=None):return validate_events({'events':[event or self.event]},self.sources,p or self.p,date(2026,10,23))[0]
    def test_valid_evidence_and_unknown_price(self):
        result=self.check();self.assertEqual(len(result),1)
        self.assertEqual(result[0]['conference']['price'],'See registration for pricing')
    def test_invented_quote_and_missing_source_rejected(self):
        self.event['proofs'][0]['quote']='December 1, 2026';self.assertEqual(self.check(),[])
        self.event['sourceID']='invented';self.assertEqual(self.check(),[])
    def test_past_and_out_of_range_events_rejected(self):
        self.event['start']='2026-10-01';self.assertEqual(self.check(),[])
        self.event['start']=self.event['end']='2027-12-01';self.assertEqual(self.check(),[])
    def test_attendance_and_profile_constraints(self):
        self.event['nearby']=False;self.assertEqual(self.check(),[])
        self.p['travel']='Online';self.assertEqual(self.check(),[])
        self.p['travel']='Open to travel';self.assertEqual(len(self.check()),1)
        self.p['interests']=['Gardening'];self.assertEqual(self.check(),[])
    def test_cache_changes_with_profile_not_name(self):
        p=copy.deepcopy(self.p);p['interests']=['Design'];self.assertNotEqual(cache_key(p),cache_key(self.p))
        p=copy.deepcopy(self.p);p['travel']='Online';self.assertNotEqual(cache_key(p),cache_key(self.p))
        self.assertEqual(clean_profile({**self.p,'name':'Other'}),self.p)
    def test_private_source_blocked(self):
        with patch('conference_service.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError):public_url('https://example.com')
        with self.assertRaises(ValueError):public_url('file:///etc/passwd')
if __name__=='__main__':unittest.main()
