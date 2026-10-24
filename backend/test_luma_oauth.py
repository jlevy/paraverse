import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import luma_oauth as oauth
class OAuthPersistenceTests(unittest.TestCase):
 def test_saved_connection_survives_reload(self):
  with tempfile.TemporaryDirectory() as d,patch.object(oauth,'TOKEN_FILE',Path(d)/'token.json'):
   oauth.save_tokens({'access_token':'test-token','refresh_token':'test-refresh','expires_in':3600})
   self.assertEqual(oauth.status()['status'],'connected')
   self.assertEqual(oauth.TOKEN_FILE.stat().st_mode & 0o777,0o600)
 def test_unknown_callback_state_rejected(self):
  with self.assertRaises(ValueError):oauth.finish('code=not-real&state=unknown')
 def test_expired_without_refresh_needs_reconnect(self):
  with tempfile.TemporaryDirectory() as d,patch.object(oauth,'TOKEN_FILE',Path(d)/'token.json'):
   oauth.save_tokens({'access_token':'test','expires_in':-10})
   self.assertEqual(oauth.status()['status'],'reconnect')
 def test_refresh_rotates_and_persists(self):
  import io
  with tempfile.TemporaryDirectory() as d,patch.object(oauth,'TOKEN_FILE',Path(d)/'token.json'):
   oauth.save_tokens({'access_token':'old','refresh_token':'old-refresh','expires_in':-10})
   with patch.object(oauth.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps({'access_token':'new','refresh_token':'new-refresh','expires_in':3600}).encode())):
    self.assertEqual(oauth.access_token(),'new')
   self.assertEqual(json.loads(oauth.TOKEN_FILE.read_text())['refresh_token'],'new-refresh')
