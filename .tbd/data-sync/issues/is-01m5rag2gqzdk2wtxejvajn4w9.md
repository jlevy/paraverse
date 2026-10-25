---
type: is
id: is-01m5rag2gqzdk2wtxejvajn4w9
title: "PTC followup: export account-owner and person-profile references"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T01:23:43.254Z
updated_at: 2026-10-25T01:23:43.254Z
---
Qodo PR1 review5640916085 inline4369217563 atb90efb0. Populated SocialAccount.owner, GitHubAccount.entity and Person.profile references lack corresponding forward graph edges. Add deliberate relation vocabulary and coverage tests in a focused followup; current person-to-account and profile-to-person paths remain available.
