---
type: is
id: is-01m5r6fy0pfqdmaex9h2wg846s
title: "PR14 Qodo r4368916767: reject conflicting identity in portrait fallback"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
created_at: 2026-10-25T00:13:44.341Z
updated_at: 2026-10-25T00:13:44.341Z
---
Confirmed Medium latent at9037dc0 by independent strong-max review. A synthetic same-name person with a different kbID and conflicting GitHubURL still receives the legacy first portrait. No duplicate normalized names or current wrong-person portrait was demonstrated in bundled assets. Make identity-bearing conflicts stop name-only portrait fallback, with a namesake negative regression. Original finding https://github.com/jlevy/paraverse/pull/14#discussion_r4368916767. Defer bounded identity hardening after native stack; elevate if an actual bundled misidentification is found.
