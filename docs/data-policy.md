# Data Policy

Paraverse publishes conference knowledge bases in a public repository.
Anything committed here can be copied and indexed by anyone, and it stays in git history
even after a later commit deletes it.
This policy sets what may be committed.
Check every change that adds or alters data against it before you commit, and again
when you review the pull request.

When in doubt, leave it out.
Information that was never committed is easy to add later, but once something is in a
public history it is hard to remove.

## Scope

The policy covers everything committed to the repository:

- knowledge-base records, search documents and graph exports
- raw source caches, curation files and generated synthesis such as bios
- test fixtures and the examples in docs
- commit messages, pull request text and issue text

## What May Be Included

Include public information that people or organizations published for a public,
professional audience and would expect to see connected to a conference:

- **Conference material:** the agenda, sessions, speaker names, titles, affiliations and
  speaker bios, sponsors, exhibitors, venues and rooms.
- **Public profiles on GitHub, LinkedIn and X:** the person’s own public profile
  information, such as name, handle, headline or bio, city-level location, current and
  past roles, education, links, and public counts, along with their own public posts.
  These profiles are central to the knowledge base.
  The same applies to other accounts a person uses for their work, such as Bluesky,
  Mastodon and YouTube.
- **Professional work people published themselves:** public repositories, packages they
  maintain, publications, patents, talks, and pages or posts about their work on their
  own sites.
- **Public statements about the event:** posts in which a person says they are speaking
  at or attending it.
- **Organizations:** facts from an organization’s own public pages.
- **Derived facts:** facts drawn from the sources above, each with a citation to its
  source.

## What Must Not Be Included

- **Contact details:** email addresses, phone numbers and postal addresses, even when the
  person published them.
  The build redacts them from free text, and a test fails if any remain.
- **Non-public sources:** anything behind a login, paywall or other access control, and
  anything obtained by working around one.
- **Other people’s data inside a profile:** scraped profile payloads often carry data
  about people other than the profile’s owner, such as “people also viewed” lists,
  similar profiles, and other people’s posts and reactions.
  Strip it, along with scraper bookkeeping that describes no one, before committing.
- **Sensitive personal attributes:** health, religion, political views, sexual
  orientation, ethnicity, family and relationships, immigration status, finances, birth
  date or age, and any location finer than a city or metro area.
  Do not infer them either.
- **Unstated attendance:** do not list someone as attending unless they said so
  publicly.
  A like, a follow or another person’s post is not enough.
- **Personal accounts:** accounts and pages unrelated to a person’s professional work.
- **Credentials:** API keys, tokens, cookies and browser session state.
  `.gitignore` excludes the usual files; check anyway.
- **Machine details:** absolute local paths, host names and local account names from the
  machine that ran a crawl.

## Generated Text

Bios and summaries written by a model must:

- stay within what their cited sources say, and cite them
- keep to professional facts, with no speculation about personality, motives or any of
  the sensitive attributes above
- record the model and a hash of the inputs, so that stale text can be found and
  rewritten

## Removal Requests

Anyone may ask to have their data removed by opening an issue, or privately by
contacting a maintainer.
To handle a request:

1. Exclude the person in the conference’s curation data so that later crawls and builds
   leave them out.
2. Rebuild the knowledge base and confirm the person is gone from the records, search
   documents, graph exports and test fixtures.
3. Commit the removal promptly.
   Removing the data from earlier history means rewriting it, and the maintainers decide
   case by case whether to do that.

## Review Checklist

Every pull request that adds or changes data, fixtures or doc examples includes this
checklist in its description, and the reviewer checks each item:

- [ ] Every new source is public and needs no login.
- [ ] No contact details appear, and the redaction test passes.
- [ ] Profile data covers only the profile’s owner, with no other people’s data and no
  scraper bookkeeping.
- [ ] No sensitive attributes are stated or inferred.
- [ ] Attendance appears only where the person said so publicly.
- [ ] Generated text cites its sources and stays professional.
- [ ] No credentials, local paths or machine details appear.
- [ ] Test fixtures and doc examples follow the same rules.
