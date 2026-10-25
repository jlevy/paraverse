import json,concurrent.futures
from profile_service import ROOT,load_env,collect,normalize,analyze
# Identity matched using the same full name and employer on public LinkedIn results and saved X bios.
LINKS={'orenme':'https://www.linkedin.com/in/orenmelamed','rishabincloud':'https://www.linkedin.com/in/rishabkumar7','jessehouwing':'https://www.linkedin.com/in/jessehouwing'}
def run(item):
 handle,url=item;d=ROOT/'work/data/attendee-profiles'/handle
 try:
  raw=d/'linkedin-raw.json';li=json.loads(raw.read_text()) if raw.exists() else collect(url,'linkedin',d)
  posts=json.loads((d/'x-raw.json').read_text());e=normalize(li,posts,li_url=url,x_url='https://x.com/'+handle)
  (d/'evidence.json').write_text(json.dumps(e,indent=2));profile=analyze(e,d)
  p=json.loads((d/'enriched.json').read_text());p.update(about=profile['background'],generated_title=profile['title'],interests=profile['interests'],linkedin_url=url,linkedin_status='name_and_employer_matched',enrichment_method='Bright Data LinkedIn and X + evidence-validated AI analysis')
  (d/'enriched.json').write_text(json.dumps(p,indent=2));return {'person':handle,'status':'ready','interests':len(p['interests'])}
 except Exception as e:return {'person':handle,'status':'failed','error':str(e)}
if __name__=='__main__':
 load_env()
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for r in pool.map(run,LINKS.items()):print(json.dumps(r),flush=True)
