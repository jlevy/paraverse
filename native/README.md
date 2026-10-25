# Paraverse for macOS

Build and run instructions are in the [repository README](../README.md#native-app).
The native SwiftUI/SpriteKit app requires macOS 14 or later.

The far-right Knowledge Base toolbar button opens a native window containing the raw
record browser. It starts `db/` locally, loads both dataset submodules into embedded
FalkorDB, and watches their builds. The browser remains inside the app; external source
links open in the default browser.

Native people and sessions are generated from the same pinned KB records at build time.
The bundled `kb-native-manifest.json` records exact commits, validation and missing
source fields. Empty biographies remain empty. Judges, hosts, speakers and public
attendee self-reports retain their distinct roles. Illustrative character artwork does
not establish attendance or location.

Profile imports and model-assisted planning use the separate local backend on port
8765. Credentials stay in the repository’s ignored `.env`, never in the app bundle.
`COMMON_GROUND_PROFILE_ENDPOINT` can override profile import during development;
other planning endpoints currently use localhost. Calendar and Luma actions use the
existing review flows.

Run `swift test -c release --package-path native` for native checks. The app is signed
for local development and needs its checkout/runtime to start the knowledge-base server;
it is not a self-contained distribution package.
