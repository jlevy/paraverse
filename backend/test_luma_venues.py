import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import luma_service


class CanonicalVenueTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.folder = self.root / 'drafts'
        self.venue = dict(id='synthetic-cafe', name='Goody Synthetic Cafe', address='Synthetic public cafe, Building C', sourceURL='https://example.org/cafe', sourceURLs=['https://example.org/cafe'], opens=510, closes=1020, hours='08:30–17:00')
        catalog = self.root / 'work/data/luma-coffee-venues.json'
        catalog.parent.mkdir(parents=True)
        catalog.write_text(json.dumps([dict(url=self.venue['sourceURL'],title='Synthetic venue source',text='Synthetic cafe information.')]))
        for target, value in [('ROOT',self.root),('FOLDER',self.folder),('VENUES',(self.venue,))]:
            fixture = patch.object(luma_service,target,value,create=True)
            fixture.start();self.addCleanup(fixture.stop)
        fixture = patch.dict(os.environ,{'OPENAI_API_KEY':'unused'})
        fixture.start();self.addCleanup(fixture.stop)
        self.draft = dict(title='Synthetic demo',description='Synthetic private demo; no invitations sent; seating not reserved.',start='2026-10-28T10:00:00-07:00',end='2026-10-28T10:45:00-07:00',venueID=self.venue['id'],venueName=self.venue['name'],address=self.venue['address'],sourceURL=self.venue['sourceURL'],venueReason='Synthetic venue choice.')

    def response(self,draft):
        return dict(status='completed',output=[dict(content=[dict(type='output_text',text=json.dumps(draft))])])

    def saved_legacy(self,**updates):
        draft=dict(self.draft,id='a'*32,status='draft',visibility='private',url=None)
        draft.pop('venueID')
        draft.update(updates)
        self.folder.mkdir()
        path=self.folder/(draft['id']+'.json')
        path.write_text(json.dumps(draft))
        return draft,path

    def test_wrong_model_address_is_rejected_before_save(self):
        self.draft['address']='Different synthetic venue'
        with patch.object(luma_service,'api',return_value=self.response(self.draft)):
            with self.assertRaisesRegex(ValueError,'address'):
                luma_service.draft_event(dict(prompt='Plan a demo'))
        self.assertFalse(self.folder.exists())

    def test_selected_id_derives_name_address_source_and_hours(self):
        selected={key:self.draft[key] for key in ('title','description','start','end','venueID')}
        with patch.object(luma_service,'api',return_value=self.response(selected)):
            result=luma_service.draft_event(dict(prompt='Plan a demo'))
        for field,key in [('venueName','name'),('address','address'),('sourceURL','sourceURL')]:
            self.assertEqual(result[field],self.venue[key])
        self.assertIn(self.venue['hours'],result['venueReason'])

    def test_legacy_wrong_address_cannot_reach_luma_or_change_saved_draft(self):
        draft,path=self.saved_legacy(address='Different synthetic venue')
        original=path.read_bytes()
        event=dict(id='synthetic-event',url='https://luma.com/synthetic',visibility='private')
        with patch('luma_mcp.tool',return_value=event) as provider:
            with self.assertRaisesRegex(ValueError,'address'):
                luma_service.create_event(draft['id'])
            provider.assert_not_called()
        self.assertEqual(path.read_bytes(),original)

    def test_legacy_verified_source_rebinds_exact_canonical_location(self):
        draft,path=self.saved_legacy(address='  '+self.venue['address'].lower()+'  ')
        event=dict(id='synthetic-event',url='https://luma.com/synthetic',visibility='private')
        with patch('luma_mcp.tool',return_value=event) as provider:
            self.assertEqual(luma_service.create_event(draft['id'])['status'],'created')
        arguments=provider.call_args_list[0].args[1]
        self.assertEqual(arguments['geo_address_json']['address'],self.venue['name']+', '+self.venue['address'])
        self.assertEqual(json.loads(path.read_text())['venueID'],self.venue['id'])

    def test_unknown_id_cannot_fall_back_to_an_allowed_source(self):
        self.draft['venueID']='unknown'
        with patch.object(luma_service,'api',return_value=self.response(self.draft)):
            with self.assertRaisesRegex(ValueError,'uniquely verified'):
                luma_service.draft_event(dict(prompt='Plan a demo'))
        self.assertFalse(self.folder.exists())

    def test_model_source_and_name_must_match_the_selected_record(self):
        for field,value in [('sourceURL','https://example.org/other'),('venueName','Different synthetic cafe')]:
            with self.subTest(field=field):
                draft=dict(self.draft,**{field:value})
                with patch.object(luma_service,'api',return_value=self.response(draft)):
                    with self.assertRaisesRegex(ValueError,'does not match'):
                        luma_service.draft_event(dict(prompt='Plan a demo'))
        self.assertFalse(self.folder.exists())

    def test_canonical_hours_apply_to_new_and_legacy_drafts(self):
        late=dict(self.draft,start='2026-10-28T18:00:00-07:00',end='2026-10-28T18:45:00-07:00')
        with patch.object(luma_service,'api',return_value=self.response(late)):
            with self.assertRaisesRegex(ValueError,'hours'):
                luma_service.draft_event(dict(prompt='Plan a demo'))
        self.assertFalse(self.folder.exists())
        draft,_=self.saved_legacy(start=late['start'],end=late['end'])
        with patch('luma_mcp.tool') as provider:
            with self.assertRaisesRegex(ValueError,'hours'):
                luma_service.create_event(draft['id'])
            provider.assert_not_called()

    def test_ambiguous_legacy_source_is_rejected_before_provider(self):
        draft,_=self.saved_legacy()
        duplicate=dict(self.venue,id='other-synthetic-cafe')
        with patch.object(luma_service,'VENUES',(self.venue,duplicate)),patch('luma_mcp.tool') as provider:
            with self.assertRaisesRegex(ValueError,'uniquely verified'):
                luma_service.create_event(draft['id'])
            provider.assert_not_called()

    def test_untrusted_catalog_source_cannot_authorize_a_venue(self):
        catalog=self.root/'work/data/luma-coffee-venues.json'
        catalog.write_text(json.dumps([dict(url='https://example.org/untrusted',text='Untrusted synthetic source')]))
        with patch.object(luma_service,'api') as provider:
            with self.assertRaisesRegex(ValueError,'source not verified'):
                luma_service.draft_event(dict(prompt='Plan a demo'))
            provider.assert_not_called()
