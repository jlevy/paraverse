"""Download official speaker portraits and build a JavaScript-ready reference index."""
import concurrent.futures
import datetime
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import unicodedata
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/data/official/speaker-photos'
SOURCE = 'https://reg.githubuniverse.com/flow/github/universe26/attendee-portal/page/speakers'


def collect():
    responses = json.loads((OUT / 'source-responses.json').read_text())
    source = next(r for r in responses if 'loadEventSpeakers' in r['url'])
    items = source['body']['data']['items']
    sessions = json.loads((OUT.parent / 'universe-sessions.json').read_text())
    expected = {s['name'] for r in sessions for s in r.get('speakers', [])}
    (OUT / 'originals').mkdir(exist_ok=True)

    def download(item):
        name = item['fullName']
        slug = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()).strip('-')
        url = item.get('photoURL')
        record = dict(name=name, slug=slug, speaker_id=item['speakerId'], company=item.get('companyName'), role=item.get('jobTitle'), source_url=SOURCE, photo_url=url, session_ids=[s['sessionID'] for s in item.get('session', []) if s.get('published') == 'true'], in_saved_catalog=name in expected)
        if not url:
            return dict(record, status='missing_photo')
        ext = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).suffix.lower()
        target = OUT / 'originals' / (slug + ext)
        try:
            if not target.exists():
                with urllib.request.urlopen(url, timeout=60) as response:
                    data = response.read()
                    if not response.headers.get('Content-Type', '').lower().startswith('image/'):
                        raise ValueError('Source did not return an image')
                target.write_bytes(data)
            data = target.read_bytes()
            info = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(target)], capture_output=True, text=True, check=True).stdout
            width = int(re.search(r'pixelWidth: (\d+)', info)[1])
            height = int(re.search(r'pixelHeight: (\d+)', info)[1])
            return dict(record, status='downloaded', file=str(target.relative_to(OUT)), width=width, height=height, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        except Exception as error:
            return dict(record, status='failed', error=str(error))

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(download, items))
    records.sort(key=lambda r: r['name'])
    (OUT / 'manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'speakers.js').write_text('// Official photo references. Paths are relative to this module.\nexport const speakers = ' + json.dumps(records, ensure_ascii=False, indent=2) + ';\nexport default speakers;\n')
    downloaded = [r for r in records if r['status'] == 'downloaded']
    hashes = {}
    for r in downloaded:
        hashes.setdefault(r['sha256'], []).append(r['name'])
    validation = dict(collected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), source_url=SOURCE, saved_catalog_speakers=len(expected), official_directory_speakers=len(items), downloaded=len(downloaded), missing_catalog_names=sorted(expected - {r['name'] for r in downloaded}), failures=[r for r in records if r['status'] != 'downloaded'], duplicate_image_groups=[names for names in hashes.values() if len(names)>1], total_bytes=sum(r['bytes'] for r in downloaded), min_width=min((r['width'] for r in downloaded), default=0), min_height=min((r['height'] for r in downloaded), default=0))
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    cards = ''.join('<figure><img loading="lazy" src="' + html.escape(r['file'], quote=True) + '" alt="' + html.escape(r['name'], quote=True) + '"><figcaption><strong>' + html.escape(r['name']) + '</strong><br>' + html.escape(r['company'] or '') + '<br><small>' + str(r['width']) + ' × ' + str(r['height']) + '</small></figcaption></figure>' for r in downloaded)
    (OUT / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>GitHub Universe speaker photo references</title><style>body{font:16px system-ui;background:#111118;color:#eee;margin:32px}a{color:#c8afff}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:24px}figure{margin:0}img{width:100%;aspect-ratio:1;object-fit:contain;background:#23232d;border-radius:10px}figcaption{padding:10px 0;line-height:1.6}small{color:#aaa}</style><h1>GitHub Universe 2026 speaker references</h1><p>' + str(len(downloaded)) + ' original official speaker photos. <a href="' + SOURCE + '">Official directory</a>. These are photo references for future drawings.</p><main>' + cards + '</main></html>')
    print(json.dumps(validation, indent=2))

if __name__ == '__main__':
    collect()
