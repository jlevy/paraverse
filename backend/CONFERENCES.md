# Live conference recommendations

Run `python3 backend/profile_service.py` from the project root. Native Upcoming Conferences posts to loopback `/conferences`; 202 jobs are polled at `/conferences/{jobID}`. API credentials remain in root `.env`.

Each request uses title, background, selected interests, city and attendance preference. Names and social URLs are not sent for conference discovery. OpenAI Responses web search discovers organizer pages in the next 180 days; the existing Bright Data official catalog can supplement candidates. Static HTTPS retrieval obtains source text and official Open Graph images. A second OpenAI call extracts and ranks eligible editions. Validation checks exact supporting quotes, upcoming dates, source IDs, matched interest labels and attendance eligibility. Geography and semantic relevance still depend on model judgment; this is not exhaustive search or independent fact certification.

Up to five matches are returned. Unsupported prices remain unknown. Full raw search responses, fetched source text, ranking responses and rejection reasons are in `work/conference-jobs`. Results are cached six hours per date and normalized profile. New profile/travel inputs produce separate jobs; repeat requests reuse the result. No fixed conference list is used by the UI. Missing images collapse to text cards.

Tests: `python3 -m unittest discover -s backend -v` and `swift test --package-path native`.

Actual Sam run: `work/conference-jobs/0da2fdfee89c49708a62e1489a91aff6/result.json`. Nine source pages considered; five validated recommendations. Native screenshot: `outputs/live-conferences-sam.png`.

## Native demo caching

Conference artwork uses a shared memory/disk image cache with bundled snapshots for the 20 already collected image URLs (including GitHub Universe). Images are decoded at at most 1000 pixels, concurrent identical downloads are coalesced, failed image downloads back off for 60 seconds, and image containers keep fixed dimensions. Newly downloaded valid images persist locally. Recommendation results persist for six hours, keyed by full profile query including location, selected interests, background and travel. The onboarding loading screen primes results and uncached artwork before opening Discover; initial cached cards render without a loading placeholder. Calendar availability remains live. A new uncached profile still uses live discovery until the shared verified catalog is implemented.

Cache validation covers disk reload, changed interests/travel isolation and expiration. Cache directory: ~/Library/Caches/CommonGround. Image evidence URLs: work/data/conference-catalog/image-cache-manifest.json.
