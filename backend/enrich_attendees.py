"""One-time, resumable enrichment of the saved self-reported attendee shortlist."""
import json,concurrent.futures
from pathlib import Path
from profile_service import ROOT,load_env,collect,normalize,analyze

def enrich(person):
 directory=ROOT/'work/data/attendee-profiles'/person['username'].lower();directory.mkdir(parents=True,exist_ok=True)
 output=directory/'enriched.json'
 if output.exists():return json.loads(output.read_text())
 try:
  raw=directory/'x-raw.json'
  posts=json.loads(raw.read_text()) if raw.exists() else collect(person['profile_url'],'x',directory,record_limit=50)
  evidence=normalize([],posts,x_url=person['profile_url'])
  (directory/'evidence.json').write_text(json.dumps(evidence,indent=2))
  saved=directory/'profile.json'
  profile=json.loads(saved.read_text()) if saved.exists() else analyze(evidence,directory)
  result={**person,'about':profile['background'],'generated_title':profile['title'],'interests':profile['interests'],'linkedin_url':None,'linkedin_status':'identity_not_verified','attendance_reason':None,'enrichment_status':'ready','enrichment_method':'Bright Data X profile posts + evidence-validated AI analysis','post_count':len(posts)}
  output.write_text(json.dumps(result,indent=2));return result
 except Exception as error:
  result={**person,'enrichment_status':'failed','error':str(error),'interests':[]};(directory/'error.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 load_env();people=json.loads((ROOT/'native/Assets/universe-attendees.json').read_text())
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for p in pool.map(enrich,people): print(json.dumps({'person':p['name'],'status':p['enrichment_status'],'interests':len(p['interests'])}),flush=True)
