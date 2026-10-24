"""Import public Luma event metadata from the connected account and public search."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from luma_mcp import tool
ROOT=Path(__file__).resolve().parents[1]
PACIFIC=ZoneInfo('America/Los_Angeles')

def normalize(event):
 if event.get('visibility')!='public':return None
 start=datetime.fromisoformat(event['start_at'].replace('Z','+00:00')).astimezone(PACIFIC)
 end=datetime.fromisoformat(event['end_at'].replace('Z','+00:00')).astimezone(PACIFIC)
 if not '2026-10-26'<=start.date().isoformat()<='2026-10-29' or end<=start:return None
 geo=event.get('geo_address_info') or {}
 if geo.get('city')!='San Francisco':return None
 availability=event.get('registration_availability','See event page')
 return dict(id='luma:'+event['api_id'],title=event['name'],description=event.get('description_md',''),speakers=(event.get('calendar') or {}).get('name') or ', '.join(h['name'] for h in event.get('hosts',[])),start=start.isoformat(),end=end.isoformat(),location=geo.get('city_state','San Francisco, CA'),sourceURL=event['url'],registrationStatus=availability,priceStatus='Free' if (event.get('ticket_info') or {}).get('is_free') else 'See event page',source='Luma MCP')

def main():
 bounds={'after':'2026-10-26T00:00:00-07:00','before':'2026-10-30T00:00:00-07:00'}
 entries=[];cursor=None
 while True:
  page=tool('list_events',{**bounds,'limit':50,**({'cursor':cursor} if cursor else {})})
  entries+=page.get('entries',[])
  if not page.get('has_more'):break
  cursor=page.get('next_cursor')
  if not cursor:raise RuntimeError('Missing Luma pagination cursor')
 search=tool('search_events',{**bounds,'query':'GitHub Universe','location':'San Francisco, CA'})
 candidates={e['api_id']:e for e in entries+search.get('entries',[]) if e.get('visibility')=='public'}
 with ThreadPoolExecutor(max_workers=4) as pool:
  details=list(pool.map(lambda eid:tool('get_event',{'event_id':eid}),candidates))
 rows=[row for e in details if (row:=normalize(e))]
 path=ROOT/'work/data/external/luma-universe-events.json'
 path.write_text(json.dumps(rows,indent=2))
 print(json.dumps({'imported':len(rows),'days':sorted({r['start'][:10] for r in rows})}))
if __name__=='__main__':main()
