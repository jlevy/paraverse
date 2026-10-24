import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import luma_service

class InvitationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.folder=Path(self.tmp.name);self.id='a'*32
  (self.folder/(self.id+'.json')).write_text(json.dumps({'id':self.id,'event_id':'evt-test','status':'created','url':'https://luma.com/test'}))
  self.patch=patch.object(luma_service,'FOLDER',self.folder);self.patch.start();self.addCleanup(self.patch.stop)
  self.contacts=patch.object(luma_service,'demo_contacts',return_value={'one':{'email':'one@example.com'},'two':{'email':'two@example.com'}});self.contacts.start();self.addCleanup(self.contacts.stop)
 def test_only_selected_recipients_and_no_repeat(self):
  with patch('luma_mcp.tool',return_value={}) as call:
   body={'draftID':self.id,'personIDs':['two'],'confirmed':True}
   self.assertEqual(luma_service.invite_selected(body)['status'],'invited')
   call.assert_called_once_with('invite_guests',{'event_id':'evt-test','guests':[{'email':'two@example.com'}]})
   luma_service.invite_selected(body);self.assertEqual(call.call_count,1)
 def test_confirmation_and_unknown_email(self):
  with patch('luma_mcp.tool') as call:
   for body in [{'draftID':self.id,'personIDs':['one']},{'draftID':self.id,'personIDs':['missing'],'confirmed':True}]:
    with self.assertRaises(ValueError):luma_service.invite_selected(body)
   call.assert_not_called()
 def test_uncertain_delivery_blocks_retry(self):
  with patch('luma_mcp.tool',side_effect=TimeoutError) as call:
   body={'draftID':self.id,'personIDs':['one'],'confirmed':True}
   self.assertEqual(luma_service.invite_selected(body)['status'],'needs_review')
   self.assertEqual(luma_service.invite_selected(body)['status'],'needs_review')
   self.assertEqual(call.call_count,1)

if __name__=='__main__':unittest.main()
