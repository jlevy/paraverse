"""Export only public conference fields into the native demo; no source-response metadata."""
import json
import pathlib
import re
import subprocess
import html
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'work/data/official'
OUT = ROOT / 'native/Assets'

def plain(value):
    return html.unescape(re.sub('<[^>]+>', '', value or '')).strip()

def social_url(value, platform):
    value = (value or '').strip()
    if not value or value.casefold() in {'n/a', 'na', 'none', '-', 'not applicable'}:
        return None
    host = {'linkedin':'linkedin.com', 'x':'x.com', 'github':'github.com'}[platform]
    if '://' not in value:
        if value.startswith(('www.', host, 'twitter.com')):
            value = 'https://' + value
        elif platform != 'linkedin' and re.fullmatch(r'@?[A-Za-z0-9_-]+', value):
            value = 'https://' + host + '/' + value.lstrip('@')
        else:
            return None
    parsed = urlparse(value)
    allowed = {host, 'www.' + host}
    if platform == 'x': allowed |= {'twitter.com', 'www.twitter.com'}
    if parsed.scheme not in {'http', 'https'} or parsed.hostname not in allowed or not parsed.path.strip('/'):
        return None
    return 'https://' + parsed.netloc + parsed.path.rstrip('/')

def social_links(detail):
    attrs = detail.get('attributevalues', [])
    github = next((a.get('value') for a in attrs if a.get('attribute') == 'GitHub Handle'), None)
    return dict(linkedinURL=social_url(detail.get('linkedIn'), 'linkedin'),
                xURL=social_url(detail.get('twitter'), 'x'),
                githubURL=social_url(github, 'github'))

def export():
    manifest = json.loads((SRC/'speaker-photos/manifest.json').read_text())
    sessions = json.loads((SRC/'universe-sessions.json').read_text())
    bios = {}
    def walk(obj):
        if isinstance(obj, dict):
            if obj.get('speakerId') and obj.get('fullName'):
                bios[obj['speakerId']] = obj
            for value in obj.values(): walk(value)
        elif isinstance(obj, list):
            for value in obj: walk(value)
    walk(json.loads((SRC/'speaker-photos/source-responses.json').read_text()))
    result = []
    photos = []
    for person in manifest:
        detail = bios.get(person['speaker_id'], {})
        talks = [s for s in sessions if s['session_id'] in person.get('session_ids', [])]
        # Session IDs are preferred; the manifest may omit a link present in the saved catalog.
        if not talks:
            talks = [s for s in sessions if any(p.get('name','').casefold() == person['name'].casefold() for p in s.get('speakers', []))]
        photo = None
        if person.get('status') == 'downloaded' and person.get('file'):
            photo = person['slug'] + '.jpg'
            photos.append((SRC/'speaker-photos'/person['file'], OUT/'SpeakerPhotos'/photo))
        result.append(dict(**social_links(detail), id=person['speaker_id'], name=person['name'], role=person.get('role',''), company=person.get('company',''), biography=plain(detail.get('bio')), photo=photo, sourceURL=person['source_url'], sessions=[dict(id=s['session_id'],title=s['title'],date=s.get('date',''),start=s.get('start_time',''),room=s.get('room',''),url=s.get('session_url',s.get('source_url',''))) for s in talks]))
    (OUT/'SpeakerPhotos').mkdir(exist_ok=True)
    def thumb(pair):
        src,dst = pair
        if not dst.exists(): subprocess.run(['sips','-s','format','jpeg','-Z','256',str(src),'--out',str(dst)],check=True,stdout=subprocess.DEVNULL)
    with ThreadPoolExecutor(max_workers=6) as pool: list(pool.map(thumb,photos))
    (OUT/'world-speakers.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(f'Exported {len(result)} official speakers, {len(photos)} headshots, {sum(len(p["sessions"]) for p in result)} session links.')
if __name__ == '__main__': export()
