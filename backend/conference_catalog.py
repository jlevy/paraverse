"""Offline matching over saved, edition-verified conference records."""
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'work/data/conference-catalog'
BAY_CITIES = {'san francisco', 'sf', 'san jose', 'palo alto', 'mountain view', 'santa clara', 'sunnyvale', 'menlo park', 'redwood city', 'cupertino', 'silicon valley', 'san mateo', 'milpitas'}
GROUPS = [
    {'ai', 'artificial intelligence', 'machine learning', 'agents', 'agentic', 'llm'},
    {'engineering', 'software', 'developer', 'developers', 'programming', 'coding'},
    {'data', 'database', 'databases', 'analytics'},
    {'design', 'ux', 'ui', 'typography', 'typefaces'},
    {'productivity', 'workflow', 'workflows', 'automation', 'tooling', 'tools'},
    {'security', 'secure', 'cybersecurity'},
    {'infrastructure', 'cloud', 'platform', 'devops'},
]
def concepts(text):
    text=text.lower()
    words={w for w in re.findall(r'[a-z0-9]+', text) if w not in {'a','an','the','and','or','to','of','in','for','on','with','your','how','is','it','at','as','by','from','what','we','our','their','this','that','work'}}
    return words | {f'group-{i}' for i,g in enumerate(GROUPS) if any((term in words if ' ' not in term else term in text) for term in g)}

def city_key(value):
    return value.lower().split(',')[0].strip()

def supported(p):
    return p.get('travel')=='Nearby' and city_key(p.get('city','')) in BAY_CITIES

def version():
    files=sorted((CATALOG/'verified').glob('*.json'))
    return hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()[:16]

def records(asof):
    result=[]
    for path in sorted((CATALOG/'verified').glob('*.json')):
        try:
            r=json.loads(path.read_text())
            if r.get('verification_status')!='official_date_location_confirmed':continue
            start=date.fromisoformat(r['start_date']);end=date.fromisoformat(r['end_date'])
            if not asof<=start<=end<=asof+timedelta(days=365):continue
            if city_key(r['city']) not in BAY_CITIES:continue
            source=CATALOG/r['evidence_file']
            if not source.is_file():continue
            result.append((r,json.loads(source.read_text())))
        except (ValueError,KeyError,TypeError):continue
    universe=ROOT/'work/data/official/conference.json'
    if universe.exists():
        r=json.loads(universe.read_text())
        start=date.fromisoformat(r['start_date']);end=date.fromisoformat(r['end_date'])
        if asof<=start<=end<=asof+timedelta(days=365):
            r.update(id='universe-2026', topics=['software engineering','AI','developer tools','open source'],
                     price={'amount':r['individual_in_person_price'],'currency':r['currency'],'ticket':'In person'})
            manifest=CATALOG/'image-cache-manifest.json'
            images=json.loads(manifest.read_text()) if manifest.exists() else []
            image=next((url for url,status in images if status=='saved' and url.startswith('https://githubuniverse.com/')),None)
            result.append((r,{'imageURL':image}))
    return result

def recommend(p, asof=None):
    if not supported(p):return None
    asof=asof or date.today()
    candidates=records(asof);ranked=[]
    for r,source in candidates:
        # Rank on the conference's curated topics and actual session titles, not
        # navigation/footer text or a previous edition mentioned on its homepage.
        program=' '.join(r.get('topics',[]))+' '+' '.join(s.get('title','') for s in r.get('sessions',[]))
        event_terms=concepts(program)
        interests=[x for x in p['interests'] if concepts(x)&event_terms]
        if not interests:continue
        score=sum(len(concepts(x)&event_terms) for x in interests)
        score+=0.25*len(concepts(p.get('title','')+' '+p.get('background',''))&event_terms)
        price=r.get('price');price_text='See registration for pricing'
        if isinstance(price,dict) and price.get('amount') is not None:
            expired = bool(price.get('valid_through') and price['valid_through'] < asof.isoformat())
            amount = price.get('standard_amount') if expired else price['amount']
            if amount is not None:
                price_text=f"{price.get('currency','USD')} {amount:g}"
                if not expired and price.get('ticket'):price_text+=' · '+price['ticket']
        elif isinstance(price,str):price_text=price
        conf={'id':r['id'],'title':r['name'],'start':r['start_date'],'end':r['end_date'],
              'dates':date.fromisoformat(r['start_date']).strftime('%b %d, %Y'),
              'city':r['city'],'venue':r.get('venue') or 'Venue to be announced','price':price_text,
              'url':r['source_url'],'online':False,'themes':r.get('topics',[]),'program':', '.join(r.get('topics',[])),
              'imageURL':source.get('imageURL')}
        if r['end_date']!=r['start_date']:conf['dates']+=' – '+date.fromisoformat(r['end_date']).strftime('%b %d, %Y')
        match={'conference':conf,'matchedInterests':interests,
               'reason':f"Program topics: {', '.join(r.get('topics',[]))}. Matches your interest in {', '.join(interests[:2])}.",
               'locationNote':'Near you · '+r['city'],
               'sources':[{'url':r['source_url'],'title':r['name'],'quotes':r.get('evidence_quotes',[])}]}
        ranked.append((score,r['start_date'],r['id'],match))
    ranked.sort(key=lambda x:(-x[0],x[1],x[2]))
    return {'matches':[x[3] for x in ranked[:6]],'generatedAt':asof.isoformat(),
            'searchedCount':len(candidates),'verifiedCount':len(candidates),
            'summary':'Matched against the saved, verified conference catalog.',
            'method':'Cached official catalog → local topic matching; no live scraping or model call',
            'catalogVersion':version()}
