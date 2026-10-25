---
type: is
id: is-01m5r9wbprxxhy8pcwerr3jsbh
title: "PR14 Qodo r4368997702: disable remote browser images by default"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
created_at: 2026-10-25T01:12:57.291Z
updated_at: 2026-10-25T01:12:57.291Z
---
Independent strong-max adjudication confirms Medium atf05e/source: native KB URL omits images=0 while browser index defaults images on, allowing remote HTTP(S) image subresources. Prefer explicit opt-in images without changing source provenance. Original https://github.com/jlevy/paraverse/pull/14#discussion_r4368997702 from Qodo review5640663254. Nonpressing privacy-default follow-up after native stack; no secret leak was demonstrated.
