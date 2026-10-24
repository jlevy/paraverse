# Paraverse for macOS

Native SwiftUI conference companion for macOS 14+. Includes a pixel conference world, personalized session/people/external-event recommendations, calendar export, and chat with Luma meetup creation and invitation review.

## Run locally

From the repository root:

```bash
python3 -m pip install -r backend/requirements.txt
cp .env.example .env
# Fill in provider keys in .env.
python3 backend/profile_service.py
```

In a second terminal:

```bash
bash native/build-app.sh
open native/build/Paraverse.app
```

The local service listens on port 8765. Recommendations require an OpenAI key. Profile enrichment also uses Bright Data. Optional graph access uses FALKORDB_HOST, FALKORDB_PORT, FALKORDB_USERNAME, FALKORDB_PASSWORD, FALKORDB_TLS and FALKORDB_GRAPH. Connect Luma from the event card using OAuth.

## Demo invitations

Creating a private Luma event does not send invitations. The chat card lets you review recipients and explicitly send invitations after creation. Test email mappings are stored locally in `work/demo-invite-contacts.json`, keyed by person ID, with values shaped like `{"email":"test@example.com","demo":true}`. This file is intentionally excluded from Git. Never put real recipient mappings in source control. A send with uncertain delivery requires checking Luma before retrying.

## Validation

```bash
swift test --package-path native
python3 -m unittest discover -s backend -p 'test_*.py'
```

The app is ad-hoc signed for local development, not notarized for distribution. Account state, provider keys, generated plans and local build outputs are not included in the repository.

### Live profile import

Run `python3 backend/profile_service.py` from the project root. The native app connects to localhost port 8765 by default; override with `COMMON_GROUND_PROFILE_ENDPOINT` if needed. Copy `.env.example` to `.env`, fill the two keys locally, then restart the backend. Keys stay on the backend and are never bundled in the app.

The service accepts any valid public X account and/or LinkedIn profile URL, collects at most 100 X posts by default (hard cap 1,000), and runs a fresh structured model analysis. The prompt receives only normalized retrieved evidence, never chat history or suggested hobbies. It excludes likes, reposts, other authors and sensitive inferences. Source IDs and verbatim evidence snippets are checked before displaying suggestions. These checks establish traceability, not guaranteed semantic correctness; users review every interest.

POST /profiles returns a job ID; GET /profiles/{id} returns collecting, analyzing, ready or failed. Background jobs avoid UI request timeouts. Runs and source snapshots are retained locally under work/profile-jobs. The service is bound to loopback, rejects browser-origin POSTs, and allows one active import. It is a local demo service, not a deployed multi-user service. No saved Sam shortcut remains in the import path.

Replay already collected data through the same model without paying for another scrape:

    python3 backend/profile_service.py --replay-x work/data/profiles/sam-lambert/x-brightdata.json --x-url https://x.com/samlambert --replay-linkedin work/data/profiles/sam-lambert/linkedin-brightdata.json --linkedin-url https://www.linkedin.com/in/isamlambert/

This still needs OPENAI_API_KEY. It does not substitute canned output when credentials are absent.

API references: https://developers.openai.com/api/docs/guides/structured-outputs and https://docs.brightdata.com/api-reference/rest-api/scraper/asynchronous-requests
