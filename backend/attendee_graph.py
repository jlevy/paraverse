"""Evidence-backed attendee graph. Queries are fixed and parameterized, never model-authored."""
import json,os,re,hashlib
from pathlib import Path
from profile_service import ROOT,load_env
from session_service import catalog
TOPICS={'ai-agents':('AI agents',r'\bagents?\b|agentic|copilot'),'developer-tools':('Developer tools',r'developer tool|devops|github|coding|software development'),'workflow-automation':('Workflow automation',r'workflow|automat|ci/cd|continuous integration'),'cloud':('Cloud infrastructure',r'\bcloud\b|\baws\b|azure|infrastructure'),'open-source':('Open source',r'open.source|oss|maintainer'),'design':('Product design',r'\bdesign\b|typography|interface'),'data':('Data systems',r'\bdata\b|database|postgres|machine learning')}
def topics(text):return [{'id':k,'name':name} for k,(name,pattern) in TOPICS.items() if re.search(pattern,text,re.I)]
def people():
 canonical=ROOT/'native/Assets/kb-attendees.json'
 if canonical.exists():return json.loads(canonical.read_text())
 base=json.loads((ROOT/'native/Assets/universe-attendees.json').read_text())
 source=ROOT/'work/data/external/attendance-x-api/candidate-users.json'
 bios={p['username'].lower():p.get('description','') for p in json.loads(source.read_text())['data']} if source.exists() else {}
 for p in base:
  f=ROOT/'work/data/attendee-profiles'/p['username'].lower()/'enriched.json'
  if f.exists():p.update(json.loads(f.read_text()))
  else:
   p.setdefault('about',bios.get(p['username'].lower(),''))
   p.setdefault('interests',[])
   p.setdefault('enrichment_status','pending')
   p.setdefault('linkedin_url',None)
  p['id']=p['username'].lower()
 return base

def connect():
 load_env()
 if not os.environ.get('FALKORDB_PASSWORD'):raise RuntimeError('FalkorDB password is not configured')
 from falkordb import FalkorDB
 db=FalkorDB(host=os.environ['FALKORDB_HOST'],port=int(os.environ['FALKORDB_PORT']),username=os.environ.get('FALKORDB_USERNAME','falkordb'),password=os.environ['FALKORDB_PASSWORD'],ssl=os.environ.get("FALKORDB_TLS","false").lower()=="true",ssl_check_hostname=True,socket_connect_timeout=8,socket_timeout=15)
 return db.select_graph(os.environ.get('FALKORDB_GRAPH','universe_demo'))

def sync():
 graph=connect();graph.query("MERGE (c:Conference {id:'universe-2026'}) SET c.name='GitHub Universe 2026', c.start='2026-10-28', c.end='2026-10-29'")
 for p in people():
  graph.query('MERGE (p:Person {id:$id}) SET p.name=$name,p.role=$role,p.about=$about,p.x_url=$url,p.matching_opt_in=$opt,p.profile_json=$payload WITH p MATCH (c:Conference {id:$conference}) MERGE (p)-[a:ATTENDANCE_SIGNAL]->(c) SET a.status=$status,a.source_url=$source,a.quote=$quote,a.date=$date',{'id':p['id'],'name':p['name'],'role':p.get('role',''),'about':p.get('about',''),'url':p['profile_url'],'opt':p['matching_opt_in'],'payload':json.dumps(p),'conference':'universe-2026','status':p['attendance_status'],'source':p['source_url'],'quote':p['evidence'],'date':p['post_date']})
  graph.query('MATCH (p:Person {id:$id})-[r:HAS_INTEREST]->() DELETE r', {'id':p['id']})
  for interest in p.get('interests',[]):
   labels=topics(interest['label']) or [{'id':'interest-'+hashlib.sha256(interest['label'].casefold().encode()).hexdigest()[:16],'name':interest['label']}]
   for topic in labels:
    graph.query('MATCH (p:Person {id:$person}) MERGE (t:Topic {id:$topic}) SET t.name=$name MERGE (p)-[r:HAS_INTEREST {label:$label}]->(t) SET r.label=$label,r.category=$category,r.confidence=$confidence,r.evidence_json=$evidence',{'person':p['id'],'topic':topic['id'],'name':topic['name'],'label':interest['label'],'category':interest['category'],'confidence':interest['confidence'],'evidence':json.dumps(interest['evidence'])})
 for s in [{**s,'kind':'Session'} for s in catalog()]+[{**s,'kind':'SideEvent'} for s in catalog(True)]:
  graph.query('MERGE (s:'+s['kind']+' {id:$id}) SET s.title=$title,s.start=$start,s.end=$end,s.source_url=$url WITH s MATCH (c:Conference {id:$conference}) MERGE (s)-[:'+('PART_OF' if s['kind']=='Session' else 'AROUND')+']->(c)',{'id':s['id'],'title':s['title'],'start':s['start'],'end':s['end'],'url':s['sourceURL'],'conference':'universe-2026'})
  for topic in topics(s['title']+' '+s['description']):
   graph.query('MATCH (s:'+s['kind']+' {id:$session}) MERGE (t:Topic {id:$topic}) SET t.name=$name MERGE (s)-[r:COVERS]->(t) SET r.method=$method',{'session':s['id'],'topic':topic['id'],'name':topic['name'],'method':'Keyword topic classification from official session text'})
 demo=ROOT/'work/profile-jobs/cdffac16e57d40768f83132219292325/profile.json'
 if demo.exists():
  user=json.loads(demo.read_text())
  graph.query("MERGE (p:DemoProfile {id:'demo-joshua'}) SET p.name='Joshua Levy',p.record_type='demo_profile' WITH p MATCH (c:Conference {id:'universe-2026'}) MERGE (p)-[r:PLANNING_TO_ATTEND]->(c) SET r.basis='User-selected demo preference; not independently verified attendance'")
  for interest in user['interests']:
   for topic in topics(interest['label']):
    graph.query("MATCH (p:DemoProfile {id:'demo-joshua'}) MERGE (t:Topic {id:$id}) SET t.name=$name MERGE (p)-[r:HAS_INTEREST {label:$label}]->(t) SET r.category=$category,r.evidence_json=$evidence",{'id':topic['id'],'name':topic['name'],'label':interest['label'],'category':interest['category'],'evidence':json.dumps(interest['evidence'])})
 return graph.ro_query('MATCH (n) RETURN count(n)').result_set

def lookup(profile):
 if (ROOT/'native/Assets/kb-native-manifest.json').exists():
  raise RuntimeError('The legacy demo graph is separate from the current knowledge-base snapshot')
 labels=topics(' '.join(profile.get('interests',[])))
 graph=connect()
 rows=graph.ro_query('MATCH (p:Person)-[r:HAS_INTEREST]->(t:Topic) WHERE t.id IN $topics MATCH (p)-[a:ATTENDANCE_SIGNAL]->(:Conference {id:$conference}) OPTIONAL MATCH (s:Session)-[:COVERS]->(t) RETURN p.id,p.name,t.name,r.evidence_json,a.source_url,collect(DISTINCT s.title) AS related_sessions LIMIT 30',{'topics':[t['id'] for t in labels],'conference':'universe-2026'}).result_set
 return [dict(person_id=r[0],person=r[1],shared_topic=r[2],interest_evidence=json.loads(r[3]),attendance_source=r[4],related_sessions=r[5]) for r in rows]
if __name__=='__main__':print(json.dumps({'nodes':sync()}))
