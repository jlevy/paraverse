---
type: is
id: is-01m5r25wj71h1c10wafanm4rds
title: Speed up KB startup and simplify native app entry
kind: task
status: closed
priority: 2
version: 5
delegate: codex@tinas-macbook-pro.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T22:58:20.871Z
updated_at: 2026-10-24T23:19:51.598Z
started_at: 2026-10-24T22:58:35.004Z
closed_at: 2026-10-24T23:19:51.597Z
close_reason: Published PR15 on upstream stack with reviewed performance and entry changes; 304 local tests pass and updated app is built.
resolution: null
duplicate_of: null
---
Speed up native KB browser startup with safe persisted graph reuse and ready-server retention. Add landing Knowledge Base access and exact requested copy. Remove sidebar, open returning users in Universe, move Log Out to top-right, and preserve profile/calendar through Settings. Publish as next layer on existing upstream stack because PR 10 merged during work.

## Notes

Published upstream formal stack5 PR15 (codex/kb-fast-entry), after PR14. Preserved all latest upstream planning/character-profile/curation fixes; no merged PR is changed by this new layer. Final local tested build d1bb172 clean. Exact landing copy and visible KB button added; no sidebar, returning user enters Universe; LogOuttop andgearSettingsProfile/Calendar/AppSettings. Independentchecks:198DBtests exit0,50native release tests,56backend tests,lint/typespass. Measured cold3.9815s,cachedrestart0.6347s (6.27x);nativewarmreopenmedian1.59ms. Review C1/C2 fixed withstagingcachemetadata andnonfatalembeddedpersistence. ActiveuserUniverse/sessionpreserved; nativevisualverifiedworld/toolbar/menu,landingcopysourceverified. FinalsignedappreadyonDisk. PR15 draftforreview; upstreamstackmayautomaticallyrebaseheadwithoutsourcechanges.
