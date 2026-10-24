"""Luma public-client OAuth. Credentials remain in the local user's private storage."""
import base64, hashlib, json, os, secrets, threading, time, urllib.parse, urllib.request
from pathlib import Path
CLIENT_ID='https://gist.githubusercontent.com/nguy-tina/a518df3d639f35b2253c9faa0c5118f1/raw/common-ground-luma-client.json'
REDIRECT='http://127.0.0.1:8765/luma/oauth/callback'
RESOURCE='https://mcp.luma.com'
TOKEN_FILE=Path.home()/'Library/Application Support/CommonGround/luma-oauth.json'
_pending={}
_lock=threading.Lock()
def begin():
 state=secrets.token_urlsafe(32); verifier=secrets.token_urlsafe(48)
 with _lock:
  _pending.clear();_pending[state]=(verifier,time.time()+600)
 challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
 query=urllib.parse.urlencode(dict(credential_type='personal',client_id=CLIENT_ID,redirect_uri=REDIRECT,response_type='code',state=state,code_challenge=challenge,code_challenge_method='S256',resource=RESOURCE))
 return {'status':'authorization','authURL':'https://luma.com/oauth/consent?'+query,'message':'Approve Paraverse in your browser, then return here.'}
def finish(query):
 values=urllib.parse.parse_qs(query)
 state=values.get('state',[''])[0]
 with _lock:pending=_pending.pop(state,None)
 if not pending or pending[1]<time.time():raise ValueError('Expired or invalid authorization. Connect again from Paraverse.')
 if values.get('error'):raise ValueError('Authorization was declined. You can reconnect from Paraverse.')
 code=values.get('code',[''])[0]
 if not code:raise ValueError('Missing authorization code.')
 data=urllib.parse.urlencode(dict(grant_type='authorization_code',client_id=CLIENT_ID,redirect_uri=REDIRECT,code=code,code_verifier=pending[0],resource=RESOURCE)).encode()
 req=urllib.request.Request('https://api.luma.com/oauth/token',data=data,headers={'Content-Type':'application/x-www-form-urlencoded','User-Agent':'CommonGround/1.0'})
 with urllib.request.urlopen(req,timeout=30) as response:tokens=json.load(response)
 if not tokens.get('access_token'):raise ValueError('Authorization did not return an access token.')
 save_tokens(tokens)
 return {'status':'connected','message':'Luma connected. Return to Paraverse.'}
def save_tokens(tokens):
 tokens['saved_at']=time.time()
 if 'expires_in' in tokens:tokens['expires_at']=time.time()+float(tokens['expires_in'])
 TOKEN_FILE.parent.mkdir(parents=True,exist_ok=True)
 temporary=TOKEN_FILE.with_suffix('.tmp')
 fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'w') as f:json.dump(tokens,f)
 os.chmod(temporary,0o600);os.replace(temporary,TOKEN_FILE)
def access_token():
 with _lock:
  if not TOKEN_FILE.exists():raise ValueError('Connect Luma to continue.')
  tokens=json.loads(TOKEN_FILE.read_text())
  if tokens.get('expires_at',0)>time.time()+60:return tokens['access_token']
  if not tokens.get('refresh_token'):raise ValueError('Reconnect Luma to renew access.')
  data=urllib.parse.urlencode(dict(grant_type='refresh_token',client_id=CLIENT_ID,refresh_token=tokens['refresh_token'],resource=RESOURCE)).encode()
  req=urllib.request.Request('https://api.luma.com/oauth/token',data=data,headers={'Content-Type':'application/x-www-form-urlencoded','User-Agent':'CommonGround/1.0'})
  with urllib.request.urlopen(req,timeout=30) as response:renewed=json.load(response)
  if not renewed.get('access_token'):raise ValueError('Reconnect Luma to renew access.')
  renewed.setdefault('refresh_token',tokens['refresh_token']);save_tokens(renewed)
  return renewed['access_token']
def status():
 if not TOKEN_FILE.exists():return {'status':'disconnected'}
 try:
  access_token()
  return {'status':'connected','message':'Luma is connected.'}
 except ValueError as e:return {'status':'reconnect','message':str(e)}
 except Exception:return {'status':'unavailable','message':'Could not check Luma. Your saved connection has been kept; try again.'}
