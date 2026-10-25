# Paraverse for macOS

A native macOS 14+ conference demo with a pixel-art world, personal recommendations,
attendee search, AI chat, and calendar review. Build with Xcode command-line tools.

## Run from a fresh clone

From the repository root:

```sh
git submodule update --init --recursive
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env
```

Set your own `OPENAI_API_KEY` in `.env`. Live public-profile imports also require
`BRIGHT_DATA_API_KEY`. Keys and local profiles are not included in GitHub.

Start the local service in one terminal:

```sh
backend/.venv/bin/python backend/profile_service.py
```

In another terminal, build and launch:

```sh
bash native/build-app.sh
open native/build/Paraverse.app
```

The app calls the local service on port 8765. Conference browsing uses bundled
catalogs. AI chat needs the service and a valid model key. Optional FalkorDB access
uses `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_PASSWORD`, and
`FALKORDB_USERNAME`; without it, chat uses the public catalog and reports graph
retrieval as unavailable. The separate `db/` component from PR #10 retains its own
setup and dataset browser.

Luma creation/invitations require a separately authenticated local connection.
Install the optional runner with `npm ci --prefix backend/luma-browser` and
`backend/luma-browser/node_modules/.bin/playwright install chromium` if using it.
No browser sessions, contacts, credentials, or invitations are shared in this repo.

## Demo

Onboard with your public profile links, review your bio and interests, then enter
GitHub Universe. The guide appears automatically. Recommended / All switch between
personal recommendations and the full catalog. The category tabs show speaker
sessions, attendees, and external events. The sidebar opens only when requested.

In chat, try “Can you find me events on the first day around security?” Results
with known catalog IDs render as event cards. Add to calendar opens the existing
review flow; merely asking a question does not create calendar events.

## Checks

```sh
swift test --package-path native
cd backend
python3 -m unittest discover -p 'test_*.py'
```

The app is development-signed, not notarized. Generated builds, local user defaults,
raw profile research, and credentials stay on each developer’s machine. The
`vendor/` submodules are the canonical shared knowledge bases; legacy raw research
is deliberately excluded from this public repository.
