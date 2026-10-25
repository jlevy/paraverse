import json
import unittest
from pathlib import Path


class PublicAttendeeExportTests(unittest.TestCase):
 def test_every_committed_row_is_minimized(self):
  from export_public_attendees import PUBLIC_FIELDS, public_attendees
  rows=json.loads((Path(__file__).resolve().parents[1]/'native/Assets/universe-attendees.json').read_text())
  self.assertEqual(len(rows),12)
  self.assertEqual(len({row['username'].casefold() for row in rows}),len(rows))
  self.assertTrue(all(isinstance(row.get('id'),str) and row['id'] for row in rows))
  self.assertEqual(len({row['id'] for row in rows}),len(rows))
  self.assertTrue(all(isinstance(row.get('attendance_status'),str) and row['attendance_status'] and isinstance(row.get('avatar_asset'),str) for row in rows))
  self.assertTrue(all(set(row)<=set(PUBLIC_FIELDS) for row in rows))
  self.assertEqual(public_attendees(rows),rows)

 def test_export_drops_unreviewed_fields_from_every_row(self):
  from export_public_attendees import public_attendees
  required=dict(id='original-stable-id',name='Example',username='example',profile_url='https://x.com/example',attendance_mode='unspecified',source_url='https://x.com/example/status/123',post_date='2026-10-01T12:00:00Z',evidence='I am attending GitHub Universe.',matching_opt_in=False,attendance_status='Public self-report')
  raw=[dict(required,generated_title='Unsupported title',enrichment_method='scraper details',about='Unreviewed synthesis'),dict(required,username='second',profile_url='https://x.com/second',source_url='https://x.com/second/status/456',post_count=500,role_source='Unreviewed')]
  exported=public_attendees(raw)
  self.assertEqual(exported[0],required)
  self.assertTrue(all('post_count' not in row and 'generated_title' not in row and 'role_source' not in row and 'about' not in row for row in exported))
  self.assertIn('generated_title',raw[0])

 def test_export_rejects_unattributed_or_invalid_ui_fields(self):
  from export_public_attendees import public_attendees
  row=dict(id='original-stable-id',name='Example',username='example',profile_url='https://x.com/example',attendance_mode='unspecified',source_url='https://x.com/example/status/123',post_date='2026-10-01',evidence='I am attending GitHub Universe.',matching_opt_in=False,attendance_status='Public self-report')
  for overrides in ({'id':None},{'id':''},{'source_url':'https://x.com/another/status/123'},{'profile_url':'https://x.com/another'},{'matching_opt_in':True},{'evidence':42},{'avatar_asset':'../../private'}):
   with self.subTest(fields=list(overrides)):
    with self.assertRaises(ValueError):public_attendees([dict(row,**overrides)])
