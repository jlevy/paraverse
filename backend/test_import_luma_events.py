import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import import_luma_events as importer

class LumaImportPaginationTests(unittest.TestCase):
 def run_import(self, page_count):
  calls=[]
  pages=iter([dict(entries=[dict(api_id=f'listed-{i}',visibility='public')],has_more=i+1<page_count,next_cursor=f'page-{i+1}') for i in range(page_count)])
  def tool(name,arguments):
   calls.append(name)
   if name=='list_events':return next(pages)
   if name=='search_events':return dict(entries=[dict(api_id='searched',visibility='public')])
   if name=='get_event':
    eid=arguments['event_id']
    return dict(api_id=eid,visibility='public',name='Synthetic public event',start_at='2026-10-28T16:00:00-07:00',end_at='2026-10-28T17:00:00-07:00',url='https://luma.com/synthetic-'+eid,geo_address_info=dict(city='San Francisco'))
   raise AssertionError(name)
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'work/data/external').mkdir(parents=True)
   with patch.object(importer,'ROOT',root),patch.object(importer,'tool',side_effect=tool),contextlib.redirect_stdout(io.StringIO()):
    importer.main()
   rows=json.loads((root/'work/data/external/luma-universe-events.json').read_text())
  self.assertEqual(calls[:page_count+1],['list_events']*page_count+['search_events'])
  self.assertEqual(calls.count('search_events'),1)
  self.assertEqual({r['id'] for r in rows},{f'luma:listed-{i}' for i in range(page_count)}|{'luma:searched'})
 def test_single_page_runs_public_search_after_listing(self):self.run_import(1)
 def test_multi_page_runs_public_search_after_final_page(self):self.run_import(2)
