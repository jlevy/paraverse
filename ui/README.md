# Common Ground interface preview

Serve this folder with a static web server (for example `python3 -m http.server 4173 --directory ui` from the project root).

This is a standalone interaction prototype with no backend or dependencies. The fictional sample profiles, sessions, availability, and Wonder event are labeled in the UI. Real conference metadata is attributed to the official website; verify pricing before release.

Supported interactions: after-3-PM replanning, group explanations, undo/reset, conference details, external event details, and a reviewed demo ICS download. Chat is deliberately limited and states this on unsupported inputs. No scraping, LLM calls, external registration, invitations or calendar synchronization occurs here.

Design foundation: Falcon Apple Human Interface Guidelines harness (focus, clear hierarchy, progressive disclosure, feedback, accessible controls), with Emil design-engineering principles. Competitor research: Gumloop agent conversations and step-by-step tool explanations; Lindy compact progress and actionable outputs; Manus explicit control over actions. Grok Bot main interface could not be reviewed because its installed app showed an update screen.

Integration boundary: replace `plans` and sample group content with normalized conference data and graph query results; replace the deterministic `replan` function with actual agent/tool events. Render verified source links and shared availability from those results. Keep public professional evidence distinct from attendee-supplied goals/availability.
