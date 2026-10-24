"""Bounded, cached collection of public GitHub profile and repository evidence."""
import json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]

def canonical_url(raw):
    if not raw or not str(raw).strip(): return None
    raw=str(raw).strip()
    if raw.startswith(('github.com/', 'www.github.com/')): raw='https://'+raw
    u=urlparse(raw)
    handle=u.path.strip('/')
    if u.scheme!='https' or u.hostname not in ('github.com','www.github.com') or u.username or u.password or u.port or u.query or u.fragment or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?',handle):
        raise ValueError('Enter a GitHub profile URL.')
    if handle.lower() in ('settings','login','signup','explore','topics','marketplace','orgs','search','features','pricing','about'): raise ValueError('Enter a personal GitHub profile URL.')
    return 'https://github.com/'+handle.lower()

def fetch(path):
    req=Request('https://api.github.com'+path,headers={'Accept':'application/vnd.github+json','User-Agent':'CommonGround-profile-import'})
    try:
        with urlopen(req,timeout=20) as r:
            raw=r.read(2_000_001)
            if len(raw)>2_000_000: raise ValueError('GitHub response is too large.')
            return json.loads(raw)
    except HTTPError as e:
        raise RuntimeError('GitHub profile unavailable or public API rate limit reached.') from None

def normalize(data):
    profile=data['profile']; handle=profile['login'].lower(); evidence=[]
    def add(url,text,kind,date=None):
        if text: evidence.append(dict(id='gh'+str(len(evidence)+1),url=url,text=text,kind=kind,date=date))
    url='https://github.com/'+handle
    add(url, '\n'.join(f'{k}: {profile[k]}' for k in ('name','bio','company','location') if profile.get(k)), 'github_bio')
    for repo in data.get('repos',[]):
        if repo.get('private') or repo.get('fork') or repo.get('owner',{}).get('login','').lower()!=handle: continue
        text=f"Public repository owned by {handle}: {repo['name']}."
        if repo.get('description'): text+=' Description: '+repo['description']
        if repo.get('language'): text+=' Primary language: '+repo['language']
        if repo.get('topics'): text+=' Topics: '+', '.join(repo['topics'])
        text+=' Repository ownership does not establish sole authorship or expertise.'
        add(repo['html_url'],text,'github_repository',repo.get('pushed_at'))
    for event in data.get('events',[]):
        if event.get('actor',{}).get('login','').lower()!=handle or event.get('type')!='PullRequestEvent':continue
        pr=event.get('payload',{}).get('pull_request',{})
        if pr.get('user',{}).get('login','').lower()!=handle or not pr.get('html_url'):continue
        add(pr['html_url'],f"{handle} authored pull request: {pr.get('title','')}. Action: {event.get('payload',{}).get('action','')}. Merged: {bool(pr.get('merged'))}.",'github_pull_request',event.get('created_at'))
    return evidence

def collect(url,directory):
    url=canonical_url(url);handle=url.rsplit('/',1)[1]
    cache=ROOT/'work/profile-jobs/github-cache'/f'{handle}.json'
    if cache.exists() and time.time()-cache.stat().st_mtime<86400:
        data=json.loads(cache.read_text())
    else:
        profile=fetch('/users/'+handle)
        if profile.get('type')!='User' or profile.get('login','').lower()!=handle: raise ValueError('Use a personal GitHub account, not an organization.')
        data={'profile':profile,'repos':[],'events':[],'warnings':[], 'checkedAt':datetime.now(timezone.utc).isoformat(),'retrievalMethod':'GitHub public REST API, unauthenticated', 'coverage':'Up to 100 recently updated owned repositories and 30 recent public events; not full contribution history.'}
        for field,path in [('repos',f'/users/{handle}/repos?type=owner&sort=updated&per_page=100'),('events',f'/users/{handle}/events/public?per_page=30')]:
            try:data[field]=fetch(path)
            except (RuntimeError,ValueError):data['warnings'].append(field+' unavailable')
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(data,indent=2))
    (directory/'github-raw.json').write_text(json.dumps(data,indent=2))
    return normalize(data),data
