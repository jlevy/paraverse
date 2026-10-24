---
type: is
id: is-01m5r2se89x53bc5rf4as9cxpv
title: "PR #13 Qodo r4368861868: Committed scraper harvests emails of named people"
kind: bug
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:01.576Z
updated_at: 2026-10-24T23:09:01.576Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/13#discussion_r4368861868. Location: backend/browser-test/public-contact.mjs:19. 9\. Committed scraper harvests emails of named people 🐞 Bug ⛨ Security


public-contact.mjs hard-codes four real people&#x27;s handles and sites. It saves each page&#x27;s full
innerText plus every mailto: link and email address it can find to
work/data/attendee-contacts/, and prints them to stdout; public-contact-followup.mjs does the
same for more pages. This collects third parties&#x27; contact details, which conflicts with the PR&#x27;s
data policy that profile data covers only its owner and that contact details are excluded.

MUST FIX BEFORE MERGE: contact-harvesting scripts violate repository data policy. Coordinator notified; do not defer.
