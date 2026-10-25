---
type: is
id: is-01m5ra13s2j4kscp87k9sze6zd
title: "PR13 Qodo r4369199215: bind meetup location to canonical venue"
kind: bug
status: closed
priority: 1
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-25T01:15:33.025Z
updated_at: 2026-10-25T04:45:23.074Z
started_at: 2026-10-25T01:18:17.965Z
closed_at: 2026-10-25T04:45:23.074Z
close_reason: Fixed in merged Paraverse PR13, merge b9d1815d27aae9fbe0919a4ed78b94ce61d1d80a. Independent F/G/H verify workspace people, generation ownership, sidebar cards, canonical venue, MCP lifecycle and captured recipients; final combined 96 backend and 64 release Swift tests pass. Dispositions https://github.com/jlevy/paraverse/pull/13#issuecomment-6393516949; duplicate C1 beads share one implemented fix.
resolution: null
duplicate_of: null
---
High review5640894815 at0333a174: draft source URL and venue-name substring do not bind address; arbitrary model address reaches Luma. https://github.com/jlevy/paraverse/pull/13#discussion_r4369199215. Select fixed trusted venue ID or unambiguous verified source and derive canonical name/address/source/hours; reject mismatch before save and revalidate legacy create. Onlyluma_service andsynthetic tests, no liveLuma/invites; root owns integration/push/merge.

## Notes

Fixed10d59609e1f6478cf979548ac063f3de44c46f50 based0333a174, isolatedclean. Onlyluma_service.py+newtest_luma_venues.py. Modelselects fixed trusted venueID; canonical name/address/source/hours derive from publicofficial FortMason/LongNow records, not model/sourcebody. Conflicting suppliedaddress/source/name rejected beforedraftSave. Legacycreate resolves onlyunambiguous verifiedsource, revalidatesaddress+hours beforestatuswrite/provider and sends exactcanonicaladdress. Invalidlegacy savedbytesunchanged/providerNotCalled. RED4cases=3failures+1error;GREEN9venuecases,full58backend0.072s,undefined-nameRuff+diffcheckPASS. No liveLuma/invites or pushes;root receivedcommit and owns integration/updatedreviewledger/closure. Publicvenue factscheckedofficialURLs incode;syntheticexamples only,no newcontacts/privateidentity/credentials. Earlierphonecacheflag corrected: onlylivepagehadbusinessphone, committedcatalog0contacts.
