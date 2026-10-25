---
type: is
id: is-01m5r9wc2rk8cjmv3rr7krbg95
title: "PR14 Qodo r4368997704: order session timestamps by instant"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
created_at: 2026-10-25T01:12:57.687Z
updated_at: 2026-10-25T01:12:57.687Z
---
Independent strong-max adjudication confirms latent Medium: fixture sorts09:00Z before10:00+02:00 even though latter is08:00Z. Current161 bundled sessions use the same -07 offset, so no actual current misorder established. Sort parsed zoned instants with a mixed-offset regression. Original https://github.com/jlevy/paraverse/pull/14#discussion_r4368997704 from review5640663254. Nonpressing follow-up after native stack.
