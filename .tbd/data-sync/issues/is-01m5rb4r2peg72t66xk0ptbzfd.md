---
type: is
id: is-01m5rb4r2peg72t66xk0ptbzfd
title: "PR13 Qodo r4369238729: pin conference fetches to validated public DNS"
kind: bug
status: in_progress
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T01:35:00.692Z
updated_at: 2026-10-25T01:42:10.109Z
started_at: 2026-10-25T01:36:14.874Z
---
High review5640939881 https://github.com/jlevy/paraverse/pull/13#discussion_r4369238729. Replace check-then-reresolve urllib conference fetch path with DNS-pinned public HTTPS transport preserving original TLS hostname and Host. Validate/pin redirects, reject private destinations, drop credential forwarding and preserve size/type limits. Isolated8cf source; no primary refs/push.

## Notes

Fixf84692432562f5e8c6320b004cb569e30515ef24 on8cf, integratedlocally13as7ff2190; notpushedyet. ActualsocketRED2failures(publicDNSthenloopbackconnect);13targetedGREEN0.198s,FULL68backend0.259s. Stdlib-onlypublisheda823transportadaptation,HTTPS443GET/HEADno body,checkedIPsockaddrpinned,originalTLS/Host/CERT_REQUIRED,proxiesdisabled,allhoppublicheaders-only,5redirectlimit,private/mixed/encoded/IPv6/downgrade rejection,2MB/typeboundsunchanged. Evidence scratchpad/review/conference-http-evidence.json. Await MCP/card bundle and nativeupstack/publication.
